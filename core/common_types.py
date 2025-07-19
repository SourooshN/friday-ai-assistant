"""
Common types and data structures for Friday AI Assistant
Shared across multiple modules to avoid circular imports
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentStatus(Enum):
    """Agent status enumeration"""
    IDLE = "idle"
    BUSY = "busy"
    THINKING = "thinking"
    EXECUTING = "executing"
    ERROR = "error"
    TERMINATED = "terminated"


class AgentCapability(Enum):
    """Agent capability enumeration"""
    CODING = "coding"
    CYBERSECURITY = "cybersecurity"
    WEB_AUTOMATION = "web_automation"
    SYSTEM_CONTROL = "system_control"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_CREATION = "content_creation"
    COMMUNICATION = "communication"
    PLANNING = "planning"


@dataclass
class Task:
    """Task representation"""
    id: str
    description: str
    type: str
    priority: int = 1
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TaskResult:
    """Task result representation"""
    task_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=datetime.now)


@dataclass
class AgentConfig:
    """Agent configuration"""
    name: str
    description: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    preferred_model: Optional[str] = None
    max_retries: int = 3
    timeout: int = 300
    require_confirmation: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)