"""
Unit tests for Media & Application Control Plugin
"""

# Import the plugin
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "available"))

from media_app_control import MediaAppControlPlugin, create_plugin


class TestMediaAppControlPlugin:
    """Test cases for the Media & Application Control Plugin."""

    @pytest.fixture
    def plugin(self):
        """Create a media app control plugin instance."""
        return MediaAppControlPlugin()

    def test_plugin_creation(self, plugin):
        """Test plugin can be created."""
        assert plugin.id == "media_app_control"
        assert plugin.version == "1.0.0"
        assert isinstance(plugin.capabilities, list)
        assert len(plugin.capabilities) > 0

    def test_factory_function(self):
        """Test the factory function works."""
        plugin = create_plugin()
        assert isinstance(plugin, MediaAppControlPlugin)
        assert plugin.id == "media_app_control"

    def test_describe_tools(self, plugin):
        """Test plugin tool description."""
        tools = plugin.describe_tools()

        # Check that all expected tools are present
        expected_tools = [
            # Media controls
            "play_media",
            "pause_media",
            "stop_media",
            "next_track",
            "previous_track",
            "volume_up",
            "volume_down",
            "mute_audio",
            "unmute_audio",
            "set_volume",
            "get_volume_status",
            "get_media_status",
            # Application controls
            "launch_application",
            "close_application",
            "get_running_applications",
            "list_installed_applications",
            # Window management
            "focus_window",
            "minimize_window",
            "maximize_window",
            "close_window",
            "get_window_list",
            "get_active_window",
        ]

        for tool in expected_tools:
            assert tool in tools
            assert "description" in tools[tool]
            assert "parameters" in tools[tool]
            assert "security_level" in tools[tool]

    def test_allowed_operations(self, plugin):
        """Test allowed operations by security level."""
        safe_ops = plugin.allowed_operations.get("safe", [])
        privileged_ops = plugin.allowed_operations.get("privileged", [])

        assert len(safe_ops) > 0
        assert "get_media_status" in safe_ops
        assert "get_running_applications" in safe_ops

        assert len(privileged_ops) > 0
        assert "play_media" in privileged_ops
        assert "launch_application" in privileged_ops

    def test_unknown_tool(self, plugin):
        """Test handling of unknown tools."""
        result = plugin.invoke("nonexistent_tool")

        assert result["success"] is False
        assert "Unknown tool" in result["error"]
        assert "available_tools" in result

    def test_operation_allowed_check(self, plugin):
        """Test operation permission checking."""
        # Test safe operation
        assert plugin._is_operation_allowed("get_media_status") is True

        # Test privileged operation
        assert plugin._is_operation_allowed("play_media") is True

        # Test operation not in any list
        assert plugin._is_operation_allowed("nonexistent_operation") is False

    def test_track_operation(self, plugin):
        """Test operation tracking for memory integration."""
        # Mock memory manager
        mock_memory = Mock()
        plugin.memory_manager = mock_memory

        plugin._track_operation("play_media", {"media_path": "/test/path"})

        assert len(plugin.operation_history) == 1
        assert plugin.operation_history[0]["tool"] == "play_media"
        mock_memory.store_memory.assert_called_once()

    def test_platform_detection(self, plugin):
        """Test platform detection."""
        assert plugin.platform in ["linux", "windows", "darwin"]

    # Media Control Tests

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_play_media_linux_with_file(self, mock_which, mock_run, plugin):
        """Test playing media file on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/xdg-open"
        mock_run.return_value = Mock(returncode=0)

        result = plugin.invoke("play_media", media_path="/test/song.mp3")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["media_path"] == "/test/song.mp3"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_pause_media_linux(self, mock_which, mock_run, plugin):
        """Test pausing media on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/playerctl"
        mock_run.return_value = Mock(returncode=0)

        result = plugin.invoke("pause_media")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["action"] == "pause_media"

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_stop_media_linux(self, mock_which, mock_run, plugin):
        """Test stopping media on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/playerctl"
        mock_run.return_value = Mock(returncode=0)

        result = plugin.invoke("stop_media")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["action"] == "stop_media"

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_next_track_linux(self, mock_which, mock_run, plugin):
        """Test next track on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/playerctl"
        mock_run.return_value = Mock(returncode=0)

        result = plugin.invoke("next_track")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["action"] == "next_track"

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_previous_track_linux(self, mock_which, mock_run, plugin):
        """Test previous track on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/playerctl"
        mock_run.return_value = Mock(returncode=0)

        result = plugin.invoke("previous_track")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["action"] == "previous_track"

    # Volume Control Tests

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_volume_up_linux(self, mock_which, mock_run, plugin):
        """Test volume up on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/amixer"
        mock_run.return_value = Mock(returncode=0)

        result = plugin.invoke("volume_up", step=3)

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["step"] == 3

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_volume_down_linux(self, mock_which, mock_run, plugin):
        """Test volume down on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/amixer"
        mock_run.return_value = Mock(returncode=0)

        result = plugin.invoke("volume_down", step=2)

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["step"] == 2

    def test_volume_invalid_step(self, plugin):
        """Test volume control with invalid step."""
        result = plugin.invoke("volume_up", step=15)

        assert result["success"] is False
        assert "between 1 and 10" in result["error"]

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_mute_audio_linux(self, mock_which, mock_run, plugin):
        """Test muting audio on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/amixer"
        mock_run.return_value = Mock(returncode=0)

        result = plugin.invoke("mute_audio")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["action"] == "mute_audio"

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_unmute_audio_linux(self, mock_which, mock_run, plugin):
        """Test unmuting audio on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/amixer"
        mock_run.return_value = Mock(returncode=0)

        result = plugin.invoke("unmute_audio")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["action"] == "unmute_audio"

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_set_volume_linux(self, mock_which, mock_run, plugin):
        """Test setting volume on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/amixer"
        mock_run.return_value = Mock(returncode=0)

        result = plugin.invoke("set_volume", level=75)

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["level"] == 75

    def test_set_volume_invalid_level(self, plugin):
        """Test setting volume with invalid level."""
        result = plugin.invoke("set_volume", level=150)

        assert result["success"] is False
        assert "between 0 and 100" in result["error"]

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_get_volume_status_linux(self, mock_which, mock_run, plugin):
        """Test getting volume status on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/amixer"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Simple mixer control 'Master',0\n  Capabilities: pvolume\n  Playback channels: Front Left - Front Right\n  Limits: Playback 0 - 65536\n  Mono:\n  Front Left: Playback 49152 [75%] [on]\n  Front Right: Playback 49152 [75%] [on]",
        )

        result = plugin.invoke("get_volume_status")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["volume_percent"] == 75
        assert result["data"]["muted"] is False

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_get_media_status_linux(self, mock_which, mock_run, plugin):
        """Test getting media status on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/playerctl"

        # Mock successful playerctl status call
        status_mock = Mock(returncode=0, stdout="Playing")
        title_mock = Mock(returncode=0, stdout="Test Song")
        artist_mock = Mock(returncode=0, stdout="Test Artist")

        mock_run.side_effect = [status_mock, title_mock, artist_mock]

        result = plugin.invoke("get_media_status")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["status"] == "Playing"
        assert result["data"]["metadata"]["title"] == "Test Song"
        assert result["data"]["metadata"]["artist"] == "Test Artist"

    # Application Control Tests

    @patch("subprocess.Popen")
    def test_launch_application_linux(self, mock_popen, plugin):
        """Test launching application on Linux."""
        plugin.platform = "linux"
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        result = plugin.invoke("launch_application", application="firefox")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["application"] == "firefox"
        assert result["data"]["pid"] == 12345

    def test_launch_application_no_name(self, plugin):
        """Test launching application without name."""
        result = plugin.invoke("launch_application")

        assert result["success"] is False
        assert "required" in result["error"]

    @patch("psutil.process_iter")
    @patch("psutil.pid_exists")
    def test_close_application_by_name(self, mock_pid_exists, mock_process_iter, plugin):
        """Test closing application by name."""
        # Mock process
        mock_process = Mock()
        mock_process.info = {"pid": 12345, "name": "firefox", "cmdline": ["firefox"]}
        mock_process.pid = 12345
        mock_process.name.return_value = "firefox"
        mock_process.status.return_value = "running"
        mock_process.wait = Mock()

        mock_process_iter.return_value = [mock_process]

        result = plugin.invoke("close_application", application="firefox")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["total_closed"] == 1
        mock_process.terminate.assert_called_once()

    @patch("psutil.process_iter")
    def test_get_running_applications(self, mock_process_iter, plugin):
        """Test getting running applications."""
        # Mock processes
        mock_proc1 = Mock()
        mock_proc1.info = {
            "pid": 123,
            "name": "firefox",
            "cmdline": ["firefox"],
            "memory_info": Mock(rss=1024 * 1024 * 100),  # 100MB
            "cpu_percent": 5.5,
        }

        mock_proc2 = Mock()
        mock_proc2.info = {
            "pid": 456,
            "name": "chrome",
            "cmdline": ["chrome"],
            "memory_info": Mock(rss=1024 * 1024 * 200),  # 200MB
            "cpu_percent": 3.2,
        }

        mock_process_iter.return_value = [mock_proc1, mock_proc2]

        result = plugin.invoke("get_running_applications", detailed=True)

        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]["applications"]) == 2
        assert result["data"]["applications"][0]["name"] == "chrome"  # Sorted by name
        assert result["data"]["applications"][1]["name"] == "firefox"

    def test_list_installed_applications_linux(self, plugin):
        """Test listing installed applications on Linux."""
        plugin.platform = "linux"

        # Mock file content
        desktop_content = """[Desktop Entry]
Name=Firefox
Exec=firefox %u
Categories=Network;WebBrowser;
"""

        # Mock Path object and its methods
        with patch("pathlib.Path") as mock_path_class:
            mock_path = Mock()
            mock_path_class.return_value = mock_path
            mock_path.expanduser.return_value = mock_path
            mock_path.exists.return_value = True

            # Mock desktop files
            mock_file1 = Mock()
            mock_file1.__str__ = lambda: "/usr/share/applications/firefox.desktop"
            mock_file2 = Mock()
            mock_file2.__str__ = lambda: "/usr/share/applications/chrome.desktop"

            mock_path.glob.return_value = [mock_file1, mock_file2]

            with patch("builtins.open", mock_open(read_data=desktop_content)):
                result = plugin.invoke("list_installed_applications")

        assert result["success"] is True
        assert "data" in result
        # Should find at least one application (may be less due to parsing)

    # Window Management Tests

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_focus_window_linux(self, mock_which, mock_run, plugin):
        """Test focusing window on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/wmctrl"
        mock_run.return_value = Mock(returncode=0)

        result = plugin.invoke("focus_window", window_title="Firefox")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["window_title"] == "Firefox"

    def test_focus_window_no_title(self, plugin):
        """Test focusing window without title."""
        result = plugin.invoke("focus_window")

        assert result["success"] is False
        assert "required" in result["error"]

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_minimize_window_linux(self, mock_which, mock_run, plugin):
        """Test minimizing window on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/xdotool"

        # Mock xdotool search and minimize
        search_mock = Mock(returncode=0, stdout="0x123456")
        minimize_mock = Mock(returncode=0)
        mock_run.side_effect = [search_mock, minimize_mock]

        result = plugin.invoke("minimize_window", window_title="Firefox")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["window_title"] == "Firefox"

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_maximize_window_linux(self, mock_which, mock_run, plugin):
        """Test maximizing window on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/wmctrl"
        mock_run.return_value = Mock(returncode=0)

        result = plugin.invoke("maximize_window", window_title="Firefox")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["window_title"] == "Firefox"

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_close_window_linux(self, mock_which, mock_run, plugin):
        """Test closing window on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/wmctrl"
        mock_run.return_value = Mock(returncode=0)

        result = plugin.invoke("close_window", window_title="Firefox")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["window_title"] == "Firefox"

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_get_window_list_linux(self, mock_which, mock_run, plugin):
        """Test getting window list on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/wmctrl"
        mock_run.return_value = Mock(returncode=0, stdout="0x01800003  0 hostname Firefox\n0x01800004  0 hostname Terminal")

        result = plugin.invoke("get_window_list")

        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]["windows"]) == 2
        assert result["data"]["windows"][0]["title"] == "Firefox"

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_get_active_window_linux(self, mock_which, mock_run, plugin):
        """Test getting active window on Linux."""
        plugin.platform = "linux"
        mock_which.return_value = "/usr/bin/xdotool"

        window_id_mock = Mock(returncode=0, stdout="0x123456")
        window_title_mock = Mock(returncode=0, stdout="Firefox")
        mock_run.side_effect = [window_id_mock, window_title_mock]

        result = plugin.invoke("get_active_window")

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["active_window"]["title"] == "Firefox"

    # Error Handling Tests

    def test_error_handling(self, plugin):
        """Test error handling in tool invocation."""
        # Mock an exception during tool execution
        with patch.object(plugin, "_play_media", side_effect=Exception("Test error")):
            result = plugin.invoke("play_media")

            assert result["success"] is False
            assert "Tool execution failed" in result["error"]

    def test_unsupported_platform_media(self, plugin):
        """Test media operations on unsupported platform."""
        plugin.platform = "unsupported"

        result = plugin.invoke("play_media")

        assert result["success"] is False
        assert "not supported" in result["error"]

    def test_unsupported_platform_volume(self, plugin):
        """Test volume operations on unsupported platform."""
        plugin.platform = "unsupported"

        result = plugin.invoke("volume_up")

        assert result["success"] is False
        assert "not supported" in result["error"]

    def test_unsupported_platform_window(self, plugin):
        """Test window operations on unsupported platform."""
        plugin.platform = "unsupported"

        result = plugin.invoke("focus_window", window_title="Test")

        assert result["success"] is False
        assert "not supported" in result["error"]

    # Helper Method Tests

    def test_get_available_media_methods(self, plugin):
        """Test getting available media methods."""
        plugin.platform = "linux"

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd in ["playerctl", "vlc"] else None
            methods = plugin._get_available_media_methods()

            assert "playerctl" in methods
            assert "vlc" in methods
            assert "mpv" not in methods

    def test_get_available_audio_methods(self, plugin):
        """Test getting available audio methods."""
        plugin.platform = "linux"

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd in ["amixer"] else None
            methods = plugin._get_available_audio_methods()

            assert "amixer" in methods
            assert "pactl" not in methods

    def test_get_available_window_methods(self, plugin):
        """Test getting available window methods."""
        plugin.platform = "linux"

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd in ["wmctrl"] else None
            methods = plugin._get_available_window_methods()

            assert "wmctrl" in methods
            assert "xdotool" not in methods

    # Integration Tests

    def test_plugin_metadata(self):
        """Test plugin metadata."""
        from media_app_control import PLUGIN_METADATA

        assert PLUGIN_METADATA["id"] == "media_app_control"
        assert PLUGIN_METADATA["version"] == "1.0.0"
        assert "capabilities" in PLUGIN_METADATA
        assert "security_levels" in PLUGIN_METADATA
        assert "platforms" in PLUGIN_METADATA

    def test_memory_integration_without_manager(self, plugin):
        """Test operation tracking without memory manager."""
        # No memory manager set
        plugin.memory_manager = None

        plugin._track_operation("test_tool", {})

        assert len(plugin.operation_history) == 1
        # Should not crash without memory manager

    def test_parameter_validation(self, plugin):
        """Test parameter validation for different tools."""
        # Test missing required parameters

        result = plugin.invoke("launch_application")
        assert result["success"] is False
        assert "required" in result["error"]

        result = plugin.invoke("focus_window")
        assert result["success"] is False
        assert "required" in result["error"]

        result = plugin.invoke("set_volume")
        assert result["success"] is False
        assert "required" in result["error"]


# Mock helper for file operations
def mock_open(read_data=""):
    """Create a mock for file open operations."""
    from unittest.mock import mock_open as original_mock_open

    return original_mock_open(read_data=read_data)
