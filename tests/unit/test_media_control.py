"""
Unit tests for Media & Application Control Plugin
Tests media control with safe fallback behavior when pactl is unavailable.
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from plugins.available.media_app_control import MediaAppControlPlugin


class TestMediaAppControlPlugin:
    """Test suite for Media & Application Control Plugin."""

    @pytest.fixture
    def plugin(self):
        """Create plugin instance for testing."""
        return MediaAppControlPlugin()

    def test_plugin_initialization(self, plugin):
        """Test plugin initializes correctly."""
        assert plugin.id == "media_app_control"
        assert plugin.version == "1.0.0"
        assert "media_control" in plugin.capabilities
        assert "application_control" in plugin.capabilities

    def test_describe_tools(self, plugin):
        """Test tool descriptions are available."""
        tools = plugin.describe_tools()

        expected_tools = [
            "mute_audio",
            "unmute_audio",
            "set_volume",
            "get_volume_status",
            "play_media",
            "pause_media",
            "stop_media",
            "volume_up",
            "volume_down",
        ]

        for tool in expected_tools:
            assert tool in tools
            assert "description" in tools[tool]
            assert "parameters" in tools[tool]
            assert "security_level" in tools[tool]

    def test_platform_detection(self, plugin):
        """Test platform detection works correctly."""
        assert plugin.platform in ["linux", "windows", "darwin"]

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_mute_audio_with_pactl_success(self, mock_subprocess, mock_which, plugin):
        """Test successful audio muting with pactl."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        # Mock pactl available
        mock_which.return_value = "/usr/bin/pactl"
        mock_subprocess.return_value = Mock(returncode=0)

        result = plugin.invoke("mute_audio")

        assert result["success"] is True
        data = result["data"]
        assert data["action"] == "mute_audio"
        assert data["method"] == "pactl"

        # Verify pactl command was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "pactl" in call_args
        assert "set-sink-mute" in call_args

        # Restore original platform
        plugin.platform = original_platform

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_unmute_audio_with_pactl_success(self, mock_subprocess, mock_which, plugin):
        """Test successful audio unmuting with pactl."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        # Mock pactl available
        mock_which.return_value = "/usr/bin/pactl"
        mock_subprocess.return_value = Mock(returncode=0)

        result = plugin.invoke("unmute_audio")

        assert result["success"] is True
        data = result["data"]
        assert data["action"] == "unmute_audio"
        assert data["method"] == "pactl"

        # Restore original platform
        plugin.platform = original_platform

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_mute_audio_with_amixer_fallback(self, mock_subprocess, mock_which, plugin):
        """Test audio muting falls back to amixer when pactl unavailable."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        # Mock pactl unavailable, amixer available
        def which_side_effect(cmd):
            if cmd == "pactl":
                return None
            elif cmd == "amixer":
                return "/usr/bin/amixer"
            return None

        mock_which.side_effect = which_side_effect
        mock_subprocess.return_value = Mock(returncode=0)

        result = plugin.invoke("mute_audio")

        assert result["success"] is True
        data = result["data"]
        assert data["action"] == "mute_audio"
        assert data["method"] == "amixer"

        # Restore original platform
        plugin.platform = original_platform

    @patch("shutil.which")
    @patch("os.environ.get")
    def test_mute_audio_headless_environment(self, mock_env_get, mock_which, plugin):
        """Test audio muting in headless environment provides clean warning."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        # Mock no audio tools available and headless environment
        mock_which.return_value = None
        mock_env_get.side_effect = lambda key, default=None: "1" if key == "HEADLESS" else default

        result = plugin.invoke("mute_audio")

        assert result["success"] is False
        assert "headless environment" in result["error"]
        assert "warning" in result
        assert "This is normal for headless" in result["warning"]

        # Restore original platform
        plugin.platform = original_platform

    @patch("shutil.which")
    @patch("os.environ.get")
    @patch("builtins.print")
    def test_mute_audio_no_tools_available(self, mock_print, mock_env_get, mock_which, plugin):
        """Test audio muting when no tools available provides helpful message."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        # Mock no audio tools and no headless environment
        mock_which.return_value = None
        mock_env_get.return_value = None

        result = plugin.invoke("mute_audio")

        assert result["success"] is False
        assert "Audio control unavailable" in result["error"]
        assert "note" in result
        assert "pulseaudio-utils" in result["note"] or "alsa-utils" in result["note"]

        # Verify informational message was printed
        mock_print.assert_called_once()
        print_args = mock_print.call_args[0][0]
        assert "INFO:" in print_args
        assert "Audio control unavailable" in print_args

        # Restore original platform
        plugin.platform = original_platform

    def test_mute_audio_windows_not_implemented(self, plugin):
        """Test audio muting on Windows shows future implementation note."""
        # Force Windows platform
        original_platform = plugin.platform
        plugin.platform = "windows"

        result = plugin.invoke("mute_audio")

        assert result["success"] is False
        assert "Windows audio control not yet implemented" in result["error"]
        assert "note" in result
        assert "pycaw" in result["note"]

        # Restore original platform
        plugin.platform = original_platform

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_volume_up_with_pactl(self, mock_subprocess, mock_which, plugin):
        """Test volume up with pactl."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        mock_which.return_value = "/usr/bin/pactl"
        mock_subprocess.return_value = Mock(returncode=0)

        result = plugin.invoke("volume_up", step=10)

        assert result["success"] is True
        data = result["data"]
        assert data["action"] == "volume_up"
        assert data["step"] == 10
        assert data["method"] == "pactl"

        # Restore original platform
        plugin.platform = original_platform

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_volume_down_with_pactl(self, mock_subprocess, mock_which, plugin):
        """Test volume down with pactl."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        mock_which.return_value = "/usr/bin/pactl"
        mock_subprocess.return_value = Mock(returncode=0)

        result = plugin.invoke("volume_down", step=5)

        assert result["success"] is True
        data = result["data"]
        assert data["action"] == "volume_down"
        assert data["step"] == 5
        assert data["method"] == "pactl"

        # Restore original platform
        plugin.platform = original_platform

    def test_volume_step_validation(self, plugin):
        """Test volume step validation."""
        # Test invalid step values
        result = plugin.invoke("volume_up", step=15)  # Too high
        assert result["success"] is False
        assert "between 1 and 10" in result["error"]

        result = plugin.invoke("volume_down", step=0)  # Too low
        assert result["success"] is False
        assert "between 1 and 10" in result["error"]

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_set_volume_with_pactl(self, mock_subprocess, mock_which, plugin):
        """Test volume setting with pactl."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        mock_which.return_value = "/usr/bin/pactl"
        mock_subprocess.return_value = Mock(returncode=0)

        result = plugin.invoke("set_volume", level=75)

        assert result["success"] is True
        data = result["data"]
        assert data["action"] == "set_volume"
        assert data["level"] == 75
        assert data["method"] == "pactl"

        # Restore original platform
        plugin.platform = original_platform

    def test_set_volume_validation(self, plugin):
        """Test volume level validation."""
        # Test invalid volume levels
        result = plugin.invoke("set_volume", level=150)  # Too high
        assert result["success"] is False
        assert "between 0 and 100" in result["error"]

        result = plugin.invoke("set_volume", level=-10)  # Too low
        assert result["success"] is False
        assert "between 0 and 100" in result["error"]

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_get_volume_status_with_amixer(self, mock_subprocess, mock_which, plugin):
        """Test volume status retrieval with amixer."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        mock_which.return_value = "/usr/bin/amixer"
        mock_subprocess.return_value = Mock(
            returncode=0, stdout="Simple mixer control 'Master',0\n  Playback channels: Mono\n  Mono: Playback 45000 [69%] [on]"
        )

        result = plugin.invoke("get_volume_status")

        assert result["success"] is True
        data = result["data"]
        assert data["volume_percent"] == 69
        assert data["muted"] is False
        assert data["method"] == "amixer"

        # Restore original platform
        plugin.platform = original_platform

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_play_media_with_playerctl(self, mock_subprocess, mock_which, plugin):
        """Test media playback with playerctl."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        mock_which.return_value = "/usr/bin/playerctl"
        mock_subprocess.return_value = Mock(returncode=0)

        result = plugin.invoke("play_media")

        assert result["success"] is True
        data = result["data"]
        assert data["action"] == "resume_playback"
        assert data["method"] == "playerctl"

        # Restore original platform
        plugin.platform = original_platform

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_pause_media_with_playerctl(self, mock_subprocess, mock_which, plugin):
        """Test media pause with playerctl."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        mock_which.return_value = "/usr/bin/playerctl"
        mock_subprocess.return_value = Mock(returncode=0)

        result = plugin.invoke("pause_media")

        assert result["success"] is True
        data = result["data"]
        assert data["action"] == "pause_media"
        assert data["method"] == "playerctl"

        # Restore original platform
        plugin.platform = original_platform

    @patch("shutil.which")
    def test_media_control_no_player_available(self, mock_which, plugin):
        """Test media control when no player is available."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        # Mock no media players available
        mock_which.return_value = None

        result = plugin.invoke("play_media")

        assert result["success"] is False
        assert "not supported" in result["error"]

        # Restore original platform
        plugin.platform = original_platform

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_get_media_status_with_playerctl(self, mock_subprocess, mock_which, plugin):
        """Test media status retrieval with playerctl."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        mock_which.return_value = "/usr/bin/playerctl"

        # Mock successful status and metadata calls
        def subprocess_side_effect(*args, **kwargs):
            cmd = args[0]
            if "status" in cmd:
                return Mock(returncode=0, stdout="Playing")
            elif "title" in cmd:
                return Mock(returncode=0, stdout="Test Song")
            elif "artist" in cmd:
                return Mock(returncode=0, stdout="Test Artist")
            return Mock(returncode=1)

        mock_subprocess.side_effect = subprocess_side_effect

        result = plugin.invoke("get_media_status")

        assert result["success"] is True
        data = result["data"]
        assert data["status"] == "Playing"
        assert data["metadata"]["title"] == "Test Song"
        assert data["metadata"]["artist"] == "Test Artist"

        # Restore original platform
        plugin.platform = original_platform

    def test_get_available_audio_methods(self, plugin):
        """Test audio methods detection."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd in ["pactl", "amixer"] else None

            methods = plugin._get_available_audio_methods()

            assert "pactl" in methods
            assert "amixer" in methods

        # Restore original platform
        plugin.platform = original_platform

    def test_get_available_media_methods(self, plugin):
        """Test media methods detection."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd in ["playerctl", "vlc"] else None

            methods = plugin._get_available_media_methods()

            assert "playerctl" in methods
            assert "vlc" in methods

        # Restore original platform
        plugin.platform = original_platform

    def test_operation_allowed_check(self, plugin):
        """Test operation permission checking."""
        # Test safe operation
        assert plugin._is_operation_allowed("get_volume_status") is True

        # Test privileged operation
        assert plugin._is_operation_allowed("mute_audio") is True

        # Test operation not in any list
        assert plugin._is_operation_allowed("nonexistent_operation") is False

    def test_invalid_tool(self, plugin):
        """Test calling invalid tool returns error."""
        result = plugin.invoke("invalid_tool")

        assert result["success"] is False
        assert "Unknown tool" in result["error"]
        assert "available_tools" in result

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_audio_command_timeout(self, mock_subprocess, mock_which, plugin):
        """Test audio command timeout handling."""
        # Force Linux platform
        original_platform = plugin.platform
        plugin.platform = "linux"

        mock_which.return_value = "/usr/bin/pactl"

        # Mock subprocess timeout
        from subprocess import TimeoutExpired

        mock_subprocess.side_effect = TimeoutExpired("pactl", 5)

        result = plugin.invoke("mute_audio")

        assert result["success"] is False
        assert "Failed to mute audio" in result["error"]

        # Restore original platform
        plugin.platform = original_platform

    @pytest.mark.skipif(not os.environ.get("AUDIO_BACKEND_AVAILABLE"), reason="Audio backend not available in CI")
    def test_audio_integration_with_real_backend(self, plugin):
        """Test audio integration when real backend is available."""
        # This test is skipped unless AUDIO_BACKEND_AVAILABLE is set
        # It's designed to be safe for CI environments

        result = plugin.invoke("get_volume_status")

        # Should either succeed or fail gracefully
        assert "success" in result
        if not result["success"]:
            # If it fails, it should be due to no audio system, not a crash
            assert "unavailable" in result["error"] or "not supported" in result["error"]

    def test_error_handling(self, plugin):
        """Test general error handling."""
        # Test with missing required parameters for operations that need them
        result = plugin.invoke("set_volume")  # Missing level parameter

        assert result["success"] is False
        assert "error" in result

    def test_track_operation(self, plugin):
        """Test operation tracking for memory integration."""
        # Create mock memory manager
        mock_memory = Mock()
        plugin.memory_manager = mock_memory

        # Perform an operation
        result = plugin.invoke("get_volume_status")

        # Verify operation was tracked
        assert len(plugin.operation_history) > 0
        latest_op = plugin.operation_history[-1]
        assert latest_op["tool"] == "get_volume_status"
        assert "timestamp" in latest_op

        # If memory manager is available, verify it was called
        if result.get("success"):
            mock_memory.store_memory.assert_called()

    def test_cross_platform_compatibility(self, plugin):
        """Test plugin handles different platforms gracefully."""
        platforms = ["linux", "windows", "darwin", "unknown"]
        original_platform = plugin.platform

        for test_platform in platforms:
            plugin.platform = test_platform

            # Test safe operation (should work or fail gracefully on all platforms)
            result = plugin.invoke("get_volume_status")
            assert "success" in result

            # Test that allowed operations are properly defined
            allowed_ops = plugin._get_allowed_operations()
            assert "safe" in allowed_ops
            assert "privileged" in allowed_ops

        # Restore original platform
        plugin.platform = original_platform
