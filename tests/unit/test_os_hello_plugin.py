"""
Unit tests for OS Hello Plugin
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.available.os_hello import PLUGIN_METADATA, OSHelloPlugin, create_plugin


class TestOSHelloPlugin(unittest.TestCase):
    """Test cases for OSHelloPlugin."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.plugin = OSHelloPlugin()

    def test_plugin_initialization(self):
        """Test plugin initialization."""
        self.assertEqual(self.plugin.id, "os_hello")
        self.assertEqual(self.plugin.version, "1.0.0")
        self.assertIn("greeting", self.plugin.capabilities)
        self.assertIn("os_automation", self.plugin.capabilities)

    def test_describe_tools(self):
        """Test the describe_tools method."""
        tools = self.plugin.describe_tools()

        # Check that say_hello tool is described
        self.assertIn("say_hello", tools)

        # Check tool structure
        say_hello_tool = tools["say_hello"]
        self.assertIn("description", say_hello_tool)
        self.assertIn("parameters", say_hello_tool)
        self.assertIn("returns", say_hello_tool)

        # Verify description content
        self.assertIn("Hello, Friday!", say_hello_tool["description"])

    @patch("builtins.print")
    def test_say_hello_execution(self, mock_print):
        """Test the say_hello tool execution."""
        result = self.plugin.invoke("say_hello")

        # Check that print was called with the correct message
        mock_print.assert_called_once_with("Hello, Friday!")

        # Check return value structure
        self.assertIsInstance(result, dict)
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Hello, Friday!")
        self.assertEqual(result["plugin_id"], "os_hello")
        self.assertEqual(result["plugin_version"], "1.0.0")

    def test_invoke_unknown_tool(self):
        """Test invoking an unknown tool."""
        result = self.plugin.invoke("unknown_tool")

        self.assertIsInstance(result, dict)
        self.assertFalse(result["success"])
        self.assertIn("Unknown tool", result["error"])
        self.assertIn("available_tools", result)

    @patch("builtins.print")
    @patch("plugins.available.os_hello.logger")
    def test_say_hello_with_logging(self, mock_logger, mock_print):
        """Test that say_hello logs the execution."""
        self.plugin.invoke("say_hello")

        # Verify logging was called
        mock_logger.info.assert_called()
        log_call = mock_logger.info.call_args[0][0]
        self.assertIn("OS Hello plugin executed", log_call)
        self.assertIn("Hello, Friday!", log_call)

    @patch("plugins.available.os_hello.OSHelloPlugin._say_hello")
    def test_invoke_exception_handling(self, mock_say_hello):
        """Test exception handling in invoke method."""
        # Make _say_hello raise an exception
        mock_say_hello.side_effect = Exception("Test exception")

        result = self.plugin.invoke("say_hello")

        self.assertIsInstance(result, dict)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Test exception")

    def test_create_plugin_factory(self):
        """Test the create_plugin factory function."""
        plugin = create_plugin()

        self.assertIsInstance(plugin, OSHelloPlugin)
        self.assertEqual(plugin.id, "os_hello")

    def test_plugin_metadata(self):
        """Test plugin metadata constants."""
        self.assertEqual(PLUGIN_METADATA["id"], "os_hello")
        self.assertEqual(PLUGIN_METADATA["name"], "OS Hello Plugin")
        self.assertEqual(PLUGIN_METADATA["version"], "1.0.0")
        self.assertIn("greeting", PLUGIN_METADATA["capabilities"])
        self.assertIn("os_automation", PLUGIN_METADATA["capabilities"])
        self.assertEqual(PLUGIN_METADATA["entry_point"], "create_plugin")

    def test_tool_invocation_with_kwargs(self):
        """Test tool invocation handles extra kwargs gracefully."""
        with patch("builtins.print") as mock_print:
            result = self.plugin.invoke("say_hello", extra_param="test", another_param=123)

            # Should still work despite extra parameters
            self.assertTrue(result["success"])
            mock_print.assert_called_once_with("Hello, Friday!")


class TestPluginIntegration(unittest.TestCase):
    """Integration tests for the plugin."""

    def test_plugin_interface_compliance(self):
        """Test that plugin complies with the expected interface."""
        plugin = OSHelloPlugin()

        # Check required attributes
        self.assertTrue(hasattr(plugin, "id"))
        self.assertTrue(hasattr(plugin, "version"))
        self.assertTrue(hasattr(plugin, "capabilities"))

        # Check required methods
        self.assertTrue(hasattr(plugin, "describe_tools"))
        self.assertTrue(hasattr(plugin, "invoke"))
        self.assertTrue(callable(plugin.describe_tools))
        self.assertTrue(callable(plugin.invoke))

        # Test method signatures work
        tools = plugin.describe_tools()
        self.assertIsInstance(tools, dict)

        result = plugin.invoke("say_hello")
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)


if __name__ == "__main__":
    unittest.main()
