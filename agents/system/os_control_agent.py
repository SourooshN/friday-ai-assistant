"""
OS Control Agent for Friday AI Assistant
Handles system operations and OS automation
"""

from typing import Any, Dict, List, Optional
from loguru import logger

from agents.base_agent import BaseAgent
from core.common_types import Task, TaskResult, AgentConfig, AgentCapability


class OSControlAgent(BaseAgent):
    """Agent for operating system control and automation"""
    
    def __init__(self, *args, **kwargs):
        # Initialize with OS control-specific config
        if 'config' not in kwargs:
            kwargs['config'] = AgentConfig(
                name="OSControlAgent",
                description="Operating system control and automation specialist",
                capabilities=[
                    AgentCapability.SYSTEM_CONTROL,
                    AgentCapability.DATA_ANALYSIS
                ],
                preferred_model="openhermes:latest",
                require_confirmation=["delete", "modify", "execute", "shutdown"],
                tools=["powershell", "cmd", "pyautogui", "psutil"]
            )
        
        super().__init__(*args, **kwargs)
        logger.info("Initialized OS Control Agent")

    async def can_handle(self, task: Task) -> bool:
        """Check if this agent can handle the task"""
        # Check task type
        if task.type in ["system_control", "file_operation", "process_management", "os_automation"]:
            return True
        
        # Check keywords
        os_keywords = ["file", "folder", "process", "system", "desktop", "window", "application"]
        task_text = f"{task.type} {task.description}".lower()
        
        return any(keyword in task_text for keyword in os_keywords)

    async def _execute_task(self, task: Task) -> TaskResult:
        """Execute OS control task"""
        logger.info(f"OS Control Agent executing: {task.description}")
        
        # Mock result for demonstration
        mock_result = {
            "task": task.description,
            "operation": task.parameters.get("operation", "info"),
            "target": task.parameters.get("target", "system"),
            "status": "completed",
            "details": {
                "os": "Windows 11",
                "user": "current_user",
                "action_taken": "Simulated OS operation"
            }
        }
        
        # Simulate work
        import asyncio
        await asyncio.sleep(1)
        
        return TaskResult(
            task_id=task.id,
            success=True,
            result=mock_result,
            metadata={"privileged": False, "safe_mode": True}
        )