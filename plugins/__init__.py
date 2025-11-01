"""
Friday Plugin System

Provides the plugin host and management functionality.
"""

from .host import PluginHost
from .loader import PluginLoader

__all__ = ["PluginHost", "PluginLoader"]
