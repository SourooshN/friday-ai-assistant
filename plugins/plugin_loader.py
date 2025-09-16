"""
Plugin Loader for Friday AI Assistant
Manages loading, unloading, and discovery of plugins
"""

import importlib
import importlib.util
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Type
import traceback

logger = logging.getLogger(__name__)


class PluginLoader:
    """Manages plugin loading and discovery for Friday AI Assistant."""

    def __init__(self, plugin_directory: str = "plugins/available"):
        """Initialize the plugin loader.

        Args:
            plugin_directory: Directory containing plugin files
        """
        self.plugin_directory = Path(plugin_directory)
        self.loaded_plugins: Dict[str, Any] = {}
        self.plugin_metadata: Dict[str, Dict] = {}
        logger.info(f"Plugin loader initialized with directory: {self.plugin_directory}")

    def discover_plugins(self) -> List[str]:
        """Discover available plugins in the plugin directory.

        Returns:
            List of plugin module names
        """
        plugins = []
        if not self.plugin_directory.exists():
            logger.warning(f"Plugin directory does not exist: {self.plugin_directory}")
            return plugins

        for file_path in self.plugin_directory.glob("*.py"):
            if file_path.name.startswith("__"):
                continue

            plugin_name = file_path.stem
            plugins.append(plugin_name)
            logger.debug(f"Discovered plugin: {plugin_name}")

        logger.info(f"Discovered {len(plugins)} plugins: {plugins}")
        return plugins

    def load_plugin(self, plugin_name: str) -> bool:
        """Load a specific plugin.

        Args:
            plugin_name: Name of the plugin to load

        Returns:
            True if plugin loaded successfully, False otherwise
        """
        if plugin_name in self.loaded_plugins:
            logger.info(f"Plugin {plugin_name} is already loaded")
            return True

        try:
            plugin_path = self.plugin_directory / f"{plugin_name}.py"
            if not plugin_path.exists():
                logger.error(f"Plugin file not found: {plugin_path}")
                return False

            # Load the module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None or spec.loader is None:
                logger.error(f"Could not create spec for plugin: {plugin_name}")
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get plugin metadata if available
            metadata = getattr(module, 'PLUGIN_METADATA', {})
            self.plugin_metadata[plugin_name] = metadata

            # Create plugin instance
            if hasattr(module, 'create_plugin'):
                plugin_instance = module.create_plugin()
            else:
                # Try to find a plugin class
                plugin_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        attr_name.lower().endswith('plugin') and
                        attr_name != 'Plugin'):
                        plugin_class = attr
                        break

                if plugin_class is None:
                    logger.error(f"No plugin class or create_plugin function found in {plugin_name}")
                    return False

                plugin_instance = plugin_class()

            self.loaded_plugins[plugin_name] = plugin_instance
            logger.info(f"Successfully loaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a specific plugin.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            True if plugin unloaded successfully, False otherwise
        """
        if plugin_name not in self.loaded_plugins:
            logger.warning(f"Plugin {plugin_name} is not loaded")
            return False

        try:
            # Call cleanup method if it exists
            plugin_instance = self.loaded_plugins[plugin_name]
            if hasattr(plugin_instance, 'cleanup'):
                plugin_instance.cleanup()

            del self.loaded_plugins[plugin_name]
            if plugin_name in self.plugin_metadata:
                del self.plugin_metadata[plugin_name]

            logger.info(f"Successfully unloaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False

    def load_all_plugins(self) -> Dict[str, bool]:
        """Load all discovered plugins.

        Returns:
            Dict mapping plugin names to their load success status
        """
        plugins = self.discover_plugins()
        results = {}

        for plugin_name in plugins:
            results[plugin_name] = self.load_plugin(plugin_name)

        loaded_count = sum(results.values())
        logger.info(f"Loaded {loaded_count}/{len(plugins)} plugins")
        return results

    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """Get a loaded plugin instance.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin instance or None if not loaded
        """
        return self.loaded_plugins.get(plugin_name)

    def list_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin names.

        Returns:
            List of loaded plugin names
        """
        return list(self.loaded_plugins.keys())

    def get_plugin_metadata(self, plugin_name: str) -> Dict[str, Any]:
        """Get metadata for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin metadata dict
        """
        return self.plugin_metadata.get(plugin_name, {})

    def invoke_plugin_tool(self, plugin_name: str, tool: str, **kwargs) -> Dict[str, Any]:
        """Invoke a tool from a loaded plugin.

        Args:
            plugin_name: Name of the plugin
            tool: Name of the tool to invoke
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        if plugin_name not in self.loaded_plugins:
            return {
                "success": False,
                "error": f"Plugin {plugin_name} is not loaded"
            }

        try:
            plugin_instance = self.loaded_plugins[plugin_name]
            if not hasattr(plugin_instance, 'invoke'):
                return {
                    "success": False,
                    "error": f"Plugin {plugin_name} does not support tool invocation"
                }

            return plugin_instance.invoke(tool, **kwargs)

        except Exception as e:
            logger.error(f"Error invoking tool {tool} from plugin {plugin_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }