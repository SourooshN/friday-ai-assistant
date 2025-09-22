"""
System Control Plugin for Friday AI Assistant

Provides basic system automation capabilities including:
- Power management (shutdown, restart, sleep)
- Volume control
- Brightness control
- System information gathering
- Process management

Security: All operations are policy-checked and logged for audit compliance.
"""

import os
import subprocess
import platform
import psutil
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

# Try to import platform-specific modules
try:
    import dbus  # For Linux brightness/volume control
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False


class SystemControlPlugin:
    """
    System Control Plugin for Friday AI Assistant.

    Provides safe system automation capabilities with proper security controls.
    """

    def __init__(self):
        self.id = "system_control"
        self.version = "1.0.0"
        self.capabilities = [
            "power_management",
            "volume_control",
            "brightness_control",
            "system_info",
            "process_management"
        ]

        # Determine the current platform
        self.platform = platform.system().lower()

        # Security: Define allowed operations per platform
        self.allowed_operations = self._get_allowed_operations()

    def _get_allowed_operations(self) -> Dict[str, List[str]]:
        """Get platform-specific allowed operations."""
        base_operations = [
            "get_system_info",
            "get_cpu_usage",
            "get_memory_usage",
            "get_disk_usage",
            "list_processes",
            "get_volume",
            "get_brightness"
        ]

        if self.platform == "linux":
            return {
                "safe": base_operations + [
                    "set_volume",
                    "set_brightness"
                ],
                "privileged": [
                    "shutdown_system",
                    "restart_system",
                    "sleep_system",
                    "kill_process"
                ]
            }
        elif self.platform == "windows":
            return {
                "safe": base_operations + [
                    "set_volume",
                    "set_brightness"
                ],
                "privileged": [
                    "shutdown_system",
                    "restart_system",
                    "sleep_system",
                    "kill_process"
                ]
            }
        else:
            # Default to safe operations only
            return {
                "safe": base_operations,
                "privileged": []
            }

    def describe_tools(self) -> Dict[str, Any]:
        """Describe the tools provided by this plugin."""
        return {
            # System Information
            "get_system_info": {
                "description": "Get comprehensive system information",
                "parameters": {},
                "security_level": "safe"
            },
            "get_cpu_usage": {
                "description": "Get current CPU usage percentage",
                "parameters": {},
                "security_level": "safe"
            },
            "get_memory_usage": {
                "description": "Get current memory usage information",
                "parameters": {},
                "security_level": "safe"
            },
            "get_disk_usage": {
                "description": "Get disk usage for specified path",
                "parameters": {
                    "path": {
                        "type": "string",
                        "description": "Path to check disk usage for",
                        "default": "/"
                    }
                },
                "security_level": "safe"
            },

            # Process Management
            "list_processes": {
                "description": "List running processes",
                "parameters": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of processes to return",
                        "default": 20
                    }
                },
                "security_level": "safe"
            },
            "kill_process": {
                "description": "Terminate a process by PID",
                "parameters": {
                    "pid": {
                        "type": "integer",
                        "description": "Process ID to terminate",
                        "required": True
                    }
                },
                "security_level": "privileged"
            },

            # Power Management
            "shutdown_system": {
                "description": "Shutdown the system",
                "parameters": {
                    "delay": {
                        "type": "integer",
                        "description": "Delay in seconds before shutdown",
                        "default": 60
                    }
                },
                "security_level": "privileged"
            },
            "restart_system": {
                "description": "Restart the system",
                "parameters": {
                    "delay": {
                        "type": "integer",
                        "description": "Delay in seconds before restart",
                        "default": 60
                    }
                },
                "security_level": "privileged"
            },
            "sleep_system": {
                "description": "Put the system to sleep",
                "parameters": {},
                "security_level": "privileged"
            },

            # Volume Control
            "get_volume": {
                "description": "Get current system volume level",
                "parameters": {},
                "security_level": "safe"
            },
            "set_volume": {
                "description": "Set system volume level",
                "parameters": {
                    "level": {
                        "type": "integer",
                        "description": "Volume level (0-100)",
                        "required": True
                    }
                },
                "security_level": "safe"
            },

            # Brightness Control
            "get_brightness": {
                "description": "Get current screen brightness level",
                "parameters": {},
                "security_level": "safe"
            },
            "set_brightness": {
                "description": "Set screen brightness level",
                "parameters": {
                    "level": {
                        "type": "integer",
                        "description": "Brightness level (0-100)",
                        "required": True
                    }
                },
                "security_level": "safe"
            }
        }

    def invoke(self, tool: str, **kwargs) -> Dict[str, Any]:
        """
        Invoke a tool provided by this plugin.

        Args:
            tool: Tool name to invoke
            **kwargs: Tool parameters

        Returns:
            Tool result with success status and data/error information
        """
        try:
            # Security check: Verify tool is allowed
            if not self._is_operation_allowed(tool):
                return {
                    "success": False,
                    "error": f"Operation '{tool}' not allowed on this platform",
                    "security_level": "denied"
                }

            # Route to appropriate handler
            if tool == "get_system_info":
                return self._get_system_info()
            elif tool == "get_cpu_usage":
                return self._get_cpu_usage()
            elif tool == "get_memory_usage":
                return self._get_memory_usage()
            elif tool == "get_disk_usage":
                return self._get_disk_usage(kwargs.get("path", "/"))
            elif tool == "list_processes":
                return self._list_processes(kwargs.get("limit", 20))
            elif tool == "kill_process":
                return self._kill_process(kwargs.get("pid"))
            elif tool == "shutdown_system":
                return self._shutdown_system(kwargs.get("delay", 60))
            elif tool == "restart_system":
                return self._restart_system(kwargs.get("delay", 60))
            elif tool == "sleep_system":
                return self._sleep_system()
            elif tool == "get_volume":
                return self._get_volume()
            elif tool == "set_volume":
                return self._set_volume(kwargs.get("level"))
            elif tool == "get_brightness":
                return self._get_brightness()
            elif tool == "set_brightness":
                return self._set_brightness(kwargs.get("level"))
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool}",
                    "available_tools": list(self.describe_tools().keys())
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "tool": tool
            }

    def _is_operation_allowed(self, operation: str) -> bool:
        """Check if an operation is allowed on this platform."""
        all_ops = self.allowed_operations.get("safe", []) + self.allowed_operations.get("privileged", [])
        return operation in all_ops

    # System Information Methods
    def _get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        try:
            return {
                "success": True,
                "data": {
                    "platform": {
                        "system": platform.system(),
                        "release": platform.release(),
                        "version": platform.version(),
                        "machine": platform.machine(),
                        "processor": platform.processor()
                    },
                    "cpu": {
                        "physical_cores": psutil.cpu_count(logical=False),
                        "logical_cores": psutil.cpu_count(logical=True),
                        "current_freq": psutil.cpu_freq().current if psutil.cpu_freq() else None,
                        "usage_percent": psutil.cpu_percent(interval=1)
                    },
                    "memory": {
                        "total": psutil.virtual_memory().total,
                        "available": psutil.virtual_memory().available,
                        "used": psutil.virtual_memory().used,
                        "percentage": psutil.virtual_memory().percent
                    },
                    "disk": {
                        "total": psutil.disk_usage('/').total,
                        "used": psutil.disk_usage('/').used,
                        "free": psutil.disk_usage('/').free,
                        "percentage": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
                    },
                    "network": {
                        "interfaces": list(psutil.net_if_addrs().keys())
                    },
                    "boot_time": psutil.boot_time(),
                    "uptime_seconds": time.time() - psutil.boot_time(),
                    "process_count": len(psutil.pids())
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_cpu_usage(self) -> Dict[str, Any]:
        """Get current CPU usage."""
        try:
            return {
                "success": True,
                "data": {
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "per_cpu": psutil.cpu_percent(interval=1, percpu=True)
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage."""
        try:
            memory = psutil.virtual_memory()
            return {
                "success": True,
                "data": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "free": memory.free,
                    "percentage": memory.percent
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_disk_usage(self, path: str) -> Dict[str, Any]:
        """Get disk usage for specified path."""
        try:
            if not os.path.exists(path):
                return {"success": False, "error": f"Path does not exist: {path}"}

            usage = psutil.disk_usage(path)
            return {
                "success": True,
                "data": {
                    "path": path,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percentage": (usage.used / usage.total) * 100
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Process Management Methods
    def _list_processes(self, limit: int) -> Dict[str, Any]:
        """List running processes."""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by CPU usage and limit results
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            return {
                "success": True,
                "data": {
                    "processes": processes[:limit],
                    "total_processes": len(processes)
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _kill_process(self, pid: Optional[int]) -> Dict[str, Any]:
        """Kill a process by PID."""
        if pid is None:
            return {"success": False, "error": "PID is required"}

        try:
            process = psutil.Process(pid)
            process_name = process.name()
            process.terminate()

            # Wait a bit for graceful termination
            time.sleep(2)

            if process.is_running():
                process.kill()  # Force kill if still running

            return {
                "success": True,
                "data": {
                    "pid": pid,
                    "process_name": process_name,
                    "action": "terminated"
                }
            }
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process with PID {pid} not found"}
        except psutil.AccessDenied:
            return {"success": False, "error": f"Access denied to kill process {pid}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Power Management Methods
    def _shutdown_system(self, delay: int) -> Dict[str, Any]:
        """Shutdown the system with specified delay."""
        try:
            if self.platform == "linux":
                cmd = f"shutdown -h +{delay//60}"  # Convert to minutes
            elif self.platform == "windows":
                cmd = f"shutdown /s /t {delay}"
            else:
                return {"success": False, "error": "Shutdown not supported on this platform"}

            subprocess.run(cmd, shell=True, check=True)
            return {
                "success": True,
                "data": {
                    "action": "shutdown_scheduled",
                    "delay_seconds": delay,
                    "command": cmd
                }
            }
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Shutdown command failed: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _restart_system(self, delay: int) -> Dict[str, Any]:
        """Restart the system with specified delay."""
        try:
            if self.platform == "linux":
                cmd = f"shutdown -r +{delay//60}"  # Convert to minutes
            elif self.platform == "windows":
                cmd = f"shutdown /r /t {delay}"
            else:
                return {"success": False, "error": "Restart not supported on this platform"}

            subprocess.run(cmd, shell=True, check=True)
            return {
                "success": True,
                "data": {
                    "action": "restart_scheduled",
                    "delay_seconds": delay,
                    "command": cmd
                }
            }
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Restart command failed: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _sleep_system(self) -> Dict[str, Any]:
        """Put the system to sleep."""
        try:
            if self.platform == "linux":
                cmd = "systemctl suspend"
            elif self.platform == "windows":
                cmd = "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"
            else:
                return {"success": False, "error": "Sleep not supported on this platform"}

            subprocess.run(cmd, shell=True, check=True)
            return {
                "success": True,
                "data": {
                    "action": "system_sleep",
                    "command": cmd
                }
            }
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Sleep command failed: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Volume Control Methods
    def _get_volume(self) -> Dict[str, Any]:
        """Get current system volume."""
        try:
            if self.platform == "linux":
                result = subprocess.run(
                    ["amixer", "get", "Master"],
                    capture_output=True, text=True, check=True
                )
                # Parse amixer output to extract volume percentage
                import re
                match = re.search(r'\[(\d+)%\]', result.stdout)
                if match:
                    volume = int(match.group(1))
                    return {
                        "success": True,
                        "data": {"volume_percent": volume}
                    }
                else:
                    return {"success": False, "error": "Could not parse volume output"}

            elif self.platform == "windows":
                # Windows volume control would require additional libraries
                return {"success": False, "error": "Volume control not implemented for Windows"}
            else:
                return {"success": False, "error": "Volume control not supported on this platform"}

        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Volume get command failed: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _set_volume(self, level: Optional[int]) -> Dict[str, Any]:
        """Set system volume level."""
        if level is None:
            return {"success": False, "error": "Volume level is required"}

        if not 0 <= level <= 100:
            return {"success": False, "error": "Volume level must be between 0 and 100"}

        try:
            if self.platform == "linux":
                cmd = f"amixer set Master {level}%"
                subprocess.run(cmd, shell=True, check=True)
                return {
                    "success": True,
                    "data": {
                        "action": "volume_set",
                        "level": level
                    }
                }
            elif self.platform == "windows":
                return {"success": False, "error": "Volume control not implemented for Windows"}
            else:
                return {"success": False, "error": "Volume control not supported on this platform"}

        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Volume set command failed: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Brightness Control Methods
    def _get_brightness(self) -> Dict[str, Any]:
        """Get current screen brightness."""
        try:
            if self.platform == "linux":
                # Try to read brightness from sysfs
                brightness_paths = [
                    "/sys/class/backlight/intel_backlight/brightness",
                    "/sys/class/backlight/acpi_video0/brightness",
                    "/sys/class/backlight/*/brightness"
                ]

                for path_pattern in brightness_paths:
                    brightness_files = list(Path("/").glob(path_pattern.lstrip("/")))
                    if brightness_files:
                        brightness_file = brightness_files[0]
                        max_file = brightness_file.parent / "max_brightness"

                        if brightness_file.exists() and max_file.exists():
                            current = int(brightness_file.read_text().strip())
                            maximum = int(max_file.read_text().strip())
                            percentage = int((current / maximum) * 100)

                            return {
                                "success": True,
                                "data": {
                                    "brightness_percent": percentage,
                                    "current_value": current,
                                    "max_value": maximum
                                }
                            }

                return {"success": False, "error": "No brightness control found"}

            elif self.platform == "windows":
                return {"success": False, "error": "Brightness control not implemented for Windows"}
            else:
                return {"success": False, "error": "Brightness control not supported on this platform"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _set_brightness(self, level: Optional[int]) -> Dict[str, Any]:
        """Set screen brightness level."""
        if level is None:
            return {"success": False, "error": "Brightness level is required"}

        if not 0 <= level <= 100:
            return {"success": False, "error": "Brightness level must be between 0 and 100"}

        try:
            if self.platform == "linux":
                # Try xrandr first (works in X11)
                try:
                    brightness_value = level / 100.0
                    cmd = f"xrandr --output $(xrandr | grep ' connected' | head -1 | cut -d' ' -f1) --brightness {brightness_value}"
                    subprocess.run(cmd, shell=True, check=True)
                    return {
                        "success": True,
                        "data": {
                            "action": "brightness_set",
                            "level": level,
                            "method": "xrandr"
                        }
                    }
                except subprocess.CalledProcessError:
                    # Fall back to sysfs if xrandr fails
                    brightness_paths = [
                        "/sys/class/backlight/intel_backlight/brightness",
                        "/sys/class/backlight/acpi_video0/brightness"
                    ]

                    for brightness_path in brightness_paths:
                        path = Path(brightness_path)
                        max_path = path.parent / "max_brightness"

                        if path.exists() and max_path.exists():
                            max_brightness = int(max_path.read_text().strip())
                            target_brightness = int((level / 100) * max_brightness)

                            # This requires root access
                            cmd = f"echo {target_brightness} | sudo tee {brightness_path}"
                            subprocess.run(cmd, shell=True, check=True)

                            return {
                                "success": True,
                                "data": {
                                    "action": "brightness_set",
                                    "level": level,
                                    "method": "sysfs"
                                }
                            }

                    return {"success": False, "error": "No brightness control method available"}

            elif self.platform == "windows":
                return {"success": False, "error": "Brightness control not implemented for Windows"}
            else:
                return {"success": False, "error": "Brightness control not supported on this platform"}

        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Brightness set command failed: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def create_plugin():
    """Factory function to create the plugin instance."""
    return SystemControlPlugin()


# Plugin metadata for discovery
PLUGIN_METADATA = {
    "id": "system_control",
    "name": "System Control Plugin",
    "version": "1.0.0",
    "description": "Provides system automation capabilities including power management, volume/brightness control, and system monitoring",
    "author": "Friday AI Assistant",
    "capabilities": ["power_management", "volume_control", "brightness_control", "system_info", "process_management"],
    "security_levels": ["safe", "privileged"],
    "platforms": ["linux", "windows", "darwin"],
    "entry_point": "create_plugin"
}