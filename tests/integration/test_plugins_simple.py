"""
Simplified integration tests for all Friday AI Assistant plugins.
"""

import pytest
import asyncio
import tempfile
import os
import json
from pathlib import Path

# Import Friday components
from core.logging import initialize_logger
from plugins.loader import PluginLoader


class TestPluginsSimple:
    """Simplified integration tests for plugins."""

    @classmethod
    def setup_class(cls):
        """Set up logger for all tests."""
        logger_config = {
            "level": "INFO",
            "log_to_console": False,
            "log_to_file": False,
            "format": "simple"
        }
        initialize_logger(logger_config)

    @pytest.mark.asyncio
    async def test_system_control_plugin(self):
        """Test system control plugin integration."""
        loader = PluginLoader()
        plugin = await loader.load_plugin("system_control")

        assert plugin is not None
        assert plugin.id == "system_control"

        # Test basic system info
        result = plugin.invoke("get_system_info")
        assert result["success"] is True
        assert "platform" in result["data"]
        assert "cpu" in result["data"]

        # Test CPU usage
        result = plugin.invoke("get_cpu_usage")
        assert result["success"] is True
        assert "cpu_percent" in result["data"]

        # Test memory usage
        result = plugin.invoke("get_memory_usage")
        assert result["success"] is True
        assert "total" in result["data"]
        assert result["data"]["total"] > 0

        # Test process list
        result = plugin.invoke("list_processes", limit=5)
        assert result["success"] is True
        assert "processes" in result["data"]
        assert len(result["data"]["processes"]) <= 5

    @pytest.mark.asyncio
    async def test_file_operations_plugin(self):
        """Test file operations plugin integration."""
        loader = PluginLoader()
        plugin = await loader.load_plugin("file_operations")

        assert plugin is not None
        assert plugin.id == "file_operations"

        # Test file CRUD operations
        test_file = os.path.join(tempfile.gettempdir(), "friday_test_file.txt")
        test_content = "Integration test content"

        # Ensure file doesn't exist
        if os.path.exists(test_file):
            os.unlink(test_file)

        test_dir = None
        try:
            # Test create
            result = plugin.invoke("create_file", file_path=test_file, content=test_content)
            assert result["success"] is True

            # Test read
            result = plugin.invoke("read_file", file_path=test_file)
            assert result["success"] is True
            assert result["data"]["content"] == test_content

            # Test file info
            result = plugin.invoke("get_file_info", path=test_file)
            assert result["success"] is True
            assert "size" in result["data"]

            # Test directory operations
            test_dir = "/tmp/friday_test_dir"
            result = plugin.invoke("create_directory", directory_path=test_dir)
            assert result["success"] is True
            assert os.path.isdir(test_dir)

            # Test list directory
            result = plugin.invoke("list_directory", directory_path="/tmp")
            assert result["success"] is True
            assert "files" in result["data"]

        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.unlink(test_file)
            if test_dir and os.path.exists(test_dir):
                os.rmdir(test_dir)

    @pytest.mark.asyncio
    async def test_media_app_control_plugin(self):
        """Test media/app control plugin integration."""
        loader = PluginLoader()
        plugin = await loader.load_plugin("media_app_control")

        assert plugin is not None
        assert plugin.id == "media_app_control"

        # Test safe operations
        result = plugin.invoke("get_running_applications")
        assert result["success"] is True
        assert "applications" in result["data"]

        # Test media status (might fail if no media player)
        result = plugin.invoke("get_media_status")
        # Just check that it returns a result, success may vary
        assert "success" in result

        # Test volume status (might fail on some systems)
        result = plugin.invoke("get_volume_status")
        assert "success" in result

    @pytest.mark.asyncio
    async def test_all_plugins_together(self):
        """Test using all plugins in a workflow."""
        loader = PluginLoader()

        # Load all plugins
        system_plugin = await loader.load_plugin("system_control")
        file_plugin = await loader.load_plugin("file_operations")
        media_plugin = await loader.load_plugin("media_app_control")

        assert all([system_plugin, file_plugin, media_plugin])

        # Create a comprehensive system report
        with tempfile.TemporaryDirectory() as temp_dir:
            # Gather system info
            sys_info = system_plugin.invoke("get_system_info")
            cpu_usage = system_plugin.invoke("get_cpu_usage")
            processes = system_plugin.invoke("list_processes", limit=10)
            apps = media_plugin.invoke("get_running_applications")

            # Create report
            report = {
                "system_info": sys_info["data"] if sys_info["success"] else None,
                "cpu_usage": cpu_usage["data"] if cpu_usage["success"] else None,
                "processes": processes["data"] if processes["success"] else None,
                "applications": apps["data"] if apps["success"] else None,
            }

            # Save report
            report_file = os.path.join(temp_dir, "system_report.json")
            create_result = file_plugin.invoke(
                "create_file",
                file_path=report_file,
                content=json.dumps(report, indent=2)
            )
            assert create_result["success"] is True

            # Verify report
            read_result = file_plugin.invoke("read_file", file_path=report_file)
            assert read_result["success"] is True

            parsed_report = json.loads(read_result["data"]["content"])
            assert "system_info" in parsed_report
            assert "cpu_usage" in parsed_report

    @pytest.mark.asyncio
    async def test_plugin_tool_descriptions(self):
        """Test that all plugins properly describe their tools."""
        loader = PluginLoader()

        plugins = [
            ("system_control", await loader.load_plugin("system_control")),
            ("file_operations", await loader.load_plugin("file_operations")),
            ("media_app_control", await loader.load_plugin("media_app_control"))
        ]

        total_tools = 0
        for plugin_name, plugin in plugins:
            tools = plugin.describe_tools()
            assert isinstance(tools, dict)
            assert len(tools) > 0

            for tool_name, tool_desc in tools.items():
                assert "description" in tool_desc
                assert "parameters" in tool_desc
                assert "security_level" in tool_desc
                assert tool_desc["security_level"] in ["safe", "privileged"]

            total_tools += len(tools)
            print(f"{plugin_name}: {len(tools)} tools")

        print(f"Total tools across all plugins: {total_tools}")
        assert total_tools >= 15  # Should have many tools

    @pytest.mark.asyncio
    async def test_plugin_error_handling(self):
        """Test plugin error handling."""
        loader = PluginLoader()
        plugin = await loader.load_plugin("system_control")

        # Test invalid tool
        result = plugin.invoke("invalid_tool")
        assert result["success"] is False
        assert "error" in result

        # Test invalid parameters
        file_plugin = await loader.load_plugin("file_operations")
        result = file_plugin.invoke("read_file", file_path="/nonexistent/file.txt")
        assert result["success"] is False
        assert "error" in result

    def test_plugin_discovery(self):
        """Test plugin discovery."""
        # Check that plugin files exist
        plugin_dir = Path("plugins/available")
        plugin_files = []

        if plugin_dir.exists():
            for file_path in plugin_dir.glob("*.py"):
                if file_path.name != "__init__.py":
                    plugin_files.append(file_path.stem)

        expected_plugins = ["system_control", "file_operations", "media_app_control"]
        for plugin in expected_plugins:
            assert plugin in plugin_files, f"Plugin {plugin} not found"

        print(f"Found plugins: {plugin_files}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])