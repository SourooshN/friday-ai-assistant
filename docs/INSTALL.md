# Friday AI Assistant - Installation Guide

## System Requirements

### Supported Platforms
- **Linux (Ubuntu 20.04+)** - Fully supported
- **Windows Subsystem for Linux (WSL2)** - Fully supported (recommended for Windows users)
- **Windows 10/11** - Basic support (future audio control planned)
- **macOS** - Basic support (community contributions welcome)

### Python Requirements
- **Python 3.11 or higher** (required)
- pip package manager
- Virtual environment (recommended)

### System Dependencies

#### Ubuntu/Debian
```bash
# Core system packages
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv

# Audio control (optional, for media commands)
sudo apt install pulseaudio-utils alsa-utils

# Web automation dependencies (optional)
sudo apt install chromium-browser firefox

# Security tools (optional, for security operations)
sudo apt install nmap

# Development tools (optional)
sudo apt install git curl wget
```

#### Windows (WSL2 Recommended)
```powershell
# Install WSL2 with Ubuntu
wsl --install -d Ubuntu-22.04

# Then follow Ubuntu instructions inside WSL
```

#### macOS
```bash
# Install Homebrew if not available
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11
brew install python@3.11

# Optional audio tools
brew install portaudio
```

---

## Installation Methods

### Method 1: Development Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/friday-ai-assistant.git
cd friday-ai-assistant

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Verify installation
python3 main.py --status
```

### Method 2: Package Installation (Future)

```bash
# When published to PyPI (future release)
pip install friday-ai-assistant

# With optional dependencies
pip install friday-ai-assistant[windows,audio-full]
```

---

## Platform-Specific Configuration

### Ubuntu/Linux Configuration

#### Audio Control Setup
Friday AI Assistant uses `pactl` (PulseAudio) for audio control on Linux systems.

```bash
# Verify PulseAudio is running
pulseaudio --check

# If not running, start PulseAudio
pulseaudio --start

# Test audio control
pactl info
pactl list sinks short
```

**Audio Command Examples:**
```bash
# Test mute/unmute (will work if pactl is available)
python3 main.py --command "mute audio"
python3 main.py --command "unmute audio"
```

#### Headless Environment Considerations
If running in a headless environment (no display/audio), media commands will safely warn and continue:

```bash
# Set headless environment flag
export HEADLESS=1

# Media commands will show informational warnings
python3 main.py --command "mute audio"
# Output: "INFO: Audio control unavailable on this system (headless environment)"
```

### WSL2 Configuration

#### Audio in WSL2
WSL2 environments may not have direct audio access. Friday AI Assistant handles this gracefully:

```bash
# Check for audio system availability
pactl info 2>/dev/null || echo "No audio system detected"

# Media commands will provide helpful guidance
python3 main.py --command "get volume status"
```

**Expected Behavior in WSL2:**
- Media commands will detect missing audio backend
- Clean error messages with installation suggestions
- No crashes or hanging operations
- Future WSL→Windows audio bridge planned

#### Installing Audio Support in WSL2
```bash
# Install PulseAudio in WSL2 (may not connect to Windows audio)
sudo apt install pulseaudio pulseaudio-utils

# Alternative: Install ALSA utilities
sudo apt install alsa-utils
```

### Windows Native Configuration

#### Current Status
Windows native support is currently limited with future enhancements planned.

**Available Features:**
- File operations (fully supported)
- System monitoring (psutil-based)
- Web automation (Selenium/Playwright)
- Security operations (authorized targets only)

**Limited Features:**
- Audio control (placeholder implementation)
- System power management (basic support)

#### Future Windows Audio Support
A future release will include Windows-native audio control:

```bash
# Planned for v1.1.0
pip install friday-ai-assistant[windows]

# Will include pycaw for Windows audio control
```

**Current Windows Audio Behavior:**
```python
# Audio commands return helpful future implementation notes
{
    "success": false,
    "error": "Windows audio control not yet implemented",
    "note": "Future versions will support Windows audio control with pycaw"
}
```

---

## Configuration

### Environment Configuration

Friday AI Assistant supports multiple environment configurations:

```bash
# Development environment (default)
cp config/dev.yaml config/local.yaml

# Edit configuration as needed
nano config/local.yaml
```

### Audio Configuration

#### Automatic Detection
The system automatically detects available audio tools:

```python
# Priority order for Linux audio control:
1. pactl (PulseAudio) - preferred for WSL/modern Linux
2. amixer (ALSA) - fallback for older systems
3. Safe failure with helpful messages
```

#### Manual Configuration
You can verify audio tools manually:

```bash
# Check available audio tools
which pactl && echo "PulseAudio available"
which amixer && echo "ALSA available"

