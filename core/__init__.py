"""
Friday AI Assistant - Core Module

The core module contains the kernel, orchestrator, and foundational components
of the Friday AI Assistant system.
"""

from .kernel import FridayKernel
from .logging import get_logger, initialize_logger
from .orchestrator import TaskOrchestrator

__all__ = ["FridayKernel", "TaskOrchestrator", "get_logger", "initialize_logger"]
