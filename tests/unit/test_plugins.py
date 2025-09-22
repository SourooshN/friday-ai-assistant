"""
Unit tests for Friday Plugin System
"""

import pytest
import asyncio
from pathlib import Path

from plugins.loader import PluginLoader
from plugins.host import PluginHost
from core.policy.engine import PolicyEngine


class TestPluginSystem:
    """Test cases for the plugin system."""

    @pytest.fixture
    def mock_policy_engine(self):
        """Create a mock policy engine."""
        return PolicyEngine({"chain_of_trust": True})

    @pytest.fixture
    def plugin_host(self, mock_policy_engine):
        """Create a plugin host for testing."""
        config = {
            "enabled": ["os_hello"],
            "disabled": [],
            "auto_load": True
        }
        return PluginHost(config, mock_policy_engine)

    def test_plugin_loader_creation(self):
        """Test plugin loader can be created."""
        loader = PluginLoader()
        assert loader is not None

    @pytest.mark.asyncio
    async def test_plugin_discovery(self):
        """Test plugin discovery."""
        loader = PluginLoader()
        plugins = await loader.discover_plugins()
        assert isinstance(plugins, list)
        # Should find at least the os_hello plugin
        assert "os_hello" in plugins

    @pytest.mark.asyncio
    async def test_load_os_hello_plugin(self):
        """Test loading the os_hello plugin."""
        loader = PluginLoader()
        plugin = await loader.load_plugin("os_hello")

        assert plugin is not None
        assert hasattr(plugin, "id")
        assert hasattr(plugin, "describe_tools")
        assert hasattr(plugin, "invoke")

        # Test plugin functionality
        tools = plugin.describe_tools()
        assert "say_hello" in tools

        result = plugin.invoke("say_hello")
        assert result["success"] is True
        assert "Hello, Friday!" in result["message"]

    def test_plugin_host_creation(self, plugin_host):
        """Test plugin host can be created."""
        assert plugin_host is not None

    @pytest.mark.asyncio
    async def test_plugin_host_load_plugins(self, plugin_host):
        """Test plugin host can load enabled plugins."""
        await plugin_host.load_enabled_plugins()

        loaded = plugin_host.get_loaded_plugins()
        assert "os_hello" in loaded

        status = plugin_host.get_status()
        assert status["loaded_plugins"] > 0