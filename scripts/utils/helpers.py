"""
Utility functions for Friday AI Assistant
"""

import os
import yaml
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union
from datetime import datetime
import hashlib
import asyncio
from functools import wraps
import platform
import psutil
from dotenv import load_dotenv
from loguru import logger


def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """Load configuration from YAML file"""
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Load environment variables
    load_dotenv()
    
    # Override with environment variables
    config = _apply_env_overrides(config)
    
    return config


def _apply_env_overrides(config: Dict[str, Any], prefix: str = "FRIDAY") -> Dict[str, Any]:
    """Apply environment variable overrides to configuration"""
    for key, value in os.environ.items():
        if key.startswith(f"{prefix}_"):
            # Convert FRIDAY_SECTION_KEY to section.key
            config_path = key[len(prefix) + 1:].lower().split('_')
            
            # Navigate to the correct position in config
            current = config
            for part in config_path[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the value (attempt to parse JSON for complex types)
            try:
                current[config_path[-1]] = json.loads(value)
            except json.JSONDecodeError:
                current[config_path[-1]] = value
    
    return config


def setup_logging(log_config: Dict[str, Any]) -> logging.Logger:
    """Setup logging configuration"""
    # Configure loguru
    logger.remove()  # Remove default handler
    
    # Console logging
    log_level = log_config.get('level', 'INFO')
    log_format = log_config.get('format', '{time} | {level} | {name}:{function}:{line} - {message}')
    
    logger.add(
        sink=lambda msg: print(msg, end=''),
        format=log_format,
        level=log_level,
        colorize=True
    )
    
    # File logging
    if 'file' in log_config:
        logger.add(
            sink=log_config['file'],
            format=log_format,
            level=log_level,
            rotation=log_config.get('rotation', '100 MB'),
            retention=log_config.get('retention', '1 week'),
            compression="zip"
        )
    
    # Bridge standard logging to loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Get corresponding Loguru level if it exists
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # Find caller from where originated the logged message
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    
    return logger


def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    return {
        'platform': platform.system(),
        'platform_release': platform.release(),
        'platform_version': platform.version(),
        'architecture': platform.machine(),
        'processor': platform.processor(),
        'ram_gb': round(psutil.virtual_memory().total / (1024**3), 2),
        'cpu_count': psutil.cpu_count(),
        'python_version': platform.python_version(),
    }


def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if not"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_id(prefix: str = "") -> str:
    """Generate unique ID with optional prefix"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_part = hashlib.md5(os.urandom(16)).hexdigest()[:8]
    
    if prefix:
        return f"{prefix}_{timestamp}_{random_part}"
    return f"{timestamp}_{random_part}"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    # Remove invalid characters
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Limit length
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    
    return filename


def rate_limit(calls: int = 1, period: float = 1.0):
    """Rate limiting decorator"""
    min_interval = period / calls
    last_called = {}
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = func.__name__
            current_time = asyncio.get_event_loop().time()
            
            if key in last_called:
                elapsed = current_time - last_called[key]
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
            
            last_called[key] = asyncio.get_event_loop().time()
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def retry_async(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Async retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"Failed after {max_attempts} attempts: {str(e)}")
                        raise
                    
                    logger.warning(f"Attempt {attempt} failed, retrying in {current_delay}s: {str(e)}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
        return wrapper
    return decorator


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def chunk_list(lst: list, chunk_size: int) -> list:
    """Split list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


class AsyncContextManager:
    """Base class for async context managers"""
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
    
    async def start(self):
        """Override in subclass"""
        pass
    
    async def stop(self):
        """Override in subclass"""
        pass


def is_windows() -> bool:
    """Check if running on Windows"""
    return platform.system() == 'Windows'


def is_admin() -> bool:
    """Check if running with administrator privileges"""
    if is_windows():
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    else:
        return os.geteuid() == 0


def get_project_root() -> Path:
    """Get project root directory"""
    # Traverse up from current file location
    current = Path(__file__).resolve()
    
    # Look for key project files/directories
    markers = ['main.py', '.git', 'pyproject.toml', 'setup.py']
    
    for parent in current.parents:
        if any((parent / marker).exists() for marker in markers):
            return parent
    
    # Fallback to 3 levels up from this file
    return current.parent.parent.parent


# Common paths
PROJECT_ROOT = get_project_root()
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = DATA_DIR / "logs"
MEMORY_DIR = DATA_DIR / "memory"


# Ensure essential directories exist
ensure_directory(LOGS_DIR)
ensure_directory(MEMORY_DIR)