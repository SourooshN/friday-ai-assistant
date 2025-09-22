"""
Friday Task Orchestrator

Handles task planning, execution, and coordination.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from ..logging import get_logger


class TaskOrchestrator:
    """
    Manages task planning, execution, and coordination across the Friday system.

    This is a skeleton implementation for Milestone 1.
    """

    def __init__(self, config, plugin_host, memory_manager, policy_engine):
        self.config = config
        self.plugin_host = plugin_host
        self.memory_manager = memory_manager
        self.policy_engine = policy_engine
        self.logger = get_logger()

        # Task tracking
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._running = False

    async def start(self):
        """Start the orchestrator."""
        self.logger.info("Task orchestrator starting...")
        self._running = True
        self.logger.audit("Orchestrator started", action="orchestrator_start")

    async def stop(self):
        """Stop the orchestrator."""
        self.logger.info("Task orchestrator stopping...")
        self._running = False
        self.logger.audit("Orchestrator stopped", action="orchestrator_stop")

    async def submit_task(self, description: str, context: Dict[str, Any]) -> str:
        """
        Submit a new task for execution.

        Args:
            description: Natural language description of the task
            context: Additional context for the task

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "description": description,
            "context": context,
            "status": "submitted",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "result": None
        }

        self._tasks[task_id] = task
        self.logger.log_task_start(task_id, "user_request", description)

        # Simple task routing based on keywords
        try:
            result = await self._execute_task(task_id, description, context)
            task["status"] = "completed"
            task["result"] = result
            success = result.get("success", False)
        except Exception as e:
            task["status"] = "failed"
            task["result"] = {"success": False, "error": str(e)}
            success = False

        task["updated_at"] = datetime.utcnow().isoformat()
        self.logger.log_task_complete(task_id, "user_request", success)

        return task_id

    async def _execute_task(self, task_id: str, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task by routing to appropriate plugin tools.

        Args:
            task_id: Task identifier
            description: Task description
            context: Task context

        Returns:
            Task execution result
        """
        description_lower = description.lower()

        # Simple keyword-based routing to system control plugin
        if any(keyword in description_lower for keyword in [
            "system info", "cpu", "memory", "disk", "processes",
            "shutdown", "restart", "sleep", "volume", "brightness"
        ]):
            return await self._route_to_system_control(description_lower, context)

        elif any(keyword in description_lower for keyword in [
            "file", "folder", "directory", "create file", "read file", "write file", "delete file",
            "list files", "search files", "copy file", "move file", "file info"
        ]):
            return await self._route_to_file_operations(description_lower, context)

        elif any(keyword in description_lower for keyword in ["hello", "hi", "greeting"]):
            return await self._route_to_hello_plugin(description_lower, context)

        elif any(keyword in description_lower for keyword in [
            "play", "pause", "stop", "music", "media", "volume", "mute", "unmute",
            "launch", "open", "close", "application", "app", "window", "focus"
        ]):
            return await self._route_to_media_app_control(description_lower, context)

        else:
            # Default response for unrecognized tasks
            return {
                "success": True,
                "message": f"Received task: {description}",
                "note": "Task routing not yet implemented for this type of request"
            }

    async def _route_to_system_control(self, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route task to system control plugin."""
        if not self.plugin_host:
            return {"success": False, "error": "Plugin host not available"}

        # Map keywords to specific tools
        if "system info" in description or "system information" in description:
            return await self.plugin_host.invoke_plugin_tool("system_control", "get_system_info")

        elif "cpu" in description:
            return await self.plugin_host.invoke_plugin_tool("system_control", "get_cpu_usage")

        elif "memory" in description:
            return await self.plugin_host.invoke_plugin_tool("system_control", "get_memory_usage")

        elif "disk" in description:
            path = context.get("path", "/")
            return await self.plugin_host.invoke_plugin_tool("system_control", "get_disk_usage", path=path)

        elif "processes" in description or "process list" in description:
            limit = context.get("limit", 10)
            return await self.plugin_host.invoke_plugin_tool("system_control", "list_processes", limit=limit)

        elif "volume" in description:
            if "set" in description or "change" in description:
                level = context.get("level", 50)
                return await self.plugin_host.invoke_plugin_tool("system_control", "set_volume", level=level)
            else:
                return await self.plugin_host.invoke_plugin_tool("system_control", "get_volume")

        elif "brightness" in description:
            if "set" in description or "change" in description:
                level = context.get("level", 50)
                return await self.plugin_host.invoke_plugin_tool("system_control", "set_brightness", level=level)
            else:
                return await self.plugin_host.invoke_plugin_tool("system_control", "get_brightness")

        elif "shutdown" in description:
            delay = context.get("delay", 60)
            return await self.plugin_host.invoke_plugin_tool("system_control", "shutdown_system", delay=delay)

        elif "restart" in description:
            delay = context.get("delay", 60)
            return await self.plugin_host.invoke_plugin_tool("system_control", "restart_system", delay=delay)

        elif "sleep" in description:
            return await self.plugin_host.invoke_plugin_tool("system_control", "sleep_system")

        else:
            return {
                "success": False,
                "error": f"System control task not recognized: {description}",
                "available_commands": [
                    "system info", "cpu usage", "memory usage", "disk usage",
                    "list processes", "get/set volume", "get/set brightness",
                    "shutdown", "restart", "sleep"
                ]
            }

    async def _route_to_hello_plugin(self, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route task to hello plugin."""
        if not self.plugin_host:
            return {"success": False, "error": "Plugin host not available"}

        return await self.plugin_host.invoke_plugin_tool("os_hello", "say_hello")

    async def _route_to_file_operations(self, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route task to file operations plugin."""
        if not self.plugin_host:
            return {"success": False, "error": "Plugin host not available"}

        # Map keywords to specific file operation tools
        if "create file" in description or "file create" in description:
            file_path = context.get("file_path", context.get("path"))
            content = context.get("content", "")
            if not file_path:
                # Try to extract file path from description
                words = description.split()
                if len(words) >= 3:  # e.g., "file create hello.txt"
                    file_path = words[2]
                else:
                    return {"success": False, "error": "File path is required for creating files"}
            return await self.plugin_host.invoke_plugin_tool("file_operations", "create_file",
                                                             file_path=file_path, content=content)

        elif "read file" in description or "show file" in description or "file read" in description:
            file_path = context.get("file_path", context.get("path"))
            if not file_path:
                # Try to extract file path from description
                words = description.split()
                if len(words) >= 3:  # e.g., "file read hello.txt"
                    file_path = words[2]
                else:
                    return {"success": False, "error": "File path is required for reading files"}
            return await self.plugin_host.invoke_plugin_tool("file_operations", "read_file",
                                                             file_path=file_path)

        elif "update file" in description or "edit file" in description or "file update" in description or "file write" in description:
            file_path = context.get("file_path", context.get("path"))
            content = context.get("content", "")
            if not file_path:
                # Try to extract file path from description
                words = description.split()
                if len(words) >= 3:  # e.g., "file write hello.txt"
                    file_path = words[2]
                    # Try to extract content from remaining words or quotes
                    if len(words) > 3:
                        content = " ".join(words[3:])
                        # Handle quoted content
                        if content.startswith('"') and content.endswith('"'):
                            content = content[1:-1]
                else:
                    return {"success": False, "error": "File path is required for updating files"}
            return await self.plugin_host.invoke_plugin_tool("file_operations", "update_file",
                                                             file_path=file_path, content=content)

        elif "delete file" in description or "remove file" in description or "file delete" in description:
            file_path = context.get("file_path", context.get("path"))
            if not file_path:
                # Try to extract file path from description
                words = description.split()
                if len(words) >= 3:  # e.g., "file delete hello.txt"
                    file_path = words[2]
                else:
                    return {"success": False, "error": "File path is required for deleting files"}
            return await self.plugin_host.invoke_plugin_tool("file_operations", "delete_file",
                                                             file_path=file_path, confirm=True)

        elif "list files" in description or "list directory" in description or "list folder" in description:
            directory_path = context.get("directory_path", context.get("path", "."))
            return await self.plugin_host.invoke_plugin_tool("file_operations", "list_directory",
                                                             directory_path=directory_path)

        elif "create directory" in description or "create folder" in description:
            directory_path = context.get("directory_path", context.get("path"))
            if not directory_path:
                return {"success": False, "error": "Directory path is required for creating directories"}
            return await self.plugin_host.invoke_plugin_tool("file_operations", "create_directory",
                                                             directory_path=directory_path)

        elif "delete directory" in description or "remove directory" in description or "delete folder" in description:
            directory_path = context.get("directory_path", context.get("path"))
            if not directory_path:
                return {"success": False, "error": "Directory path is required for deleting directories"}
            return await self.plugin_host.invoke_plugin_tool("file_operations", "delete_directory",
                                                             directory_path=directory_path)

        elif "search files" in description or "find files" in description:
            directory_path = context.get("directory_path", context.get("path", "."))
            pattern = context.get("pattern", "*")
            return await self.plugin_host.invoke_plugin_tool("file_operations", "search_files",
                                                             directory_path=directory_path, pattern=pattern)

        elif "file info" in description or "file details" in description:
            file_path = context.get("file_path", context.get("path"))
            if not file_path:
                return {"success": False, "error": "File path is required for getting file info"}
            return await self.plugin_host.invoke_plugin_tool("file_operations", "get_file_info",
                                                             file_path=file_path)

        elif "copy file" in description:
            source_path = context.get("source_path", context.get("source"))
            destination_path = context.get("destination_path", context.get("destination"))
            if not source_path or not destination_path:
                return {"success": False, "error": "Source and destination paths are required for copying files"}
            return await self.plugin_host.invoke_plugin_tool("file_operations", "copy_file",
                                                             source_path=source_path, destination_path=destination_path)

        elif "move file" in description:
            source_path = context.get("source_path", context.get("source"))
            destination_path = context.get("destination_path", context.get("destination"))
            if not source_path or not destination_path:
                return {"success": False, "error": "Source and destination paths are required for moving files"}
            return await self.plugin_host.invoke_plugin_tool("file_operations", "move_file",
                                                             source_path=source_path, destination_path=destination_path)

        else:
            # List available file operations
            return {
                "success": False,
                "error": f"File operation not recognized: {description}",
                "available_operations": [
                    "create file", "read file", "update file", "delete file",
                    "list files/directory", "create directory", "delete directory",
                    "search files", "file info", "copy file", "move file"
                ]
            }

    async def _route_to_media_app_control(self, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route task to media & application control plugin."""
        if not self.plugin_host:
            return {"success": False, "error": "Plugin host not available"}

        # Media control routing
        if "play" in description and "media" in description:
            media_path = context.get("media_path", context.get("path"))
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "play_media",
                                                             media_path=media_path)

        elif "pause" in description:
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "pause_media")

        elif "stop" in description:
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "stop_media")

        elif "next track" in description or "next song" in description:
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "next_track")

        elif "previous track" in description or "previous song" in description:
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "previous_track")

        elif "volume up" in description:
            step = context.get("step", 5)
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "volume_up", step=step)

        elif "volume down" in description:
            step = context.get("step", 5)
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "volume_down", step=step)

        elif "mute" in description and "unmute" not in description:
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "mute_audio")

        elif "unmute" in description:
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "unmute_audio")

        elif "set volume" in description or "volume" in description:
            level = context.get("level", context.get("volume", 50))
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "set_volume", level=level)

        elif "volume status" in description or "get volume" in description:
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "get_volume_status")

        elif "media status" in description:
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "get_media_status")

        # Application control routing
        elif "launch" in description or "open" in description:
            application = context.get("application", context.get("app"))
            arguments = context.get("arguments", "")
            if not application:
                return {"success": False, "error": "Application name is required for launching applications"}
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "launch_application",
                                                             application=application, arguments=arguments)

        elif "close" in description and ("application" in description or "app" in description):
            application = context.get("application", context.get("app"))
            force = context.get("force", False)
            if not application:
                return {"success": False, "error": "Application name is required for closing applications"}
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "close_application",
                                                             application=application, force=force)

        elif "running applications" in description or "list applications" in description:
            detailed = context.get("detailed", False)
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "get_running_applications",
                                                             detailed=detailed)

        elif "installed applications" in description:
            category = context.get("category", "all")
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "list_installed_applications",
                                                             category=category)

        # Window management routing
        elif "focus window" in description or "focus" in description:
            window_title = context.get("window_title", context.get("title"))
            if not window_title:
                return {"success": False, "error": "Window title is required for focusing windows"}
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "focus_window",
                                                             window_title=window_title)

        elif "minimize window" in description or "minimize" in description:
            window_title = context.get("window_title", context.get("title"))
            if not window_title:
                return {"success": False, "error": "Window title is required for minimizing windows"}
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "minimize_window",
                                                             window_title=window_title)

        elif "maximize window" in description or "maximize" in description:
            window_title = context.get("window_title", context.get("title"))
            if not window_title:
                return {"success": False, "error": "Window title is required for maximizing windows"}
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "maximize_window",
                                                             window_title=window_title)

        elif "close window" in description:
            window_title = context.get("window_title", context.get("title"))
            if not window_title:
                return {"success": False, "error": "Window title is required for closing windows"}
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "close_window",
                                                             window_title=window_title)

        elif "window list" in description or "list windows" in description:
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "get_window_list")

        elif "active window" in description:
            return await self.plugin_host.invoke_plugin_tool("media_app_control", "get_active_window")

        else:
            # List available media/app operations
            return {
                "success": False,
                "error": f"Media/application operation not recognized: {description}",
                "available_operations": [
                    "play/pause/stop media", "volume up/down/mute/unmute", "next/previous track",
                    "launch/close application", "focus/minimize/maximize/close window",
                    "list running/installed applications", "get window list/active window"
                ]
            }

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a task.

        Args:
            task_id: Task identifier

        Returns:
            Task status information
        """
        return self._tasks.get(task_id, {"error": "Task not found"})

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "running": self._running,
            "total_tasks": len(self._tasks),
            "active_tasks": len([t for t in self._tasks.values() if t["status"] == "running"])
        }