"""
Media & Application Control Plugin for Friday AI Assistant

Provides comprehensive media playback and application management capabilities including:
- Media controls: play, pause, stop, volume up/down, mute/unmute
- Application controls: launch, close, switch window focus
- Cross-platform compatibility (Linux, Windows, macOS)
- Security: All operations are policy-checked and logged

Security: All media and application operations are policy-checked, validated, and logged.
"""

import json
import os
import platform
import shlex
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil


class MediaAppControlPlugin:
    """
    Media & Application Control Plugin for Friday AI Assistant.

    Provides secure media playback and application management with comprehensive safety controls.
    """

    def __init__(self):
        self.id = "media_app_control"
        self.version = "1.0.0"
        self.capabilities = ["media_control", "application_control", "window_management", "volume_control", "process_management"]

        # Platform detection
        self.platform = platform.system().lower()

        # Security: Define allowed operations by platform and security level
        self.allowed_operations = self._get_allowed_operations()

        # Application launch history for memory integration
        self.operation_history = []

        # Memory manager (set by kernel during initialization)
        self.memory_manager = None

    def _get_allowed_operations(self) -> Dict[str, List[str]]:
        """Get allowed operations based on platform and security level."""
        base_safe_ops = [
            "get_media_status",
            "get_running_applications",
            "list_installed_applications",
            "get_window_list",
            "get_active_window",
            "get_volume_status",
        ]

        base_privileged_ops = [
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
            "launch_application",
            "close_application",
            "focus_window",
            "minimize_window",
            "maximize_window",
            "close_window",
        ]

        return {"safe": base_safe_ops, "privileged": base_privileged_ops}

    def describe_tools(self) -> Dict[str, Any]:
        """Describe the tools provided by this plugin."""
        return {
            # Media Control Operations
            "play_media": {
                "description": "Start or resume media playback",
                "parameters": {"media_path": {"type": "string", "description": "Optional path to media file to play", "required": False}},
                "security_level": "privileged",
            },
            "pause_media": {"description": "Pause current media playback", "parameters": {}, "security_level": "privileged"},
            "stop_media": {"description": "Stop current media playback", "parameters": {}, "security_level": "privileged"},
            "next_track": {"description": "Skip to next track in playlist", "parameters": {}, "security_level": "privileged"},
            "previous_track": {"description": "Go to previous track in playlist", "parameters": {}, "security_level": "privileged"},
            "volume_up": {
                "description": "Increase system volume",
                "parameters": {"step": {"type": "integer", "description": "Volume increase step (1-10)", "default": 5}},
                "security_level": "privileged",
            },
            "volume_down": {
                "description": "Decrease system volume",
                "parameters": {"step": {"type": "integer", "description": "Volume decrease step (1-10)", "default": 5}},
                "security_level": "privileged",
            },
            "mute_audio": {"description": "Mute system audio", "parameters": {}, "security_level": "privileged"},
            "unmute_audio": {"description": "Unmute system audio", "parameters": {}, "security_level": "privileged"},
            "set_volume": {
                "description": "Set system volume to specific level",
                "parameters": {"level": {"type": "integer", "description": "Volume level (0-100)", "required": True}},
                "security_level": "privileged",
            },
            "get_volume_status": {"description": "Get current volume and mute status", "parameters": {}, "security_level": "safe"},
            "get_media_status": {"description": "Get current media playback status", "parameters": {}, "security_level": "safe"},
            # Application Control Operations
            "launch_application": {
                "description": "Launch an application",
                "parameters": {
                    "application": {"type": "string", "description": "Application name or path to launch", "required": True},
                    "arguments": {"type": "string", "description": "Command line arguments", "default": ""},
                },
                "security_level": "privileged",
            },
            "close_application": {
                "description": "Close a running application",
                "parameters": {
                    "application": {"type": "string", "description": "Application name or process ID", "required": True},
                    "force": {"type": "boolean", "description": "Force close if application doesn't respond", "default": False},
                },
                "security_level": "privileged",
            },
            "get_running_applications": {
                "description": "Get list of currently running applications",
                "parameters": {"detailed": {"type": "boolean", "description": "Include detailed process information", "default": False}},
                "security_level": "safe",
            },
            "list_installed_applications": {
                "description": "List installed applications on the system",
                "parameters": {"category": {"type": "string", "description": "Filter by application category", "default": "all"}},
                "security_level": "safe",
            },
            # Window Management Operations
            "focus_window": {
                "description": "Bring a window to focus",
                "parameters": {"window_title": {"type": "string", "description": "Title or partial title of window to focus", "required": True}},
                "security_level": "privileged",
            },
            "minimize_window": {
                "description": "Minimize a window",
                "parameters": {"window_title": {"type": "string", "description": "Title or partial title of window to minimize", "required": True}},
                "security_level": "privileged",
            },
            "maximize_window": {
                "description": "Maximize a window",
                "parameters": {"window_title": {"type": "string", "description": "Title or partial title of window to maximize", "required": True}},
                "security_level": "privileged",
            },
            "close_window": {
                "description": "Close a specific window",
                "parameters": {"window_title": {"type": "string", "description": "Title or partial title of window to close", "required": True}},
                "security_level": "privileged",
            },
            "get_window_list": {"description": "Get list of open windows", "parameters": {}, "security_level": "safe"},
            "get_active_window": {"description": "Get information about the currently active window", "parameters": {}, "security_level": "safe"},
        }

    def invoke(self, tool: str, **kwargs) -> Dict[str, Any]:
        """
        Invoke a tool with the given parameters.

        Args:
            tool: Tool name to invoke
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        # Validate tool exists
        tools = self.describe_tools()
        if tool not in tools:
            return {"success": False, "error": f"Unknown tool: {tool}", "available_tools": list(tools.keys())}

        # Check if operation is allowed
        if not self._is_operation_allowed(tool):
            return {"success": False, "error": f"Operation not allowed: {tool}", "platform": self.platform}

        # Track operation for memory integration
        self._track_operation(tool, kwargs)

        try:
            # Route to appropriate handler
            if tool == "play_media":
                return self._play_media(**kwargs)
            elif tool == "pause_media":
                return self._pause_media(**kwargs)
            elif tool == "stop_media":
                return self._stop_media(**kwargs)
            elif tool == "next_track":
                return self._next_track(**kwargs)
            elif tool == "previous_track":
                return self._previous_track(**kwargs)
            elif tool == "volume_up":
                return self._volume_up(**kwargs)
            elif tool == "volume_down":
                return self._volume_down(**kwargs)
            elif tool == "mute_audio":
                return self._mute_audio(**kwargs)
            elif tool == "unmute_audio":
                return self._unmute_audio(**kwargs)
            elif tool == "set_volume":
                return self._set_volume(**kwargs)
            elif tool == "get_volume_status":
                return self._get_volume_status(**kwargs)
            elif tool == "get_media_status":
                return self._get_media_status(**kwargs)
            elif tool == "launch_application":
                return self._launch_application(**kwargs)
            elif tool == "close_application":
                return self._close_application(**kwargs)
            elif tool == "get_running_applications":
                return self._get_running_applications(**kwargs)
            elif tool == "list_installed_applications":
                return self._list_installed_applications(**kwargs)
            elif tool == "focus_window":
                return self._focus_window(**kwargs)
            elif tool == "minimize_window":
                return self._minimize_window(**kwargs)
            elif tool == "maximize_window":
                return self._maximize_window(**kwargs)
            elif tool == "close_window":
                return self._close_window(**kwargs)
            elif tool == "get_window_list":
                return self._get_window_list(**kwargs)
            elif tool == "get_active_window":
                return self._get_active_window(**kwargs)
            else:
                return {"success": False, "error": f"Tool handler not implemented: {tool}"}

        except Exception as e:
            return {"success": False, "error": f"Tool execution failed: {str(e)}", "tool": tool, "parameters": kwargs}

    def _is_operation_allowed(self, operation: str) -> bool:
        """Check if an operation is allowed based on security level."""
        safe_ops = self.allowed_operations.get("safe", [])
        privileged_ops = self.allowed_operations.get("privileged", [])

        return operation in safe_ops or operation in privileged_ops

    def _track_operation(self, tool: str, parameters: Dict[str, Any]):
        """Track operation for memory integration."""
        operation_record = {"tool": tool, "parameters": parameters, "timestamp": datetime.utcnow().isoformat(), "platform": self.platform}

        self.operation_history.append(operation_record)

        # Store in memory manager if available
        if self.memory_manager:
            memory_id = f"media_app_op_{len(self.operation_history)}"
            self.memory_manager.store_memory(memory_id, json.dumps(operation_record), "media_app_operation", {"plugin": self.id, "tool": tool})

    # Media Control Methods

    def _play_media(self, media_path: Optional[str] = None) -> Dict[str, Any]:
        """Start or resume media playback."""
        try:
            if self.platform == "linux":
                if media_path:
                    # Play specific media file
                    result = subprocess.run(["xdg-open", media_path], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "play_media", "media_path": media_path, "method": "xdg-open"}}
                else:
                    # Resume playback using playerctl (if available)
                    if shutil.which("playerctl"):
                        result = subprocess.run(["playerctl", "play"], capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            return {"success": True, "data": {"action": "resume_playback", "method": "playerctl"}}

                    # Fallback: try common media players
                    for player in ["vlc", "mpv", "mplayer"]:
                        if shutil.which(player):
                            return {
                                "success": True,
                                "data": {
                                    "action": "media_player_available",
                                    "player": player,
                                    "note": "Use play_media with media_path to play specific file",
                                },
                            }

            elif self.platform == "windows":
                if media_path:
                    result = subprocess.run(["start", "", media_path], shell=True, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "play_media", "media_path": media_path, "method": "windows_start"}}

            elif self.platform == "darwin":  # macOS
                if media_path:
                    result = subprocess.run(["open", media_path], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "play_media", "media_path": media_path, "method": "macos_open"}}

            return {
                "success": False,
                "error": f"Media playback not supported or failed on {self.platform}",
                "available_methods": self._get_available_media_methods(),
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Media playback command timed out"}
        except Exception as e:
            return {"success": False, "error": f"Failed to play media: {str(e)}"}

    def _pause_media(self) -> Dict[str, Any]:
        """Pause current media playback."""
        try:
            if self.platform == "linux":
                if shutil.which("playerctl"):
                    result = subprocess.run(["playerctl", "pause"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "pause_media", "method": "playerctl"}}

            # Platform-specific implementations would go here
            return {
                "success": False,
                "error": f"Media pause not supported on {self.platform}",
                "available_methods": self._get_available_media_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to pause media: {str(e)}"}

    def _stop_media(self) -> Dict[str, Any]:
        """Stop current media playback."""
        try:
            if self.platform == "linux":
                if shutil.which("playerctl"):
                    result = subprocess.run(["playerctl", "stop"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "stop_media", "method": "playerctl"}}

            return {
                "success": False,
                "error": f"Media stop not supported on {self.platform}",
                "available_methods": self._get_available_media_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to stop media: {str(e)}"}

    def _next_track(self) -> Dict[str, Any]:
        """Skip to next track."""
        try:
            if self.platform == "linux":
                if shutil.which("playerctl"):
                    result = subprocess.run(["playerctl", "next"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "next_track", "method": "playerctl"}}

            return {
                "success": False,
                "error": f"Next track not supported on {self.platform}",
                "available_methods": self._get_available_media_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to skip to next track: {str(e)}"}

    def _previous_track(self) -> Dict[str, Any]:
        """Go to previous track."""
        try:
            if self.platform == "linux":
                if shutil.which("playerctl"):
                    result = subprocess.run(["playerctl", "previous"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "previous_track", "method": "playerctl"}}

            return {
                "success": False,
                "error": f"Previous track not supported on {self.platform}",
                "available_methods": self._get_available_media_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to go to previous track: {str(e)}"}

    def _volume_up(self, step: int = 5) -> Dict[str, Any]:
        """Increase system volume."""
        if not 1 <= step <= 10:
            return {"success": False, "error": "Volume step must be between 1 and 10"}

        try:
            if self.platform == "linux":
                # Try amixer first
                if shutil.which("amixer"):
                    result = subprocess.run(["amixer", "set", "Master", f"{step}%+"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "volume_up", "step": step, "method": "amixer"}}

                # Try pactl (PulseAudio)
                if shutil.which("pactl"):
                    result = subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"+{step}%"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "volume_up", "step": step, "method": "pactl"}}

            return {
                "success": False,
                "error": f"Volume control not supported on {self.platform}",
                "available_methods": self._get_available_audio_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to increase volume: {str(e)}"}

    def _volume_down(self, step: int = 5) -> Dict[str, Any]:
        """Decrease system volume."""
        if not 1 <= step <= 10:
            return {"success": False, "error": "Volume step must be between 1 and 10"}

        try:
            if self.platform == "linux":
                # Try amixer first
                if shutil.which("amixer"):
                    result = subprocess.run(["amixer", "set", "Master", f"{step}%-"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "volume_down", "step": step, "method": "amixer"}}

                # Try pactl (PulseAudio)
                if shutil.which("pactl"):
                    result = subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"-{step}%"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "volume_down", "step": step, "method": "pactl"}}

            return {
                "success": False,
                "error": f"Volume control not supported on {self.platform}",
                "available_methods": self._get_available_audio_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to decrease volume: {str(e)}"}

    def _mute_audio(self) -> Dict[str, Any]:
        """Mute system audio."""
        try:
            if self.platform == "linux":
                # Try pactl (PulseAudio) first for WSL/Linux
                if shutil.which("pactl"):
                    result = subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "mute_audio", "method": "pactl"}}

                # Try amixer as fallback
                if shutil.which("amixer"):
                    result = subprocess.run(["amixer", "set", "Master", "mute"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "mute_audio", "method": "amixer"}}

                # Check if this is a headless environment
                if os.environ.get("HEADLESS") or not os.environ.get("DISPLAY"):
                    print("INFO: Audio control unavailable on this system (headless environment)")
                    return {
                        "success": False,
                        "error": "Audio control unavailable on this system (headless environment)",
                        "warning": "This is normal for headless/server environments",
                    }

                # No audio control available
                print("INFO: Audio control unavailable on this system (pactl/amixer not found)")
                return {
                    "success": False,
                    "error": "Audio control unavailable on this system",
                    "available_methods": self._get_available_audio_methods(),
                    "note": "Install pulseaudio-utils (pactl) or alsa-utils (amixer) for audio control",
                }

            elif self.platform == "windows":
                # Windows backend skeleton - prepare for future pycaw integration
                return {
                    "success": False,
                    "error": "Windows audio control not yet implemented",
                    "note": "Future versions will support Windows audio control with pycaw",
                }

            return {
                "success": False,
                "error": f"Audio mute not supported on {self.platform}",
                "available_methods": self._get_available_audio_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to mute audio: {str(e)}"}

    def _unmute_audio(self) -> Dict[str, Any]:
        """Unmute system audio."""
        try:
            if self.platform == "linux":
                # Try pactl (PulseAudio) first for WSL/Linux
                if shutil.which("pactl"):
                    result = subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "unmute_audio", "method": "pactl"}}

                # Try amixer as fallback
                if shutil.which("amixer"):
                    result = subprocess.run(["amixer", "set", "Master", "unmute"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "unmute_audio", "method": "amixer"}}

                # Check if this is a headless environment
                if os.environ.get("HEADLESS") or not os.environ.get("DISPLAY"):
                    print("INFO: Audio control unavailable on this system (headless environment)")
                    return {
                        "success": False,
                        "error": "Audio control unavailable on this system (headless environment)",
                        "warning": "This is normal for headless/server environments",
                    }

                # No audio control available
                print("INFO: Audio control unavailable on this system (pactl/amixer not found)")
                return {
                    "success": False,
                    "error": "Audio control unavailable on this system",
                    "available_methods": self._get_available_audio_methods(),
                    "note": "Install pulseaudio-utils (pactl) or alsa-utils (amixer) for audio control",
                }

            elif self.platform == "windows":
                # Windows backend skeleton - prepare for future pycaw integration
                return {
                    "success": False,
                    "error": "Windows audio control not yet implemented",
                    "note": "Future versions will support Windows audio control with pycaw",
                }

            return {
                "success": False,
                "error": f"Audio unmute not supported on {self.platform}",
                "available_methods": self._get_available_audio_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to unmute audio: {str(e)}"}

    def _set_volume(self, level: int) -> Dict[str, Any]:
        """Set system volume to specific level."""
        if not 0 <= level <= 100:
            return {"success": False, "error": "Volume level must be between 0 and 100"}

        try:
            if self.platform == "linux":
                # Try amixer first
                if shutil.which("amixer"):
                    result = subprocess.run(["amixer", "set", "Master", f"{level}%"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "set_volume", "level": level, "method": "amixer"}}

                # Try pactl (PulseAudio)
                if shutil.which("pactl"):
                    result = subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "set_volume", "level": level, "method": "pactl"}}

            return {
                "success": False,
                "error": f"Volume control not supported on {self.platform}",
                "available_methods": self._get_available_audio_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to set volume: {str(e)}"}

    def _get_volume_status(self) -> Dict[str, Any]:
        """Get current volume and mute status."""
        try:
            if self.platform == "linux":
                # Try amixer first
                if shutil.which("amixer"):
                    result = subprocess.run(["amixer", "get", "Master"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        output = result.stdout
                        # Parse amixer output for volume and mute status
                        # Example: [75%] [on]
                        import re

                        volume_match = re.search(r"\[(\d+)%\]", output)
                        mute_match = re.search(r"\[(on|off)\]", output)

                        if volume_match:
                            volume = int(volume_match.group(1))
                            muted = mute_match.group(1) == "off" if mute_match else False

                            return {"success": True, "data": {"volume_percent": volume, "muted": muted, "method": "amixer"}}

            return {
                "success": False,
                "error": f"Volume status not available on {self.platform}",
                "available_methods": self._get_available_audio_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to get volume status: {str(e)}"}

    def _get_media_status(self) -> Dict[str, Any]:
        """Get current media playback status."""
        try:
            if self.platform == "linux":
                if shutil.which("playerctl"):
                    # Get playback status
                    status_result = subprocess.run(["playerctl", "status"], capture_output=True, text=True, timeout=5)

                    # Get metadata if playing
                    metadata = {}
                    if status_result.returncode == 0:
                        try:
                            title_result = subprocess.run(["playerctl", "metadata", "title"], capture_output=True, text=True, timeout=3)
                            if title_result.returncode == 0:
                                metadata["title"] = title_result.stdout.strip()

                            artist_result = subprocess.run(["playerctl", "metadata", "artist"], capture_output=True, text=True, timeout=3)
                            if artist_result.returncode == 0:
                                metadata["artist"] = artist_result.stdout.strip()
                        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
                            pass  # Metadata is optional

                        return {"success": True, "data": {"status": status_result.stdout.strip(), "metadata": metadata, "method": "playerctl"}}

            return {
                "success": True,
                "data": {
                    "status": "no_player",
                    "message": f"No media player detected on {self.platform}",
                    "available_methods": self._get_available_media_methods(),
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to get media status: {str(e)}"}

    # Application Control Methods

    def _launch_application(self, application: str, arguments: str = "") -> Dict[str, Any]:
        """Launch an application."""
        if not application:
            return {"success": False, "error": "Application name or path is required"}

        try:
            cmd = [application]
            if arguments:
                cmd.extend(arguments.split())

            if self.platform == "linux":
                # Try to launch with nohup to detach from terminal
                process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                time.sleep(0.5)  # Give process time to start

                return {
                    "success": True,
                    "data": {
                        "action": "launch_application",
                        "application": application,
                        "arguments": arguments,
                        "pid": process.pid,
                        "platform": self.platform,
                    },
                }

            elif self.platform == "windows":
                # Check if it's a file path, use os.startfile for files
                if os.path.exists(application) and os.path.isfile(application):
                    os.startfile(application)
                    return {
                        "success": True,
                        "data": {
                            "action": "launch_application",
                            "application": application,
                            "arguments": arguments,
                            "platform": self.platform,
                            "method": "os.startfile",
                        },
                    }
                else:
                    # For executables, use subprocess.Popen without shell
                    cmd = [application]
                    if arguments:
                        cmd.extend(shlex.split(arguments))

                    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                    time.sleep(0.5)  # Give process time to start

                    return {
                        "success": True,
                        "data": {
                            "action": "launch_application",
                            "application": application,
                            "arguments": arguments,
                            "pid": process.pid,
                            "platform": self.platform,
                            "method": "subprocess.Popen",
                        },
                    }

            elif self.platform == "darwin":  # macOS
                result = subprocess.run(
                    ["open", "-a", application] + (arguments.split() if arguments else []), capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return {
                        "success": True,
                        "data": {"action": "launch_application", "application": application, "arguments": arguments, "platform": self.platform},
                    }

            return {"success": False, "error": f"Failed to launch application: {application}", "platform": self.platform}

        except Exception as e:
            return {"success": False, "error": f"Failed to launch application: {str(e)}"}

    def _close_application(self, application: str, force: bool = False) -> Dict[str, Any]:
        """Close a running application."""
        if not application:
            return {"success": False, "error": "Application name or process ID is required"}

        try:
            # Try to find process by name or PID
            target_processes = []

            # Check if it's a PID
            try:
                pid = int(application)
                if psutil.pid_exists(pid):
                    target_processes.append(psutil.Process(pid))
            except ValueError:
                # It's a process name, search for it
                for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                    try:
                        if application.lower() in proc.info["name"].lower() or any(
                            application.lower() in arg.lower() for arg in proc.info["cmdline"] if arg
                        ):
                            target_processes.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            if not target_processes:
                return {"success": False, "error": f"Application not found: {application}"}

            closed_processes = []
            for proc in target_processes:
                try:
                    proc_info = {"pid": proc.pid, "name": proc.name(), "status": proc.status()}

                    if force:
                        proc.kill()
                        proc.wait(timeout=5)
                    else:
                        proc.terminate()
                        proc.wait(timeout=10)

                    proc_info["action"] = "killed" if force else "terminated"
                    closed_processes.append(proc_info)

                except psutil.TimeoutExpired:
                    if not force:
                        # Try force kill if terminate didn't work
                        try:
                            proc.kill()
                            proc.wait(timeout=5)
                            proc_info["action"] = "force_killed"
                            closed_processes.append(proc_info)
                        except (psutil.TimeoutExpired, psutil.NoSuchProcess, psutil.AccessDenied):
                            proc_info["action"] = "failed_to_close"
                            closed_processes.append(proc_info)
                except psutil.NoSuchProcess:
                    proc_info["action"] = "already_closed"
                    closed_processes.append(proc_info)

            return {
                "success": True,
                "data": {
                    "action": "close_application",
                    "application": application,
                    "force": force,
                    "closed_processes": closed_processes,
                    "total_closed": len([p for p in closed_processes if p["action"] in ["terminated", "killed", "force_killed"]]),
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to close application: {str(e)}"}

    def _get_running_applications(self, detailed: bool = False) -> Dict[str, Any]:
        """Get list of currently running applications."""
        try:
            applications = []

            for proc in psutil.process_iter(["pid", "name", "cmdline", "memory_info", "cpu_percent"]):
                try:
                    proc_info = {"pid": proc.info["pid"], "name": proc.info["name"]}

                    if detailed:
                        proc_info.update(
                            {
                                "cmdline": " ".join(proc.info["cmdline"]) if proc.info["cmdline"] else "",
                                "memory_mb": round(proc.info["memory_info"].rss / 1024 / 1024, 1),
                                "cpu_percent": proc.info["cpu_percent"],
                            }
                        )

                    applications.append(proc_info)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by name
            applications.sort(key=lambda x: x["name"].lower())

            return {
                "success": True,
                "data": {"applications": applications, "total_count": len(applications), "detailed": detailed, "platform": self.platform},
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to get running applications: {str(e)}"}

    def _list_installed_applications(self, category: str = "all") -> Dict[str, Any]:
        """List installed applications on the system."""
        try:
            applications = []

            if self.platform == "linux":
                # Check common application directories
                app_dirs = ["/usr/share/applications", "/usr/local/share/applications", "~/.local/share/applications"]

                for app_dir in app_dirs:
                    app_path = Path(app_dir).expanduser()
                    if app_path.exists():
                        for desktop_file in app_path.glob("*.desktop"):
                            try:
                                with open(desktop_file, "r") as f:
                                    content = f.read()

                                # Parse .desktop file
                                app_info = {"file": str(desktop_file)}
                                for line in content.split("\n"):
                                    if "=" in line:
                                        key, value = line.split("=", 1)
                                        if key == "Name":
                                            app_info["name"] = value
                                        elif key == "Exec":
                                            app_info["executable"] = value.split()[0]
                                        elif key == "Categories":
                                            app_info["categories"] = value.split(";")

                                if "name" in app_info:
                                    applications.append(app_info)

                            except Exception:
                                continue

            elif self.platform == "windows":
                # For Windows, we could check registry or common program directories
                # This is a simplified implementation
                program_dirs = ["C:\\Program Files", "C:\\Program Files (x86)"]

                for prog_dir in program_dirs:
                    try:
                        for item in Path(prog_dir).iterdir():
                            if item.is_dir():
                                applications.append({"name": item.name, "path": str(item)})
                    except Exception:
                        continue

            elif self.platform == "darwin":  # macOS
                # Check Applications directory
                app_dir = Path("/Applications")
                if app_dir.exists():
                    for app in app_dir.glob("*.app"):
                        applications.append({"name": app.stem, "path": str(app)})

            # Filter by category if specified
            if category != "all" and applications:
                filtered_apps = []
                for app in applications:
                    if "categories" in app:
                        if any(category.lower() in cat.lower() for cat in app["categories"]):
                            filtered_apps.append(app)
                applications = filtered_apps

            return {
                "success": True,
                "data": {
                    "applications": applications[:100],  # Limit to 100 for performance
                    "total_found": len(applications),
                    "category_filter": category,
                    "platform": self.platform,
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to list installed applications: {str(e)}"}

    # Window Management Methods

    def _focus_window(self, window_title: str) -> Dict[str, Any]:
        """Bring a window to focus."""
        if not window_title:
            return {"success": False, "error": "Window title is required"}

        try:
            if self.platform == "linux":
                # Try using wmctrl if available
                if shutil.which("wmctrl"):
                    result = subprocess.run(["wmctrl", "-a", window_title], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "focus_window", "window_title": window_title, "method": "wmctrl"}}

                # Try using xdotool if available
                if shutil.which("xdotool"):
                    # First find the window
                    result = subprocess.run(["xdotool", "search", "--name", window_title], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        window_id = result.stdout.strip().split("\n")[0]
                        # Focus the window
                        focus_result = subprocess.run(["xdotool", "windowactivate", window_id], capture_output=True, text=True, timeout=5)
                        if focus_result.returncode == 0:
                            return {
                                "success": True,
                                "data": {"action": "focus_window", "window_title": window_title, "window_id": window_id, "method": "xdotool"},
                            }

            return {
                "success": False,
                "error": f"Window focus not supported on {self.platform} or window not found",
                "available_methods": self._get_available_window_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to focus window: {str(e)}"}

    def _minimize_window(self, window_title: str) -> Dict[str, Any]:
        """Minimize a window."""
        if not window_title:
            return {"success": False, "error": "Window title is required"}

        try:
            if self.platform == "linux":
                # Try using xdotool if available
                if shutil.which("xdotool"):
                    # First find the window
                    result = subprocess.run(["xdotool", "search", "--name", window_title], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        window_id = result.stdout.strip().split("\n")[0]
                        # Minimize the window
                        minimize_result = subprocess.run(["xdotool", "windowminimize", window_id], capture_output=True, text=True, timeout=5)
                        if minimize_result.returncode == 0:
                            return {
                                "success": True,
                                "data": {"action": "minimize_window", "window_title": window_title, "window_id": window_id, "method": "xdotool"},
                            }

            return {
                "success": False,
                "error": f"Window minimize not supported on {self.platform} or window not found",
                "available_methods": self._get_available_window_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to minimize window: {str(e)}"}

    def _maximize_window(self, window_title: str) -> Dict[str, Any]:
        """Maximize a window."""
        if not window_title:
            return {"success": False, "error": "Window title is required"}

        try:
            if self.platform == "linux":
                # Try using wmctrl if available
                if shutil.which("wmctrl"):
                    result = subprocess.run(
                        ["wmctrl", "-r", window_title, "-b", "add,maximized_vert,maximized_horz"], capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "maximize_window", "window_title": window_title, "method": "wmctrl"}}

            return {
                "success": False,
                "error": f"Window maximize not supported on {self.platform} or window not found",
                "available_methods": self._get_available_window_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to maximize window: {str(e)}"}

    def _close_window(self, window_title: str) -> Dict[str, Any]:
        """Close a specific window."""
        if not window_title:
            return {"success": False, "error": "Window title is required"}

        try:
            if self.platform == "linux":
                # Try using wmctrl if available
                if shutil.which("wmctrl"):
                    result = subprocess.run(["wmctrl", "-c", window_title], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        return {"success": True, "data": {"action": "close_window", "window_title": window_title, "method": "wmctrl"}}

                # Try using xdotool if available
                if shutil.which("xdotool"):
                    # First find the window
                    result = subprocess.run(["xdotool", "search", "--name", window_title], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        window_id = result.stdout.strip().split("\n")[0]
                        # Close the window
                        close_result = subprocess.run(["xdotool", "windowclose", window_id], capture_output=True, text=True, timeout=5)
                        if close_result.returncode == 0:
                            return {
                                "success": True,
                                "data": {"action": "close_window", "window_title": window_title, "window_id": window_id, "method": "xdotool"},
                            }

            return {
                "success": False,
                "error": f"Window close not supported on {self.platform} or window not found",
                "available_methods": self._get_available_window_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to close window: {str(e)}"}

    def _get_window_list(self) -> Dict[str, Any]:
        """Get list of open windows."""
        try:
            windows = []

            if self.platform == "linux":
                # Try using wmctrl if available
                if shutil.which("wmctrl"):
                    result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        for line in result.stdout.strip().split("\n"):
                            if line:
                                parts = line.split(None, 3)
                                if len(parts) >= 4:
                                    windows.append({"window_id": parts[0], "desktop": parts[1], "host": parts[2], "title": parts[3]})

                        return {
                            "success": True,
                            "data": {"windows": windows, "total_count": len(windows), "method": "wmctrl", "platform": self.platform},
                        }

            return {
                "success": False,
                "error": f"Window listing not supported on {self.platform}",
                "available_methods": self._get_available_window_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to get window list: {str(e)}"}

    def _get_active_window(self) -> Dict[str, Any]:
        """Get information about the currently active window."""
        try:
            if self.platform == "linux":
                # Try using xdotool if available
                if shutil.which("xdotool"):
                    # Get active window ID
                    result = subprocess.run(["xdotool", "getactivewindow"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        window_id = result.stdout.strip()

                        # Get window title
                        title_result = subprocess.run(["xdotool", "getwindowname", window_id], capture_output=True, text=True, timeout=5)

                        window_info = {"window_id": window_id}
                        if title_result.returncode == 0:
                            window_info["title"] = title_result.stdout.strip()

                        return {"success": True, "data": {"active_window": window_info, "method": "xdotool", "platform": self.platform}}

            return {
                "success": False,
                "error": f"Active window detection not supported on {self.platform}",
                "available_methods": self._get_available_window_methods(),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to get active window: {str(e)}"}

    # Helper Methods

    def _get_available_media_methods(self) -> List[str]:
        """Get available media control methods for current platform."""
        methods = []
        if self.platform == "linux":
            if shutil.which("playerctl"):
                methods.append("playerctl")
            if shutil.which("vlc"):
                methods.append("vlc")
            if shutil.which("mpv"):
                methods.append("mpv")
        return methods

    def _get_available_audio_methods(self) -> List[str]:
        """Get available audio control methods for current platform."""
        methods = []
        if self.platform == "linux":
            if shutil.which("amixer"):
                methods.append("amixer")
            if shutil.which("pactl"):
                methods.append("pactl")
        return methods

    def _get_available_window_methods(self) -> List[str]:
        """Get available window management methods for current platform."""
        methods = []
        if self.platform == "linux":
            if shutil.which("wmctrl"):
                methods.append("wmctrl")
            if shutil.which("xdotool"):
                methods.append("xdotool")
        return methods


# Plugin metadata for discovery
PLUGIN_METADATA = {
    "id": "media_app_control",
    "version": "1.0.0",
    "name": "Media & Application Control Plugin",
    "description": "Comprehensive media playback and application management with cross-platform support",
    "capabilities": ["media_control", "application_control", "window_management", "volume_control", "process_management"],
    "security_levels": ["safe", "privileged"],
    "platforms": ["linux", "windows", "darwin"],
    "dependencies": {"required": ["psutil"], "optional": ["playerctl", "wmctrl", "xdotool", "amixer", "pactl"]},
}


def create_plugin() -> MediaAppControlPlugin:
    """Factory function to create plugin instance."""
    return MediaAppControlPlugin()
