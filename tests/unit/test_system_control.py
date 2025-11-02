"""
Unit tests for System Control Plugin
"""

# Import the plugin
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import psutil
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "available"))

from system_control import SystemControlPlugin, create_plugin


class TestSystemControlPlugin:
    """Test cases for the System Control Plugin."""

    @pytest.fixture
    def plugin(self):
        """Create a system control plugin instance."""
        return SystemControlPlugin()

    def test_plugin_creation(self, plugin):
        """Test plugin can be created."""
        assert plugin.id == "system_control"
        assert plugin.version == "1.0.0"
        assert isinstance(plugin.capabilities, list)
        assert len(plugin.capabilities) > 0

    def test_factory_function(self):
        """Test the factory function works."""
        plugin = create_plugin()
        assert isinstance(plugin, SystemControlPlugin)
        assert plugin.id == "system_control"

    def test_describe_tools(self, plugin):
        """Test plugin tool description."""
        tools = plugin.describe_tools()

        # Check that all expected tools are present
        expected_tools = [
            "get_system_info",
            "get_cpu_usage",
            "get_memory_usage",
            "get_disk_usage",
            "list_processes",
            "get_volume",
            "set_volume",
            "get_brightness",
            "set_brightness",
            "shutdown_system",
            "restart_system",
            "sleep_system",
            "kill_process",
        ]

        for tool in expected_tools:
            assert tool in tools
            assert "description" in tools[tool]
            assert "parameters" in tools[tool]
            assert "security_level" in tools[tool]

    def test_allowed_operations(self, plugin):
        """Test platform-specific allowed operations."""
        safe_ops = plugin.allowed_operations.get("safe", [])
        privileged_ops = plugin.allowed_operations.get("privileged", [])

        assert len(safe_ops) > 0
        assert "get_system_info" in safe_ops
        assert "get_cpu_usage" in safe_ops

        # Privileged operations should exist for supported platforms
        if plugin.platform in ["linux", "windows"]:
            assert len(privileged_ops) > 0

    def test_unknown_tool(self, plugin):
        """Test handling of unknown tools."""
        result = plugin.invoke("nonexistent_tool")

        assert result["success"] is False
        assert ("Unknown tool" in result["error"] or "not allowed" in result["error"])

    # System Information Tests
    def test_get_system_info(self, plugin):
        """Test system information gathering."""
        result = plugin.invoke("get_system_info")

        assert result["success"] is True
        assert "data" in result

        data = result["data"]
        assert "platform" in data
        assert "cpu" in data
        assert "memory" in data
        assert "disk" in data

    def test_get_cpu_usage(self, plugin):
        """Test CPU usage retrieval."""
        with patch("psutil.cpu_percent") as mock_cpu:
            mock_cpu.return_value = 25.0

            result = plugin.invoke("get_cpu_usage")

            assert result["success"] is True
            assert "data" in result
            assert "cpu_percent" in result["data"]

    def test_get_memory_usage(self, plugin):
        """Test memory usage retrieval."""
        # Mock psutil.virtual_memory
        mock_memory = Mock()
        mock_memory.total = 8589934592  # 8GB
        mock_memory.available = 4294967296  # 4GB
        mock_memory.used = 4294967296  # 4GB
        mock_memory.free = 4294967296  # 4GB
        mock_memory.percent = 50.0

        with patch("psutil.virtual_memory", return_value=mock_memory):
            result = plugin.invoke("get_memory_usage")

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["percentage"] == 50.0

    def test_get_disk_usage_valid_path(self, plugin):
        """Test disk usage for valid path."""
        # Mock psutil.disk_usage
        mock_usage = Mock()
        mock_usage.total = 1000000000  # 1GB
        mock_usage.used = 500000000  # 500MB
        mock_usage.free = 500000000  # 500MB

        with patch("psutil.disk_usage", return_value=mock_usage), patch("os.path.exists", return_value=True):

            result = plugin.invoke("get_disk_usage", path="/")

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["percentage"] == 50.0

    def test_get_disk_usage_invalid_path(self, plugin):
        """Test disk usage for invalid path."""
        with patch("os.path.exists", return_value=False):
            result = plugin.invoke("get_disk_usage", path="/nonexistent")

            assert result["success"] is False
            assert "does not exist" in result["error"]

    # Process Management Tests
    def test_list_processes(self, plugin):
        """Test process listing."""
        # Mock psutil.process_iter
        mock_processes = [
            Mock(info={"pid": 1, "name": "init", "cpu_percent": 0.1, "memory_percent": 0.1}),
            Mock(info={"pid": 2, "name": "kthreadd", "cpu_percent": 0.0, "memory_percent": 0.0}),
        ]

        with patch("psutil.process_iter", return_value=mock_processes):
            result = plugin.invoke("list_processes", limit=10)

            assert result["success"] is True
            assert "data" in result
            assert "processes" in result["data"]
            assert len(result["data"]["processes"]) <= 10

    def test_kill_process_no_pid(self, plugin):
        """Test kill process without PID."""
        result = plugin.invoke("kill_process")

        assert result["success"] is False
        assert "PID is required" in result["error"]

    def test_kill_process_nonexistent(self, plugin):
        """Test kill process with nonexistent PID."""
        with patch("psutil.Process") as mock_process_class:
            mock_process_class.side_effect = psutil.NoSuchProcess(99999)

            result = plugin.invoke("kill_process", pid=99999)

            assert result["success"] is False
            assert "not found" in result["error"]

    def test_kill_process_success(self, plugin):
        """Test successful process termination."""
        mock_process = Mock()
        mock_process.name.return_value = "test_process"
        mock_process.is_running.return_value = False

        with patch("psutil.Process", return_value=mock_process), patch("time.sleep"):

            result = plugin.invoke("kill_process", pid=12345)

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["pid"] == 12345

    # Power Management Tests
    @patch("subprocess.run")
    def test_shutdown_system_linux(self, mock_run, plugin):
        """Test system shutdown on Linux."""
        plugin.platform = "linux"
        mock_run.return_value = Mock()

        result = plugin.invoke("shutdown_system", delay=120)

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["delay_seconds"] == 120
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_restart_system_linux(self, mock_run, plugin):
        """Test system restart on Linux."""
        plugin.platform = "linux"
        mock_run.return_value = Mock()

        result = plugin.invoke("restart_system", delay=60)

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["delay_seconds"] == 60
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_sleep_system_linux(self, mock_run, plugin):
        """Test system sleep on Linux."""
        plugin.platform = "linux"
        mock_run.return_value = Mock()

        result = plugin.invoke("sleep_system")

        assert result["success"] is True
        assert "data" in result
        mock_run.assert_called_once()

    def test_power_management_unsupported_platform(self, plugin):
        """Test power management on unsupported platform."""
        plugin.platform = "unsupported"

        result = plugin.invoke("shutdown_system")

        assert result["success"] is False
        assert "not supported" in result["error"]

    # Volume Control Tests
    @patch("subprocess.run")
    def test_get_volume_linux(self, mock_run, plugin):
        """Test volume retrieval on Linux."""
        plugin.platform = "linux"
        mock_run.return_value = Mock(stdout="[75%]")

        result = plugin.invoke("get_volume")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["volume_percent"] == 75

    @patch("subprocess.run")
    def test_set_volume_linux(self, mock_run, plugin):
        """Test volume setting on Linux."""
        plugin.platform = "linux"
        mock_run.return_value = Mock()

        result = plugin.invoke("set_volume", level=50)

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["level"] == 50

    def test_set_volume_invalid_level(self, plugin):
        """Test volume setting with invalid level."""
        result = plugin.invoke("set_volume", level=150)

        assert result["success"] is False
        assert "between 0 and 100" in result["error"]

    def test_set_volume_no_level(self, plugin):
        """Test volume setting without level parameter."""
        result = plugin.invoke("set_volume")

        assert result["success"] is False
        assert "required" in result["error"]

    # Brightness Control Tests
    def test_get_brightness_no_control(self, plugin):
        """Test brightness retrieval when no control is available."""
        plugin.platform = "linux"

        with patch("pathlib.Path.glob", return_value=[]), patch("pathlib.Path.exists", return_value=False):

            result = plugin.invoke("get_brightness")

            assert result["success"] is False
            assert "No brightness control found" in result["error"]

    def test_set_brightness_invalid_level(self, plugin):
        """Test brightness setting with invalid level."""
        result = plugin.invoke("set_brightness", level=150)

        assert result["success"] is False
        assert "between 0 and 100" in result["error"]

    def test_set_brightness_no_level(self, plugin):
        """Test brightness setting without level parameter."""
        result = plugin.invoke("set_brightness")

        assert result["success"] is False
        assert "required" in result["error"]

    # Security and Platform Tests
    def test_operation_allowed_check(self, plugin):
        """Test operation permission checking."""
        # Test safe operation
        assert plugin._is_operation_allowed("get_system_info") is True

        # Test operation not in any list
        assert plugin._is_operation_allowed("nonexistent_operation") is False

    def test_error_handling(self, plugin):
        """Test error handling in tool invocation."""
        # Mock an exception during tool execution
        with patch.object(plugin, "_get_system_info", side_effect=Exception("Test error")):
            result = plugin.invoke("get_system_info")

            assert result["success"] is False
            assert "Tool execution failed" in result["error"]

    def test_platform_detection(self, plugin):
        """Test platform detection."""
        assert plugin.platform in ["linux", "windows", "darwin"]
        assert isinstance(plugin.allowed_operations, dict)

    # Integration Tests
    def test_plugin_metadata(self):
        """Test plugin metadata."""
        from system_control import PLUGIN_METADATA

        assert PLUGIN_METADATA["id"] == "system_control"
        assert PLUGIN_METADATA["version"] == "1.0.0"
        assert "capabilities" in PLUGIN_METADATA
        assert "security_levels" in PLUGIN_METADATA
        assert "platforms" in PLUGIN_METADATA
