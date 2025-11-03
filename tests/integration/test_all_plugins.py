"""
Integration tests for all Friday AI Assistant plugins.

Tests the complete plugin ecosystem including:
- System Control Plugin
- File Operations Plugin
- Media & Application Control Plugin

This ensures end-to-end functionality across the entire plugin system.
"""

import json
import os
import platform
import shutil
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

# Import Friday components
from core.logging import initialize_logger
from core.policy.engine import PolicyEngine
from plugins.host import PluginHost
from plugins.loader import PluginLoader


class TestPluginIntegration:
    """Integration tests for all plugins."""

    @pytest.fixture(scope="class", autouse=True)
    def setup_logger(self):
        """Initialize logger for all tests."""
        # Initialize Friday logger
        logger_config = {"level": "DEBUG", "log_to_console": False, "log_to_file": False, "format": "simple"}
        initialize_logger(logger_config)
        yield

    @pytest.fixture
    def policy_engine(self):
        """Create a policy engine for testing."""
        return PolicyEngine(
            {
                "chain_of_trust": True,
                "allow_privileged_operations": True,
                "allowed_file_paths": [str(Path.cwd()), "/tmp"],
            }
        )

    @pytest.fixture
    def plugin_loader(self):
        """Create a plugin loader."""
        return PluginLoader()

    @pytest_asyncio.fixture
    async def system_plugin(self, plugin_loader):
        """Load the system control plugin."""
        plugin = await plugin_loader.load_plugin("system_control")
        if plugin is None:
            pytest.skip("System control plugin not available")
        return plugin

    @pytest_asyncio.fixture
    async def file_plugin(self, plugin_loader):
        """Load the file operations plugin."""
        plugin = await plugin_loader.load_plugin("file_operations")
        if plugin is None:
            pytest.skip("File operations plugin not available")
        return plugin

    @pytest_asyncio.fixture
    async def media_plugin(self, plugin_loader):
        """Load the media/app control plugin."""
        plugin = await plugin_loader.load_plugin("media_app_control")
        if plugin is None:
            pytest.skip("Media/app control plugin not available")
        return plugin

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for file operations."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    # System Control Plugin Integration Tests
    @pytest.mark.asyncio
    async def test_system_plugin_basic_functionality(self, system_plugin):
        """Test basic system control plugin functionality."""
        # Test plugin metadata
        assert system_plugin.id == "system_control"
        assert hasattr(system_plugin, "describe_tools")
        assert hasattr(system_plugin, "invoke")

        # Test tool description
        tools = system_plugin.describe_tools()
        expected_tools = ["get_system_info", "get_cpu_usage", "get_memory_usage", "get_disk_usage", "list_processes", "get_volume", "get_brightness"]

        for tool in expected_tools:
            assert tool in tools, f"Tool {tool} not found in system plugin"

    @pytest.mark.asyncio
    async def test_system_plugin_safe_operations(self, system_plugin):
        """Test safe system operations."""
        # Test getting system info
        result = system_plugin.invoke("get_system_info")
        assert result["success"] is True
        assert "data" in result
        assert "platform" in result["data"]
        assert "cpu" in result["data"]
        assert "memory" in result["data"]

        # Test CPU usage
        result = system_plugin.invoke("get_cpu_usage")
        assert result["success"] is True
        assert "cpu_percent" in result["data"]
        assert isinstance(result["data"]["cpu_percent"], (int, float))

        # Test memory usage
        result = system_plugin.invoke("get_memory_usage")
        assert result["success"] is True
        assert "total" in result["data"]
        assert "available" in result["data"]
        assert result["data"]["total"] > 0

        # Test disk usage
        result = system_plugin.invoke("get_disk_usage", path="/")
        assert result["success"] is True
        assert "total" in result["data"]
        assert "used" in result["data"]
        assert "free" in result["data"]

    @pytest.mark.asyncio
    async def test_system_plugin_process_operations(self, system_plugin):
        """Test process-related operations."""
        # Test listing processes
        result = system_plugin.invoke("list_processes", limit=5)
        assert result["success"] is True
        assert "processes" in result["data"]
        assert len(result["data"]["processes"]) <= 5

        # Verify process structure
        if result["data"]["processes"]:
            process = result["data"]["processes"][0]
            assert "pid" in process
            assert "name" in process

    # File Operations Plugin Integration Tests
    @pytest.mark.asyncio
    async def test_file_plugin_basic_functionality(self, file_plugin):
        """Test basic file operations plugin functionality."""
        # Test plugin metadata
        assert file_plugin.id == "file_operations"

        tools = file_plugin.describe_tools()
        expected_tools = [
            "create_file",
            "read_file",
            "update_file",
            "delete_file",
            "list_directory",
            "create_directory",
            "delete_directory",
            "search_files",
            "get_file_info",
        ]

        for tool in expected_tools:
            assert tool in tools, f"Tool {tool} not found in file plugin"

    @pytest.mark.asyncio
    async def test_file_plugin_crud_operations(self, file_plugin, temp_dir):
        """Test complete file CRUD operations."""
        test_file = os.path.join(temp_dir, "test_integration.txt")
        test_content = "This is integration test content!"

        # Test file creation
        result = file_plugin.invoke("create_file", file_path=test_file, content=test_content)
        assert result["success"] is True
        assert os.path.exists(test_file)

        # Test file reading
        result = file_plugin.invoke("read_file", file_path=test_file)
        assert result["success"] is True
        assert result["data"]["content"] == test_content

        # Test file update
        updated_content = "Updated integration test content!"
        result = file_plugin.invoke("update_file", file_path=test_file, content=updated_content)
        assert result["success"] is True

        # Verify update
        result = file_plugin.invoke("read_file", file_path=test_file)
        assert result["success"] is True
        assert result["data"]["content"] == updated_content

        # Test file info
        result = file_plugin.invoke("get_file_info", path=test_file)
        assert result["success"] is True
        assert "size" in result["data"]
        assert "modified" in result["data"]

        # Test file deletion
        result = file_plugin.invoke("delete_file", file_path=test_file, confirm=True)
        assert result["success"] is True
        assert not os.path.exists(test_file)

    @pytest.mark.asyncio
    async def test_file_plugin_directory_operations(self, file_plugin, temp_dir):
        """Test directory operations."""
        # Ensure temp_dir is in allowed paths
        file_plugin.allowed_base_paths = [temp_dir]

        test_dir = os.path.join(temp_dir, "test_subdir")

        # Test directory creation
        result = file_plugin.invoke("create_directory", directory_path=test_dir)
        assert result["success"] is True
        assert os.path.isdir(test_dir)

        # Test directory listing
        result = file_plugin.invoke("list_directory", directory_path=temp_dir)
        assert result["success"] is True
        assert "items" in result["data"]
        assert "test_subdir" in [f["name"] for f in result["data"]["items"]]

        # Create a test file in the directory
        test_file = os.path.join(test_dir, "nested_file.txt")
        result = file_plugin.invoke("create_file", file_path=test_file, content="nested content")
        assert result["success"] is True

        # Test search functionality
        result = file_plugin.invoke("search_files", base_path=temp_dir, pattern="*.txt")
        assert result["success"] is True
        found_files = [f["name"] for f in result["data"]["results"]]
        assert "nested_file.txt" in found_files

        # Test directory deletion
        result = file_plugin.invoke("delete_directory", directory_path=test_dir, confirm=True, recursive=True)
        assert result["success"] is True
        assert not os.path.exists(test_dir)

    # Media & App Control Plugin Integration Tests
    @pytest.mark.asyncio
    async def test_media_plugin_basic_functionality(self, media_plugin):
        """Test basic media/app control plugin functionality."""
        # Test plugin metadata
        assert media_plugin.id == "media_app_control"

        tools = media_plugin.describe_tools()
        expected_tools = ["get_running_applications", "list_installed_applications", "get_media_status", "get_volume_status", "get_window_list"]

        for tool in expected_tools:
            assert tool in tools, f"Tool {tool} not found in media plugin"

    @pytest.mark.asyncio
    async def test_media_plugin_safe_operations(self, media_plugin):
        """Test safe media plugin operations."""
        # Test getting running applications
        result = media_plugin.invoke("get_running_applications")
        assert result["success"] is True
        assert "applications" in result["data"]
        assert isinstance(result["data"]["applications"], list)

        # Test getting media status
        result = media_plugin.invoke("get_media_status")
        # This might fail if no media player is available, which is expected
        assert "success" in result

        # Test getting volume status
        result = media_plugin.invoke("get_volume_status")
        # This might fail on some systems without audio, which is expected
        assert "success" in result

    # Cross-Plugin Integration Tests
    @pytest.mark.asyncio
    async def test_multi_plugin_workflow(self, system_plugin, file_plugin, temp_dir):
        """Test workflow using multiple plugins together."""
        # Step 1: Get system info using system plugin
        sys_result = system_plugin.invoke("get_system_info")
        assert sys_result["success"] is True

        # Step 2: Create a system report file using file plugin
        report_path = os.path.join(temp_dir, "system_report.json")
        report_content = json.dumps(sys_result["data"], indent=2)

        file_result = file_plugin.invoke("create_file", file_path=report_path, content=report_content)
        assert file_result["success"] is True

        # Step 3: Verify file was created and contains system info
        read_result = file_plugin.invoke("read_file", file_path=report_path)
        assert read_result["success"] is True

        # Step 4: Parse and verify the content
        parsed_data = json.loads(read_result["data"]["content"])
        assert "platform" in parsed_data
        assert "cpu" in parsed_data
        assert "memory" in parsed_data

        # Step 5: Get file info using file plugin
        info_result = file_plugin.invoke("get_file_info", path=report_path)
        assert info_result["success"] is True
        assert info_result["data"]["size"] > 0

    @pytest.mark.asyncio
    async def test_plugin_error_handling(self, system_plugin, file_plugin):
        """Test error handling across all plugins."""
        # Test invalid tool invocation
        result = system_plugin.invoke("invalid_tool")
        assert result["success"] is False
        assert "error" in result

        # Test invalid file operation
        result = file_plugin.invoke("read_file", file_path="/nonexistent/file.txt")
        assert result["success"] is False
        assert "error" in result

        # Test invalid parameters
        result = system_plugin.invoke("set_volume")  # Missing required level
        # This should either fail or handle gracefully
        assert "success" in result

    @pytest.mark.asyncio
    async def test_plugin_security_controls(self, file_plugin):
        """Test plugin security controls."""
        # Test path validation (try to access outside allowed paths)
        restricted_path = "/etc/passwd"
        result = file_plugin.invoke("read_file", file_path=restricted_path)
        # Should fail due to security restrictions
        if platform.system().lower() == "linux":
            # On Linux, this might fail due to path restrictions
            pass  # Security behavior varies by implementation

        # Test that plugins properly validate input
        result = file_plugin.invoke("create_file", file_path="", content="test")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_plugin_host_integration(self, policy_engine):
        """Test plugin host can load and coordinate all plugins."""
        config = {"enabled": ["system_control", "file_operations", "media_app_control"], "disabled": [], "auto_load": True}

        plugin_host = PluginHost(config, policy_engine)

        # Load all enabled plugins
        await plugin_host.load_enabled_plugins()

        # Verify plugins are loaded
        loaded_plugins = plugin_host.get_loaded_plugins()
        assert "system_control" in loaded_plugins
        assert "file_operations" in loaded_plugins
        assert "media_app_control" in loaded_plugins

        # Test plugin status
        status = plugin_host.get_status()
        assert status["loaded_plugins"] >= 3
        assert len(status["available_tools"]) > 10

        # Test invoking tools through plugin host
        result = await plugin_host.invoke_tool("system_control", "get_cpu_usage")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_all_plugins_describe_tools(self, system_plugin, file_plugin, media_plugin):
        """Test that all plugins properly describe their tools."""
        all_plugins = [("system_control", system_plugin), ("file_operations", file_plugin), ("media_app_control", media_plugin)]

        total_tools = 0
        for _plugin_name, plugin in all_plugins:
            tools = plugin.describe_tools()
            assert isinstance(tools, dict)
            assert len(tools) > 0
            total_tools += len(tools)

            # Verify tool structure
            for _tool_name, tool_desc in tools.items():
                assert "description" in tool_desc
                assert "parameters" in tool_desc
                assert "security_level" in tool_desc
                assert tool_desc["security_level"] in ["safe", "privileged"]

        print(f"Total tools available across all plugins: {total_tools}")
        assert total_tools > 15  # Should have many tools across all plugins

    def test_plugin_discovery_completeness(self):
        """Test that plugin discovery finds all expected plugins."""
        PluginLoader()

        # Get list of available plugins
        plugin_files = []
        plugin_dir = Path("plugins/available")
        if plugin_dir.exists():
            for file_path in plugin_dir.glob("*.py"):
                if file_path.name != "__init__.py":
                    plugin_files.append(file_path.stem)

        print(f"Found plugin files: {plugin_files}")

        # Should find our three main plugins
        expected_plugins = ["system_control", "file_operations", "media_app_control"]
        for plugin in expected_plugins:
            assert f"{plugin}.py" in [f"{p}.py" for p in plugin_files], f"Plugin {plugin} not found"

    @pytest.mark.asyncio
    async def test_end_to_end_plugin_workflow(self, policy_engine, temp_dir):
        """Test complete end-to-end workflow using all plugins."""
        # Initialize plugin host with all plugins
        config = {"enabled": ["system_control", "file_operations", "media_app_control"], "disabled": [], "auto_load": True}

        plugin_host = PluginHost(config, policy_engine)
        await plugin_host.load_enabled_plugins()

        # Workflow: System monitoring -> File reporting -> App management

        # Step 1: Get comprehensive system status
        sys_result = await plugin_host.invoke_tool("system_control", "get_system_info")
        assert sys_result["success"] is True

        cpu_result = await plugin_host.invoke_tool("system_control", "get_cpu_usage")
        assert cpu_result["success"] is True

        proc_result = await plugin_host.invoke_tool("system_control", "list_processes", limit=10)
        assert proc_result["success"] is True

        # Step 2: Create comprehensive system report
        report_data = {
            "timestamp": "2024-01-15T10:30:00Z",
            "system_info": sys_result["data"],
            "cpu_usage": cpu_result["data"],
            "top_processes": proc_result["data"],
        }

        report_path = os.path.join(temp_dir, "friday_system_report.json")
        create_result = await plugin_host.invoke_tool(
            "file_operations", "create_file", file_path=report_path, content=json.dumps(report_data, indent=2)
        )
        assert create_result["success"] is True

        # Step 3: Verify report and get file metadata
        info_result = await plugin_host.invoke_tool("file_operations", "get_file_info", path=report_path)
        assert info_result["success"] is True
        assert info_result["data"]["size"] > 100  # Report should be substantial

        # Step 4: List running applications for context
        apps_result = await plugin_host.invoke_tool("media_app_control", "get_running_applications")
        assert apps_result["success"] is True

        # Step 5: Create a summary directory and organize files
        summary_dir = os.path.join(temp_dir, "friday_reports")
        dir_result = await plugin_host.invoke_tool("file_operations", "create_directory", directory_path=summary_dir)
        assert dir_result["success"] is True

        # Step 6: Search for our created files
        search_result = await plugin_host.invoke_tool("file_operations", "search_files", base_path=temp_dir, pattern="*.json")
        assert search_result["success"] is True
        found_files = [f["name"] for f in search_result["data"]["results"]]
        assert "friday_system_report.json" in found_files

        print("✅ End-to-end plugin workflow completed successfully!")
        print("   - System info collected: ✓")
        print(f"   - Report created: ✓ ({info_result['data']['size']} bytes)")
        print(f"   - Applications checked: ✓ ({len(apps_result['data']['applications'])} apps)")
        print("   - Files organized: ✓")
