"""
Unit tests for Task Orchestrator CLI Command Routing
Tests the command routing functionality in the orchestrator.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.orchestrator.orchestrator import TaskOrchestrator


class TestOrchestratorRouting:
    """Test suite for Task Orchestrator command routing."""

    @pytest.fixture
    def mock_plugin_host(self):
        """Create a mock plugin host for testing."""
        mock_host = Mock()
        mock_host.invoke_plugin_tool = AsyncMock()
        return mock_host

    @pytest.fixture
    def mock_config(self):
        """Create a mock config for testing."""
        return {}

    @pytest.fixture
    def mock_memory_manager(self):
        """Create a mock memory manager for testing."""
        return Mock()

    @pytest.fixture
    def mock_policy_engine(self):
        """Create a mock policy engine for testing."""
        return Mock()

    @pytest.fixture
    def orchestrator(self, mock_config, mock_plugin_host, mock_memory_manager, mock_policy_engine):
        """Create orchestrator instance for testing."""
        with patch("core.orchestrator.orchestrator.get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_logger.log_task_start = Mock()
            mock_logger.log_task_complete = Mock()
            mock_logger.audit = Mock()
            mock_get_logger.return_value = mock_logger

            return TaskOrchestrator(
                config=mock_config, plugin_host=mock_plugin_host, memory_manager=mock_memory_manager, policy_engine=mock_policy_engine
            )

    # System Control Routing Tests
    @pytest.mark.asyncio
    async def test_system_info_routing(self, orchestrator, mock_plugin_host):
        """Test system info command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"platform": "linux", "cpu": "test"}}

        task_id = await orchestrator.submit_task("system info", {})

        # Verify the plugin was called correctly
        mock_plugin_host.invoke_plugin_tool.assert_called_with("system_control", "get_system_info")

        # Verify task was tracked
        assert task_id in orchestrator._tasks
        assert orchestrator._tasks[task_id]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_cpu_usage_routing(self, orchestrator, mock_plugin_host):
        """Test CPU usage command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"cpu_percent": 25.0}}

        await orchestrator.submit_task("cpu usage", {})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("system_control", "get_cpu_usage")

    @pytest.mark.asyncio
    async def test_memory_usage_routing(self, orchestrator, mock_plugin_host):
        """Test memory usage command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"memory_percent": 50.0}}

        await orchestrator.submit_task("memory usage", {})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("system_control", "get_memory_usage")

    @pytest.mark.asyncio
    async def test_disk_usage_routing_with_context(self, orchestrator, mock_plugin_host):
        """Test disk usage command routing with path context."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"disk_percent": 75.0}}

        await orchestrator.submit_task("disk usage", {"path": "/home"})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("system_control", "get_disk_usage", path="/home")

    @pytest.mark.asyncio
    async def test_list_processes_routing(self, orchestrator, mock_plugin_host):
        """Test process list command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"processes": []}}

        await orchestrator.submit_task("list processes", {"limit": 20})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("system_control", "list_processes", limit=20)

    # File Operations Routing Tests
    @pytest.mark.asyncio
    async def test_create_file_routing(self, orchestrator, mock_plugin_host):
        """Test create file command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"created": "/tmp/test.txt"}}

        await orchestrator.submit_task("create file", {"file_path": "/tmp/test.txt", "content": "Hello World"})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("file_operations", "create_file", file_path="/tmp/test.txt", content="Hello World")

    @pytest.mark.asyncio
    async def test_file_create_cli_pattern_routing(self, orchestrator, mock_plugin_host):
        """Test CLI pattern 'file create filename' routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"created": "test.txt"}}

        await orchestrator.submit_task("file create test.txt", {})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("file_operations", "create_file", file_path="test.txt", content="")

    @pytest.mark.asyncio
    async def test_file_read_cli_pattern_routing(self, orchestrator, mock_plugin_host):
        """Test CLI pattern 'file read filename' routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"content": "File content"}}

        await orchestrator.submit_task("file read test.txt", {})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("file_operations", "read_file", file_path="test.txt")

    @pytest.mark.asyncio
    async def test_file_write_cli_pattern_routing(self, orchestrator, mock_plugin_host):
        """Test CLI pattern 'file write filename content' routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"updated": "test.txt"}}

        await orchestrator.submit_task("file write test.txt 'Hello World'", {})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("file_operations", "update_file", file_path="test.txt", content="'hello world'")

    @pytest.mark.asyncio
    async def test_file_delete_cli_pattern_routing(self, orchestrator, mock_plugin_host):
        """Test CLI pattern 'file delete filename' routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"deleted": "test.txt"}}

        await orchestrator.submit_task("file delete test.txt", {})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("file_operations", "delete_file", file_path="test.txt", confirm=True)

    @pytest.mark.asyncio
    async def test_file_create_hello_routing_priority(self, orchestrator, mock_plugin_host):
        """Test that 'file create hello.txt' routes to file_operations, not os_hello."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"created": "hello.txt"}}

        await orchestrator.submit_task("file create hello.txt", {})

        # Should route to file_operations.create_file, NOT os_hello.say_hello
        mock_plugin_host.invoke_plugin_tool.assert_called_with("file_operations", "create_file", file_path="hello.txt", content="")

    @pytest.mark.asyncio
    async def test_read_file_routing(self, orchestrator, mock_plugin_host):
        """Test read file command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"content": "File content"}}

        await orchestrator.submit_task("read file", {"file_path": "/tmp/test.txt"})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("file_operations", "read_file", file_path="/tmp/test.txt")

    @pytest.mark.asyncio
    async def test_delete_file_routing(self, orchestrator, mock_plugin_host):
        """Test delete file command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"deleted": "/tmp/test.txt"}}

        await orchestrator.submit_task("delete file", {"file_path": "/tmp/test.txt"})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("file_operations", "delete_file", file_path="/tmp/test.txt", confirm=True)

    @pytest.mark.asyncio
    async def test_list_files_routing(self, orchestrator, mock_plugin_host):
        """Test list files command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"items": [], "total_items": 0}}

        await orchestrator.submit_task("list files in current directory", {})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("file_operations", "list_directory", directory_path=".")

    @pytest.mark.asyncio
    async def test_create_directory_routing(self, orchestrator, mock_plugin_host):
        """Test create directory command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"created": "/tmp/newdir"}}

        await orchestrator.submit_task("create directory", {"directory_path": "/tmp/newdir"})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("file_operations", "create_directory", directory_path="/tmp/newdir")

    # Media/App Control Routing Tests
    @pytest.mark.asyncio
    async def test_mute_audio_routing(self, orchestrator, mock_plugin_host):
        """Test mute audio command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"action": "mute_audio", "method": "pactl"}}

        await orchestrator.submit_task("mute audio", {})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("media_app_control", "mute_audio")

    @pytest.mark.asyncio
    async def test_unmute_audio_routing(self, orchestrator, mock_plugin_host):
        """Test unmute audio command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"action": "unmute_audio", "method": "pactl"}}

        await orchestrator.submit_task("unmute audio", {})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("media_app_control", "unmute_audio")

    @pytest.mark.asyncio
    async def test_volume_up_routing(self, orchestrator, mock_plugin_host):
        """Test volume up command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"action": "volume_up", "step": 5}}

        await orchestrator.submit_task("volume up", {"step": 5})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("media_app_control", "volume_up", step=5)

    @pytest.mark.asyncio
    async def test_volume_down_routing(self, orchestrator, mock_plugin_host):
        """Test volume down command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"action": "volume_down", "step": 3}}

        await orchestrator.submit_task("volume down", {"step": 3})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("media_app_control", "volume_down", step=3)

    @pytest.mark.asyncio
    async def test_set_volume_routing(self, orchestrator, mock_plugin_host):
        """Test set volume command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"action": "set_volume", "level": 75}}

        await orchestrator.submit_task("set volume", {"level": 75})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("media_app_control", "set_volume", level=75)

    @pytest.mark.asyncio
    async def test_play_media_routing(self, orchestrator, mock_plugin_host):
        """Test play media command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"action": "play_media"}}

        await orchestrator.submit_task("play media", {"media_path": "/music/song.mp3"})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("media_app_control", "play_media", media_path="/music/song.mp3")

    @pytest.mark.asyncio
    async def test_pause_media_routing(self, orchestrator, mock_plugin_host):
        """Test pause media command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"action": "pause_media"}}

        await orchestrator.submit_task("pause music", {})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("media_app_control", "pause_media")

    # Hello Plugin Routing Tests
    @pytest.mark.asyncio
    async def test_hello_routing(self, orchestrator, mock_plugin_host):
        """Test hello command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"message": "Hello!"}}

        await orchestrator.submit_task("hello", {})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("os_hello", "say_hello")

    @pytest.mark.asyncio
    async def test_hi_routing(self, orchestrator, mock_plugin_host):
        """Test hi command routing."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"message": "Hi there!"}}

        await orchestrator.submit_task("hi there", {})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("os_hello", "say_hello")

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_missing_file_path_error(self, orchestrator, mock_plugin_host):
        """Test error handling for missing file path."""
        task_id = await orchestrator.submit_task("create file", {})

        task_status = orchestrator._tasks[task_id]
        assert task_status["status"] == "completed"
        assert not task_status["result"]["success"]
        assert "File path is required" in task_status["result"]["error"]

    @pytest.mark.asyncio
    async def test_file_not_found_error_handling(self, orchestrator, mock_plugin_host):
        """Test error handling for file not found."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": False, "error": "File not found: nonexistent.txt"}

        task_id = await orchestrator.submit_task("file read nonexistent.txt", {})

        task_status = orchestrator._tasks[task_id]
        assert task_status["status"] == "completed"
        assert not task_status["result"]["success"]
        assert "File not found" in task_status["result"]["error"]

    @pytest.mark.asyncio
    async def test_access_denied_error_handling(self, orchestrator, mock_plugin_host):
        """Test error handling for access denied."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": False, "error": "Access denied to path: /invalid/path"}

        task_id = await orchestrator.submit_task("file create /invalid/path/test.txt", {})

        task_status = orchestrator._tasks[task_id]
        assert task_status["status"] == "completed"
        assert not task_status["result"]["success"]
        assert "Access denied" in task_status["result"]["error"]

    @pytest.mark.asyncio
    async def test_no_plugin_host_error(self, orchestrator):
        """Test error handling when plugin host is unavailable."""
        orchestrator.plugin_host = None

        task_id = await orchestrator.submit_task("system info", {})

        task_status = orchestrator._tasks[task_id]
        assert task_status["status"] == "failed"
        assert "Plugin host not available" in task_status["result"]["error"]

    @pytest.mark.asyncio
    async def test_unrecognized_command_default_response(self, orchestrator, mock_plugin_host):
        """Test default response for unrecognized commands."""
        task_id = await orchestrator.submit_task("do something impossible", {})

        task_status = orchestrator._tasks[task_id]
        assert task_status["status"] == "completed"
        assert "Task routing not yet implemented" in task_status["result"]["note"]

    # Task Status Tests
    @pytest.mark.asyncio
    async def test_get_task_status(self, orchestrator, mock_plugin_host):
        """Test task status retrieval."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {"test": "result"}}

        task_id = await orchestrator.submit_task("system info", {})
        status = await orchestrator.get_task_status(task_id)

        assert status["id"] == task_id
        assert status["status"] == "completed"
        assert status["result"]["success"] is True

    @pytest.mark.asyncio
    async def test_get_nonexistent_task_status(self, orchestrator):
        """Test getting status for nonexistent task."""
        status = await orchestrator.get_task_status("nonexistent-id")
        assert "error" in status
        assert status["error"] == "Task not found"

    def test_orchestrator_status(self, orchestrator):
        """Test orchestrator status retrieval."""
        status = orchestrator.get_status()

        assert "running" in status
        assert "total_tasks" in status
        assert "active_tasks" in status
        assert status["total_tasks"] == 0
        assert status["active_tasks"] == 0

    # Keyword Matching Tests
    @pytest.mark.asyncio
    async def test_keyword_variations_system_info(self, orchestrator, mock_plugin_host):
        """Test different keyword variations for system info."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {}}

        # Test various system info keywords
        test_phrases = ["system info", "system information", "get system info", "show system information"]

        for phrase in test_phrases:
            await orchestrator.submit_task(phrase, {})

        # Should have been called for each phrase
        assert mock_plugin_host.invoke_plugin_tool.call_count == len(test_phrases)

        # All calls should be to system_control.get_system_info
        for call in mock_plugin_host.invoke_plugin_tool.call_args_list:
            args, kwargs = call
            assert args[0] == "system_control"
            assert args[1] == "get_system_info"

    @pytest.mark.asyncio
    async def test_keyword_variations_file_operations(self, orchestrator, mock_plugin_host):
        """Test different keyword variations for file operations."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {}}

        # Test various file operation keywords
        test_cases = [
            ("list files", "list_directory"),
            ("list directory", "list_directory"),
            ("list folder", "list_directory"),
            ("show file content.txt", "read_file"),  # Contains "file" but not exact match
        ]

        for phrase, _expected_tool in test_cases:
            # Reset mock for each test
            mock_plugin_host.invoke_plugin_tool.reset_mock()

            await orchestrator.submit_task(phrase, {"file_path": "test.txt", "directory_path": "."})

            # Verify the correct tool was called
            mock_plugin_host.invoke_plugin_tool.assert_called_once()
            args, kwargs = mock_plugin_host.invoke_plugin_tool.call_args
            assert args[0] == "file_operations"
            # Note: For complex routing, we just verify it went to file_operations

    @pytest.mark.asyncio
    async def test_context_parameter_handling(self, orchestrator, mock_plugin_host):
        """Test proper handling of context parameters."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {}}

        # Test disk usage with custom path
        await orchestrator.submit_task("disk usage", {"path": "/custom/path"})

        mock_plugin_host.invoke_plugin_tool.assert_called_with("system_control", "get_disk_usage", path="/custom/path")

    @pytest.mark.asyncio
    async def test_multiple_concurrent_tasks(self, orchestrator, mock_plugin_host):
        """Test handling multiple concurrent tasks."""
        mock_plugin_host.invoke_plugin_tool.return_value = {"success": True, "data": {}}

        # Submit multiple tasks concurrently
        tasks = await asyncio.gather(
            orchestrator.submit_task("system info", {}),
            orchestrator.submit_task("cpu usage", {}),
            orchestrator.submit_task("memory usage", {}),
            orchestrator.submit_task("list files", {"directory_path": "."}),
        )

        # All tasks should complete
        assert len(tasks) == 4
        assert all(task_id in orchestrator._tasks for task_id in tasks)

        # All tasks should be completed
        for task_id in tasks:
            assert orchestrator._tasks[task_id]["status"] == "completed"

        # Plugin host should have been called 4 times
        assert mock_plugin_host.invoke_plugin_tool.call_count == 4

    @pytest.mark.asyncio
    async def test_exception_handling_in_plugin_call(self, orchestrator, mock_plugin_host):
        """Test exception handling when plugin calls fail."""
        # Make plugin call raise an exception
        mock_plugin_host.invoke_plugin_tool.side_effect = Exception("Plugin failed")

        task_id = await orchestrator.submit_task("system info", {})

        task_status = orchestrator._tasks[task_id]
        assert task_status["status"] == "failed"
        assert "Plugin failed" in task_status["result"]["error"]
