"""
Friday Plugin Loader

Handles discovery and loading of plugins.
"""

import importlib.util
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logging import get_logger


class PluginLoader:
    """
    Discovers and loads plugins from the available plugins directory.

    This is a skeleton implementation for Milestone 1.
    """

    def __init__(self, plugins_dir: Optional[Path] = None):
        self.plugins_dir = plugins_dir or Path("plugins/available")
        self.logger = get_logger()

    async def discover_plugins(self) -> List[str]:
        """
        Discover available plugins.

        Returns:
            List of plugin IDs
        """
        plugin_ids = []

        if not self.plugins_dir.exists():
            self.logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return plugin_ids

        for item in self.plugins_dir.iterdir():
            if item.is_file() and item.suffix == ".py" and not item.name.startswith("_"):
                plugin_id = item.stem
                plugin_ids.append(plugin_id)

        self.logger.debug(f"Discovered {len(plugin_ids)} plugins: {plugin_ids}")
        return plugin_ids

    async def load_plugin(self, plugin_id: str) -> Optional[Any]:
        """
        Load a specific plugin by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin instance or None if loading failed
        """
        plugin_file = self.plugins_dir / f"{plugin_id}.py"

        if not plugin_file.exists():
            self.logger.error(f"Plugin file not found: {plugin_file}")
            return None

        try:
            # Load the plugin module
            spec = importlib.util.spec_from_file_location(plugin_id, plugin_file)
            if spec is None or spec.loader is None:
                self.logger.error(f"Could not load spec for plugin: {plugin_id}")
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Look for a create_plugin function or Plugin class
            if hasattr(module, "create_plugin"):
                plugin = module.create_plugin()
                self.logger.info(f"Loaded plugin: {plugin_id}")
                return plugin
            elif hasattr(module, "Plugin"):
                plugin = module.Plugin()
                self.logger.info(f"Loaded plugin: {plugin_id}")
                return plugin
            else:
                self.logger.error(f"Plugin {plugin_id} missing create_plugin() or Plugin class")
                return None

        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_id}: {e}")
            return None

    def get_plugin_info(self, plugin_id: str) -> Dict[str, Any]:
        """
        Get information about a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            Plugin metadata
        """
        plugin_file = self.plugins_dir / f"{plugin_id}.py"

        if not plugin_file.exists():
            return {"error": "Plugin not found"}

        # Basic file info for now
        stat = plugin_file.stat()
        return {
            "id": plugin_id,
            "file": str(plugin_file),
            "size": stat.st_size,
            "modified": stat.st_mtime
        }