# Test audio commands
pactl list sinks short  # PulseAudio
amixer scontrols        # ALSA
```

### Plugin Configuration

#### Enabling/Disabling Features
```yaml
# config/local.yaml
plugins:
  enabled:
    - file_operations
    - system_control
    - media_app_control  # Disable if no audio needed
    - web_automation
    - security_ops
```

#### Security Configuration
```yaml
security:
  allowed_base_paths:
    - "/home/user/projects"
    - "/tmp"
  audio_control_enabled: true
  web_automation_enabled: true
```

---

## Verification and Testing

### Basic Functionality Test

```bash
# Test core system
python3 main.py --status

# Test file operations
python3 -c "
from plugins.available.file_operations import FileOperationsPlugin
plugin = FileOperationsPlugin()
result = plugin.invoke('list_directory', path='.')
print('File ops:', result['success'])
"

# Test system monitoring
python3 -c "
from plugins.available.system_control import SystemControlPlugin
plugin = SystemControlPlugin()
result = plugin.invoke('get_system_info')
print('System info:', result['success'])
"
```

### Audio System Test

```bash
# Test audio detection
python3 -c "
from plugins.available.media_app_control import MediaAppControlPlugin
plugin = MediaAppControlPlugin()

# Test audio methods availability
methods = plugin._get_available_audio_methods()
print('Available audio methods:', methods)

# Test mute command (safe - will warn if unavailable)
result = plugin.invoke('mute_audio')
print('Mute test:', result)
"
```

Expected outputs:
- **With audio**: `"Available audio methods: ['pactl']"` or `['amixer']`
- **Without audio**: `"Available audio methods: []"` and helpful error message
- **Headless**: Clean warning about headless environment

### Web Automation Test

```bash
# Test web automation (requires browser)
python3 -c "
from plugins.available.web_automation import WebAutomationPlugin
plugin = WebAutomationPlugin()
result = plugin.invoke('check_browser_availability')
print('Browser check:', result)
"
```

---

## Troubleshooting

### Common Issues

#### 1. Audio Commands Not Working

**Symptoms:**
```
"Audio control unavailable on this system"
```

**Solutions:**
```bash
# Install PulseAudio
sudo apt install pulseaudio pulseaudio-utils

# Or install ALSA
sudo apt install alsa-utils

# Restart PulseAudio
pulseaudio --kill
pulseaudio --start

# Verify audio system
pactl info || amixer
```

#### 2. WSL2 Audio Issues

**Expected Behavior:**
- WSL2 may not have direct Windows audio access
- Commands will provide clean warnings
- No system crashes or hangs

**Current Limitation:**
WSL2 → Windows audio bridge is planned for future release.

#### 3. Permission Errors

**Symptoms:**
```
"Access denied" or "Permission denied"
```

**Solutions:**
```bash
# Check file permissions
ls -la /path/to/file

# For system operations, ensure user has appropriate permissions
# Audio control typically doesn't require sudo
```

#### 4. Import Errors

**Symptoms:**
```
ImportError: No module named 'psutil'
```

**Solutions:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Or reinstall in development mode
pip install -e .
```

### Debug Mode

```bash
# Enable verbose logging
export FRIDAY_LOG_LEVEL=DEBUG

# Run with debug output
python3 main.py --debug --status
```

### Getting Help

1. **Check logs**: `./data/logs/friday_*.log`
2. **Run system status**: `python3 main.py --status`
3. **Test individual plugins**: Use test scripts in `tests/`
4. **Community support**: GitHub Issues and Discussions

---

## Development Setup

### Additional Development Dependencies

```bash
# Install development tools
pip install -r requirements.txt
pip install pytest black ruff mypy

# Run tests
python -m pytest tests/ -v

# Run linting
ruff check .
black --check .
mypy plugins/
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run all hooks
pre-commit run --all-files
```

---

## Performance Optimization

### Audio Performance
- Media commands timeout after 5 seconds to prevent hanging
- Audio tool detection is cached for performance
- Graceful fallbacks prevent system delays

### System Monitoring
- CPU/memory monitoring uses efficient psutil calls
- Process listing is limited to prevent memory issues
- Disk usage checks validate paths before access

### Web Automation
- Browser instances are properly managed
- Timeouts prevent indefinite waits
- Resource cleanup is automated

---

## Security Considerations

### Audio Control Security
- No privileged access required for basic audio operations
- Commands are validated before execution
- Safe fallbacks prevent security issues

### File Operations Security
- Path validation prevents directory traversal
- Sandboxed operation within allowed directories
- Comprehensive audit logging

### Network Operations Security
- Security operations require explicit target authorization
- No unauthorized network scanning
- Compliance with ethical hacking guidelines

---

**Note**: For platform-specific issues or advanced configuration, consult the project's GitHub repository and community discussions.