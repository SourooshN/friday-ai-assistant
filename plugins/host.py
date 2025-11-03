"""
Friday Plugin Host

Manages plugin lifecycle and provides runtime plugin management.
"""

from typing import Any, Dict, List

from core.logging import get_logger

from .loader import PluginLoader


class PluginHost:
    """
    Manages plugin lifecycle and execution.

    This is a skeleton implementation for Milestone 1.
    """

    def __init__(self, plugin_config: Dict[str, Any], policy_engine):
        self.config = plugin_config
        self.policy_engine = policy_engine
        self.logger = get_logger()
        self.loader = PluginLoader()

        # Plugin tracking
        self._loaded_plugins: Dict[str, Any] = {}
        self._enabled_plugins = set(plugin_config.get("enabled", []))

    async def load_enabled_plugins(self):
        """Load all enabled plugins."""
        self.logger.info("Loading enabled plugins...")

        for plugin_id in self._enabled_plugins:
            try:
                await self.load_plugin(plugin_id)
            except Exception as e:
                self.logger.error(f"Failed to load plugin {plugin_id}: {e}")

        self.logger.info(f"Loaded {len(self._loaded_plugins)} plugins")

    async def load_plugin(self, plugin_id: str):
        """Load a specific plugin."""
        if plugin_id in self._loaded_plugins:
            self.logger.warning(f"Plugin {plugin_id} already loaded")
            return

        plugin = await self.loader.load_plugin(plugin_id)
        if plugin:
            # Inject policy engine and memory manager if expected
            if hasattr(plugin, "policy_engine"):
                plugin.policy_engine = self.policy_engine
            if hasattr(plugin, "memory_manager") and hasattr(self, "memory_manager"):
                plugin.memory_manager = self.memory_manager

            self._loaded_plugins[plugin_id] = plugin
            self.logger.log_plugin_event(plugin_id, "loaded")

    async def invoke_plugin_tool(self, plugin_id: str, tool: str, **kwargs) -> Dict[str, Any]:
        """
        Invoke a tool from a plugin with policy checking.

        Args:
            plugin_id: Plugin identifier
            tool: Tool name to invoke
            **kwargs: Tool parameters

        Returns:
            Tool result with security validation
        """
        if plugin_id not in self._loaded_plugins:
            return {"success": False, "error": f"Plugin {plugin_id} not loaded"}

        plugin = self._loaded_plugins[plugin_id]

        # Get tool description for security level
        tools = plugin.describe_tools()
        if tool not in tools:
            return {"success": False, "error": f"Tool {tool} not found in plugin {plugin_id}"}

        tool_info = tools[tool]
        security_level = tool_info.get("security_level", "safe")

        # Check policy permissions
        policy_context = {"plugin_id": plugin_id, "tool_name": tool, "security_level": security_level, "parameters": kwargs}

        if not self.policy_engine.check_permission(action=f"plugin_tool_{tool}", resource=f"plugin_{plugin_id}", context=policy_context):
            return {"success": False, "error": f"Permission denied for tool {tool} in plugin {plugin_id}", "security_level": security_level}

        # Log tool invocation
        self.logger.log_tool_call(f"{plugin_id}.{tool}", kwargs, "pending")

        # Invoke the plugin tool
        try:
            result = plugin.invoke(tool, **kwargs)

            # Log successful invocation
            self.logger.log_tool_call(f"{plugin_id}.{tool}", kwargs, result)

            return result

        except Exception as e:
            error_result = {"success": False, "error": f"Plugin tool execution failed: {str(e)}"}

            # Log failed invocation
            self.logger.log_tool_call(f"{plugin_id}.{tool}", kwargs, error_result)

            return error_result

    async def unload_plugin(self, plugin_id: str):
        """Unload a specific plugin."""
        if plugin_id in self._loaded_plugins:
            del self._loaded_plugins[plugin_id]
            self.logger.log_plugin_event(plugin_id, "unloaded")

    async def shutdown_all_plugins(self):
        """Shutdown all loaded plugins."""
        self.logger.info("Shutting down all plugins...")

        for plugin_id in list(self._loaded_plugins.keys()):
            await self.unload_plugin(plugin_id)

        self.logger.info("All plugins shut down")

    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin IDs."""
        return list(self._loaded_plugins.keys())

    def get_status(self) -> Dict[str, Any]:
        """Get plugin host status."""
        return {
            "loaded_plugins": len(self._loaded_plugins),
            "enabled_plugins": list(self._enabled_plugins),
            "loaded_plugin_ids": list(self._loaded_plugins.keys()),
        }
