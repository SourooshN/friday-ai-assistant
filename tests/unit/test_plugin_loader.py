"""
Unit tests for Plugin Loader
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from plugins.plugin_loader import PluginLoader


class TestPluginLoader(unittest.TestCase):
    """Test cases for PluginLoader."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.plugin_loader = PluginLoader(self.temp_dir)

    def tearDown(self):
        """Clean up after tests."""
        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test plugin loader initialization."""
        loader = PluginLoader("test/path")
        self.assertEqual(str(loader.plugin_directory), "test/path")
        self.assertEqual(loader.loaded_plugins, {})
        self.assertEqual(loader.plugin_metadata, {})

    def test_discover_plugins_empty_directory(self):
        """Test discovering plugins in empty directory."""
        plugins = self.plugin_loader.discover_plugins()
        self.assertEqual(plugins, [])

    def test_discover_plugins_with_files(self):
        """Test discovering plugins with Python files."""
        # Create test plugin files
        test_files = ["plugin1.py", "plugin2.py", "__init__.py", "not_python.txt"]

        for filename in test_files:
            file_path = Path(self.temp_dir) / filename
            file_path.touch()

        plugins = self.plugin_loader.discover_plugins()

        # Should find plugin1 and plugin2, but not __init__.py or .txt files
        expected = ["plugin1", "plugin2"]
        self.assertEqual(sorted(plugins), sorted(expected))

    def test_discover_plugins_nonexistent_directory(self):
        """Test discovering plugins when directory doesn't exist."""
        loader = PluginLoader("nonexistent/path")
        plugins = loader.discover_plugins()
        self.assertEqual(plugins, [])

    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    def test_load_plugin_success(self, mock_module_from_spec, mock_spec_from_file):
        """Test successful plugin loading."""
        # Setup mocks
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file.return_value = mock_spec

        mock_module = MagicMock()
        mock_module.PLUGIN_METADATA = {"id": "test_plugin"}
        mock_module.create_plugin.return_value = MagicMock()
        mock_module_from_spec.return_value = mock_module

        # Create test plugin file
        plugin_file = Path(self.temp_dir) / "test_plugin.py"
        plugin_file.touch()

        # Test loading
        result = self.plugin_loader.load_plugin("test_plugin")

        self.assertTrue(result)
        self.assertIn("test_plugin", self.plugin_loader.loaded_plugins)
        self.assertIn("test_plugin", self.plugin_loader.plugin_metadata)

    def test_load_plugin_file_not_found(self):
        """Test loading plugin when file doesn't exist."""
        result = self.plugin_loader.load_plugin("nonexistent_plugin")
        self.assertFalse(result)

    def test_load_plugin_already_loaded(self):
        """Test loading plugin that's already loaded."""
        # Manually add a plugin to loaded_plugins
        mock_plugin = MagicMock()
        self.plugin_loader.loaded_plugins["existing_plugin"] = mock_plugin

        result = self.plugin_loader.load_plugin("existing_plugin")
        self.assertTrue(result)

    def test_unload_plugin_success(self):
        """Test successful plugin unloading."""
        # Add a plugin with cleanup method
        mock_plugin = MagicMock()
        mock_plugin.cleanup = MagicMock()
        self.plugin_loader.loaded_plugins["test_plugin"] = mock_plugin
        self.plugin_loader.plugin_metadata["test_plugin"] = {}

        result = self.plugin_loader.unload_plugin("test_plugin")

        self.assertTrue(result)
        mock_plugin.cleanup.assert_called_once()
        self.assertNotIn("test_plugin", self.plugin_loader.loaded_plugins)
        self.assertNotIn("test_plugin", self.plugin_loader.plugin_metadata)

    def test_unload_plugin_not_loaded(self):
        """Test unloading plugin that's not loaded."""
        result = self.plugin_loader.unload_plugin("nonexistent_plugin")
        self.assertFalse(result)

    def test_get_plugin(self):
        """Test getting a loaded plugin."""
        mock_plugin = MagicMock()
        self.plugin_loader.loaded_plugins["test_plugin"] = mock_plugin

        result = self.plugin_loader.get_plugin("test_plugin")
        self.assertEqual(result, mock_plugin)

        # Test getting non-existent plugin
        result = self.plugin_loader.get_plugin("nonexistent")
        self.assertIsNone(result)

    def test_list_loaded_plugins(self):
        """Test listing loaded plugins."""
        self.plugin_loader.loaded_plugins = {"plugin1": MagicMock(), "plugin2": MagicMock()}

        result = self.plugin_loader.list_loaded_plugins()
        self.assertEqual(sorted(result), ["plugin1", "plugin2"])

    def test_get_plugin_metadata(self):
        """Test getting plugin metadata."""
        test_metadata = {"id": "test", "version": "1.0.0"}
        self.plugin_loader.plugin_metadata["test_plugin"] = test_metadata

        result = self.plugin_loader.get_plugin_metadata("test_plugin")
        self.assertEqual(result, test_metadata)

        # Test getting metadata for non-existent plugin
        result = self.plugin_loader.get_plugin_metadata("nonexistent")
        self.assertEqual(result, {})

    def test_invoke_plugin_tool_success(self):
        """Test successful plugin tool invocation."""
        mock_plugin = MagicMock()
        mock_plugin.invoke.return_value = {"success": True, "result": "test"}
        self.plugin_loader.loaded_plugins["test_plugin"] = mock_plugin

        result = self.plugin_loader.invoke_plugin_tool("test_plugin", "test_tool", param="value")

        self.assertEqual(result, {"success": True, "result": "test"})
        mock_plugin.invoke.assert_called_once_with("test_tool", param="value")

    def test_invoke_plugin_tool_plugin_not_loaded(self):
        """Test invoking tool from unloaded plugin."""
        result = self.plugin_loader.invoke_plugin_tool("nonexistent", "test_tool")

        self.assertFalse(result["success"])
        self.assertIn("not loaded", result["error"])

    def test_invoke_plugin_tool_no_invoke_method(self):
        """Test invoking tool from plugin without invoke method."""
        mock_plugin = MagicMock()
        del mock_plugin.invoke  # Remove invoke method
        self.plugin_loader.loaded_plugins["test_plugin"] = mock_plugin

        result = self.plugin_loader.invoke_plugin_tool("test_plugin", "test_tool")

        self.assertFalse(result["success"])
        self.assertIn("does not support tool invocation", result["error"])

    @patch("plugins.plugin_loader.logger")
    def test_invoke_plugin_tool_exception(self, mock_logger):
        """Test exception handling in tool invocation."""
        mock_plugin = MagicMock()
        mock_plugin.invoke.side_effect = Exception("Test exception")
        self.plugin_loader.loaded_plugins["test_plugin"] = mock_plugin

        result = self.plugin_loader.invoke_plugin_tool("test_plugin", "test_tool")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Test exception")
        mock_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()
