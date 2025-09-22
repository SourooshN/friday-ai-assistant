"""
Friday UI Backend - API Server

Provides a REST API bridge between the Friday UI frontend and the core Friday system.
Handles task submission, status monitoring, and log streaming.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import subprocess
import os

from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Add Friday core to path
import sys
friday_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(friday_root))

from core.kernel import FridayKernel
from core.logging import get_logger


class TaskRequest(BaseModel):
    description: str
    context: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    initialized: bool
    running: bool
    environment: str
    components: Dict[str, Any]


class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    component: str


class FridayAPIServer:
    """API server for Friday UI backend."""

    def __init__(self):
        self.app = FastAPI(
            title="Friday AI Assistant API",
            description="REST API for Friday AI Assistant UI",
            version="1.0.0"
        )

        # Enable CORS for frontend development
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Friday kernel instance
        self.kernel: Optional[FridayKernel] = None
        self.kernel_initialized = False

        # Active WebSocket connections for real-time updates
        self.websocket_connections: List[WebSocket] = []

        # Task tracking
        self.active_tasks: Dict[str, Dict[str, Any]] = {}

        # Log storage for UI
        self.recent_logs: List[LogEntry] = []
        self.max_logs = 1000

        self._setup_routes()

    def _setup_routes(self):
        """Setup API routes."""

        @self.app.on_event("startup")
        async def startup_event():
            """Initialize Friday kernel on startup."""
            await self._initialize_kernel()

        @self.app.on_event("shutdown")
        async def shutdown_event():
            """Cleanup on shutdown."""
            if self.kernel:
                await self.kernel.shutdown()

        @self.app.get("/")
        async def root():
            """Root endpoint - health check."""
            return {"message": "Friday AI Assistant API", "status": "running"}

        @self.app.get("/api/status", response_model=StatusResponse)
        async def get_status():
            """Get Friday system status."""
            if not self.kernel:
                return StatusResponse(
                    initialized=False,
                    running=False,
                    environment="unknown",
                    components={}
                )

            status = self.kernel.get_system_status()
            return StatusResponse(
                initialized=status.get("initialized", False),
                running=status.get("running", False),
                environment=status.get("environment", "unknown"),
                components=status.get("components", {})
            )

        @self.app.post("/api/tasks", response_model=TaskResponse)
        async def submit_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
            """Submit a new task to Friday."""
            if not self.kernel or not self.kernel_initialized:
                raise HTTPException(status_code=503, detail="Friday kernel not initialized")

            try:
                task_id = await self.kernel.submit_task(
                    task_request.description,
                    task_request.context or {}
                )

                # Track task
                self.active_tasks[task_id] = {
                    "id": task_id,
                    "description": task_request.description,
                    "context": task_request.context,
                    "submitted_at": datetime.utcnow().isoformat(),
                    "status": "submitted"
                }

                # Start background task monitoring
                background_tasks.add_task(self._monitor_task, task_id)

                # Notify WebSocket clients
                await self._broadcast_task_update(task_id, "submitted")

                return TaskResponse(
                    task_id=task_id,
                    status="submitted",
                    message="Task submitted successfully"
                )

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")

        @self.app.get("/api/tasks/{task_id}")
        async def get_task_status(task_id: str):
            """Get status of a specific task."""
            if not self.kernel:
                raise HTTPException(status_code=503, detail="Friday kernel not initialized")

            try:
                status = await self.kernel.get_task_status(task_id)

                # Update our tracking
                if task_id in self.active_tasks:
                    self.active_tasks[task_id].update(status)

                return status

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

        @self.app.get("/api/tasks")
        async def list_tasks():
            """List all tracked tasks."""
            return {"tasks": list(self.active_tasks.values())}

        @self.app.get("/api/logs")
        async def get_logs(
            limit: int = 100,
            level: Optional[str] = None,
            component: Optional[str] = None
        ):
            """Get recent logs with optional filtering."""
            logs = self.recent_logs[-limit:]

            if level:
                logs = [log for log in logs if log.level.lower() == level.lower()]

            if component:
                logs = [log for log in logs if component.lower() in log.component.lower()]

            return {"logs": [log.dict() for log in logs]}

        @self.app.websocket("/api/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            self.websocket_connections.append(websocket)

            try:
                # Send initial status
                if self.kernel:
                    status = self.kernel.get_system_status()
                    await websocket.send_json({"type": "status", "data": status})

                # Keep connection alive
                while True:
                    # Wait for messages (ping/pong to keep alive)
                    try:
                        data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                        message = json.loads(data)

                        if message.get("type") == "ping":
                            await websocket.send_json({"type": "pong"})

                    except asyncio.TimeoutError:
                        # Send periodic status updates
                        if self.kernel:
                            status = self.kernel.get_system_status()
                            await websocket.send_json({"type": "status", "data": status})

            except Exception as e:
                print(f"WebSocket error: {e}")
            finally:
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)

        # Serve static files (React build)
        frontend_build = Path(__file__).parent.parent / "frontend" / "build"
        if frontend_build.exists():
            self.app.mount("/static", StaticFiles(directory=str(frontend_build / "static")), name="static")

            @self.app.get("/{path:path}")
            async def serve_frontend(path: str):
                """Serve React frontend."""
                if path.startswith("api/"):
                    raise HTTPException(status_code=404)

                file_path = frontend_build / path
                if file_path.exists() and file_path.is_file():
                    return FileResponse(file_path)
                else:
                    # Serve index.html for client-side routing
                    return FileResponse(frontend_build / "index.html")

    async def _initialize_kernel(self):
        """Initialize Friday kernel."""
        try:
            self.kernel = FridayKernel(environment="dev")
            success = await self.kernel.initialize()

            if success:
                self.kernel_initialized = True
                print("Friday kernel initialized successfully")

                # Add log capture
                self._setup_log_capture()
            else:
                print("Failed to initialize Friday kernel")

        except Exception as e:
            print(f"Error initializing Friday kernel: {e}")

    def _setup_log_capture(self):
        """Setup log capture for UI display."""
        # This is a simplified log capture - in a real implementation,
        # you'd want to hook into the logging system more directly
        pass

    async def _monitor_task(self, task_id: str):
        """Monitor task progress in background."""
        if not self.kernel:
            return

        try:
            # Poll task status until completion
            while task_id in self.active_tasks:
                await asyncio.sleep(1)  # Poll every second

                status = await self.kernel.get_task_status(task_id)
                if status:
                    self.active_tasks[task_id].update(status)

                    # Notify WebSocket clients
                    await self._broadcast_task_update(task_id, status.get("status", "unknown"))

                    # Stop monitoring if task is complete
                    if status.get("status") in ["completed", "failed"]:
                        break

        except Exception as e:
            print(f"Error monitoring task {task_id}: {e}")

    async def _broadcast_task_update(self, task_id: str, status: str):
        """Broadcast task updates to WebSocket clients."""
        if not self.websocket_connections:
            return

        update = {
            "type": "task_update",
            "data": {
                "task_id": task_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        # Send to all connected clients
        disconnected = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(update)
            except Exception:
                disconnected.append(websocket)

        # Remove disconnected clients
        for websocket in disconnected:
            self.websocket_connections.remove(websocket)

    def add_log_entry(self, level: str, message: str, component: str = "system"):
        """Add a log entry for UI display."""
        log_entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=level,
            message=message,
            component=component
        )

        self.recent_logs.append(log_entry)

        # Keep only recent logs
        if len(self.recent_logs) > self.max_logs:
            self.recent_logs = self.recent_logs[-self.max_logs:]

        # Broadcast to WebSocket clients
        asyncio.create_task(self._broadcast_log_entry(log_entry))

    async def _broadcast_log_entry(self, log_entry: LogEntry):
        """Broadcast log entry to WebSocket clients."""
        if not self.websocket_connections:
            return

        update = {
            "type": "log_entry",
            "data": log_entry.dict()
        }

        # Send to all connected clients
        disconnected = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(update)
            except Exception:
                disconnected.append(websocket)

        # Remove disconnected clients
        for websocket in disconnected:
            self.websocket_connections.remove(websocket)


# Global API server instance
api_server = FridayAPIServer()
app = api_server.app


if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )