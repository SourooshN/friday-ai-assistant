"""
Core module for Friday AI Assistant
"""

# Export common types to avoid circular imports
from .common_types import (
    AgentStatus,
    AgentCapability,
    AgentConfig,
    Task,
    TaskResult
)

__all__ = [
    'AgentStatus',
    'AgentCapability', 
    'AgentConfig',
    'Task',
    'TaskResult'
]