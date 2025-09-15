"""
Coding Agent for Friday AI Assistant
Handles code generation, analysis, and development tasks
"""

from typing import Any, Dict, List, Optional
from loguru import logger

from agents.base_agent import BaseAgent
from core.common_types import Task, TaskResult, AgentConfig, AgentCapability


class CodingAgent(BaseAgent):
    """Agent for software development and coding tasks"""
    
    def __init__(self, *args, **kwargs):
        # Initialize with coding-specific config
        if 'config' not in kwargs:
            kwargs['config'] = AgentConfig(
                name="CodingAgent",
                description="Software development and code generation specialist",
                capabilities=[
                    AgentCapability.CODING,
                    AgentCapability.DATA_ANALYSIS,
                    AgentCapability.PLANNING
                ],
                preferred_model="codellama:13b",
                require_confirmation=["execute_code", "modify_files"],
                tools=["git", "docker", "python", "nodejs"]
            )
        
        super().__init__(*args, **kwargs)
        logger.info("Initialized Coding Agent")

    async def can_handle(self, task: Task) -> bool:
        """Check if this agent can handle the task"""
        # Check task type
        if task.type in ["coding", "development", "debug", "refactor", "code_review"]:
            return True
        
        # Check keywords in description
        coding_keywords = ["code", "program", "script", "function", "class", "api", "debug", "implement"]
        task_text = f"{task.type} {task.description}".lower()
        
        return any(keyword in task_text for keyword in coding_keywords)

    async def _execute_task(self, task: Task) -> TaskResult:
        """Execute coding task"""
        logger.info(f"Coding Agent executing: {task.description}")
        
        # Use the code-specialized model
        prompt = f"""
You are an expert programmer. Complete this task:

Task: {task.description}
Parameters: {task.parameters}

Provide clean, well-commented code with explanations.
"""
        
        try:
            # Generate code using LLM
            response = await self.think(prompt, model=self.config.preferred_model)
            
            # For demonstration, return a structured result
            result = {
                "task": task.description,
                "code": response,
                "language": task.parameters.get("language", "python"),
                "status": "completed",
                "files_created": [],
                "notes": "Code generated successfully"
            }
            
            return TaskResult(
                task_id=task.id,
                success=True,
                result=result,
                metadata={
                    "model_used": self.config.preferred_model,
                    "tokens_generated": len(response.split()) if isinstance(response, str) else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Coding task failed: {e}")
            return TaskResult(
                task_id=task.id,
                success=False,
                result=None,
                error=str(e)
            )