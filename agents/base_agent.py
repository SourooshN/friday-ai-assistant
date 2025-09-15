"""
Base Agent class that all specialized agents inherit from.
Provides common functionality for task execution, memory, and model interaction.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import traceback

from core.models.model_manager import ModelManager
from core.memory.short_term import ShortTermMemory
from core.security.policy_engine import PolicyEngine


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    """Types of tasks agents can handle."""
    ANALYSIS = "analysis"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    PLANNING = "planning"
    COMMUNICATION = "communication"


class Task:
    """Represents a task to be executed by an agent."""
    def __init__(self, id: str, type: TaskType, description: str, 
                 data: Optional[Dict[str, Any]] = None,
                 priority: int = 5):
        self.id = id
        self.type = type
        self.description = description
        self.data = data or {}
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.result: Optional[Dict[str, Any]] = None
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None


class BaseAgent(ABC):
    """Base class for all agents in the Friday system."""
    
    def __init__(self, name: str, capabilities: List[str], 
                 model_manager: ModelManager,
                 memory: ShortTermMemory,
                 policy_engine: PolicyEngine,
                 max_retries: int = 3):
        """Initialize base agent."""
        self.name = name
        self.capabilities = capabilities
        self.model_manager = model_manager
        self.memory = memory
        self.policy_engine = policy_engine
        self.max_retries = max_retries
        self.logger = logging.getLogger(self.__class__.__name__)
        self.is_running = False
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._current_task: Optional[Task] = None
        
        self.logger.info(f"Initialized {name} agent")
    
    async def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a task with retries and error handling."""
        self.logger.info(f"Executing task: {task.id} - {task.description}")
        
        try:
            # Start status update
            status_task = asyncio.create_task(self._update_status_periodically(task.id))
            
            # Prepare task data for execution
            if hasattr(task, 'data') and isinstance(task.data, dict):
                task_data = task.data
            else:
                # Create a proper task data dictionary
                task_data = {
                    'task_id': task.id,
                    'description': task.description,
                    'type': task.type.value if hasattr(task.type, 'value') else str(task.type),
                    'context': getattr(task, 'context', {}),
                    'parameters': getattr(task, 'parameters', {})
                }
            
            # Execute with retries
            result = await self._execute_with_retries(
                task_func=lambda: self._execute_task(task_data),
                task_id=task.id,
                max_retries=self.max_retries
            )
            
            # Cancel status updates
            status_task.cancel()
            try:
                await status_task
            except asyncio.CancelledError:
                pass
            
            # Record metrics
            end_time = datetime.now()
            execution_time = (end_time - task.created_at).total_seconds()
            
            await self.memory.store(
                key=f"task_metrics_{task.id}",
                value={
                    'execution_time': execution_time,
                    'success': True,
                    'agent': self.name
                },
                metadata={'type': 'task_metrics'}
            )
            
            # Update task status
            task.status = TaskStatus.COMPLETED
            task.result = result
            
            self.logger.info(f"Task {task.id} completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Task {task.id} failed: {str(e)}")
            task.status = TaskStatus.FAILED
            task.result = {'error': str(e)}
            
            # Store failure metrics
            await self.memory.store(
                key=f"task_metrics_{task.id}",
                value={
                    'execution_time': -1,
                    'success': False,
                    'error': str(e),
                    'agent': self.name
                },
                metadata={'type': 'task_metrics'}
            )
            
            raise
    
    @abstractmethod
    async def _execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual task logic. Must be implemented by subclasses."""
        pass
    
    async def _execute_with_retries(self, task_func: Callable, task_id: str, 
                                    max_retries: int) -> Dict[str, Any]:
        """Execute a task with retries on failure."""
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                # Check policy before execution
                if not await self._check_policy(task_id):
                    raise PermissionError(f"Task {task_id} blocked by policy")
                
                # Execute task
                result = await task_func()
                
                # Validate result
                if not isinstance(result, dict):
                    raise ValueError(f"Task must return a dictionary, got {type(result)}")
                
                return result
                
            except Exception as e:
                last_error = e
                self.logger.error(f"Error in attempt {attempt}: {str(e)}")
                
                if attempt < max_retries:
                    # Exponential backoff
                    wait_time = 2 ** (attempt - 1)
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    break
        
        # All retries failed
        raise Exception(f"Failed after {max_retries} attempts. Last error: {str(last_error)}")
    
    async def _check_policy(self, task_id: str) -> bool:
        """Check if task execution is allowed by policy."""
        # For now, always allow. Will be enhanced with actual policy checks
        return True
    
    async def _update_status_periodically(self, task_id: str):
        """Update task status in memory periodically."""
        try:
            while True:
                await self.memory.store(
                    key=f"task_status_{task_id}",
                    value={
                        'status': 'running',
                        'agent': self.name,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata={'type': 'task_status'}
                )
                await asyncio.sleep(5)  # Update every 5 seconds
        except asyncio.CancelledError:
            # Task completed, update final status
            await self.memory.store(
                key=f"task_status_{task_id}",
                value={
                    'status': 'completed',
                    'agent': self.name,
                    'timestamp': datetime.now().isoformat()
                },
                metadata={'type': 'task_status'}
            )
            raise
    
    def can_handle(self, task_type: str) -> bool:
        """Check if this agent can handle a specific task type."""
        return any(cap in task_type.lower() for cap in self.capabilities)
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        metrics = await self._get_performance_metrics()
        
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'capabilities': self.capabilities,
            'is_running': self.is_running,
            'current_task': self._current_task.id if self._current_task else None,
            'queue_size': self._task_queue.qsize(),
            'metrics': metrics
        }
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics from memory."""
        # Retrieve all task metrics for this agent
        metrics_keys = await self.memory.search(
            query=f"agent:{self.name}",
            filter_metadata={'type': 'task_metrics'}
        )
        
        if not metrics_keys:
            return {
                'total_tasks': 0,
                'successful_tasks': 0,
                'failed_tasks': 0,
                'average_execution_time': 0
            }
        
        total_tasks = len(metrics_keys)
        successful_tasks = 0
        failed_tasks = 0
        total_time = 0
        
        for key in metrics_keys:
            metric = await self.memory.retrieve(key)
            if metric and isinstance(metric, dict):
                if metric.get('success', False):
                    successful_tasks += 1
                    exec_time = metric.get('execution_time', 0)
                    if exec_time > 0:
                        total_time += exec_time
                else:
                    failed_tasks += 1
        
        avg_time = total_time / successful_tasks if successful_tasks > 0 else 0
        
        return {
            'total_tasks': total_tasks,
            'successful_tasks': successful_tasks,
            'failed_tasks': failed_tasks,
            'average_execution_time': round(avg_time, 2),
            'success_rate': round(successful_tasks / total_tasks * 100, 2) if total_tasks > 0 else 0
        }
    
    async def shutdown(self):
        """Cleanup agent resources."""
        self.logger.info(f"Shutting down agent {self.name}")
        self.is_running = False
        
        # Clear task queue
        while not self._task_queue.empty():
            try:
                self._task_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        # Any other cleanup needed
        await self._cleanup()
    
    async def _cleanup(self):
        """Additional cleanup to be implemented by subclasses if needed."""
        pass