"""
Friday Core Kernel Module

The kernel is the heart of Friday, responsible for:
- System lifecycle management
- Configuration management
- Security policy enforcement
- Plugin lifecycle management
- Resource monitoring
"""

from .kernel import FridayKernel
from .config import ConfigManager
from .lifecycle import LifecycleManager

__all__ = [
    "FridayKernel",
    "ConfigManager",
    "LifecycleManager"
]