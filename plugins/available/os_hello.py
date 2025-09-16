"""
OS Hello Plugin for Friday AI Assistant
A simple plugin that provides a greeting functionality by printing "Hello, Friday!"
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class OSHelloPlugin:
    """Simple plugin that provides a greeting functionality."""

    def __init__(self):
        """Initialize the OS Hello plugin."""
        self.id = "os_hello"
        self.version = "1.0.0"
        self.capabilities = ["greeting", "os_automation"]
        logger.info(f"Initialized {self.id} plugin v{self.version}")

    def describe_tools(self) -> Dict[str, Any]:
        """Describe the tools provided by this plugin.

        Returns:
            Dict containing tool descriptions and schemas.
        """
        return {
            "say_hello": {
                "description": "Print a greeting message 'Hello, Friday!'",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "returns": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "success": {"type": "boolean"}
                    }
                }
            }
        }

    def invoke(self, tool: str, **kwargs) -> Dict[str, Any]:
        """Invoke a tool provided by this plugin.

        Args:
            tool: The name of the tool to invoke
            **kwargs: Tool-specific parameters

        Returns:
            Dict containing the tool execution result
        """
        try:
            if tool == "say_hello":
                return self._say_hello(**kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool}",
                    "available_tools": list(self.describe_tools().keys())
                }
        except Exception as e:
            logger.error(f"Error invoking tool {tool}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _say_hello(self, **kwargs) -> Dict[str, Any]:
        """Execute the hello functionality.

        Returns:
            Dict containing the greeting result
        """
        greeting_message = "Hello, Friday!"
        print(greeting_message)
        logger.info(f"OS Hello plugin executed: {greeting_message}")

        return {
            "success": True,
            "message": greeting_message,
            "plugin_id": self.id,
            "plugin_version": self.version
        }


# Plugin factory function (optional, for plugin loader)
def create_plugin() -> OSHelloPlugin:
    """Factory function to create an instance of the OSHelloPlugin.

    Returns:
        An instance of OSHelloPlugin
    """
    return OSHelloPlugin()


# Plugin metadata for discovery
PLUGIN_METADATA = {
    "id": "os_hello",
    "name": "OS Hello Plugin",
    "version": "1.0.0",
    "description": "A simple plugin that provides greeting functionality",
    "author": "Friday AI Assistant",
    "capabilities": ["greeting", "os_automation"],
    "entry_point": "create_plugin"
}