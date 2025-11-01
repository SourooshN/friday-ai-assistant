"""
Friday AI Assistant - Logging Module

Provides structured logging with configurable outputs, sensitive data redaction,
and audit trails as specified in the architecture.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger


class FridayLogger:
    """
    Centralized logging system for Friday AI Assistant.

    Features:
    - Structured JSON logging
    - Sensitive data redaction
    - Multiple output destinations
    - Configurable log levels
    - Audit trail capabilities
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.log_path = Path(config.get("path", "./data/logs"))
        self.level = config.get("level", "INFO")
        self.console_enabled = config.get("console", True)
        self.file_enabled = config.get("file", True)
        self.format_type = config.get("format", "structured")
        self.redact_sensitive = config.get("sensitive_data_redaction", True)

        # Ensure log directory exists
        self.log_path.mkdir(parents=True, exist_ok=True)

        # Setup loguru configuration
        self._setup_loguru()

        # Sensitive data patterns for redaction
        self.sensitive_patterns = [
            "password",
            "token",
            "key",
            "secret",
            "auth",
            "credential",
            "api_key",
            "access_token",
            "refresh_token",
            "private_key",
        ]

    def _setup_loguru(self):
        """Configure loguru logger with our settings."""
        # Remove default handler
        logger.remove()

        # Console handler
        if self.console_enabled:
            console_format = self._get_console_format()
            logger.add(sys.stderr, format=console_format, level=self.level, colorize=True)

        # File handler - main log
        if self.file_enabled:
            main_log_file = self.log_path / "friday.log"
            file_format = self._get_file_format()
            logger.add(
                main_log_file,
                format=file_format,
                level=self.level,
                rotation="10 MB",
                retention=self.config.get("retention", {}).get("detailed", "30 days"),
                compression="gz",
                serialize=self.format_type == "structured",
            )

            # Separate audit log for high-importance events
            audit_log_file = self.log_path / "audit.log"
            logger.add(
                audit_log_file,
                format=file_format,
                level="INFO",
                filter=lambda record: record.get("extra", {}).get("audit", False),
                rotation="5 MB",
                retention="1 year",
                compression="gz",
                serialize=True,
            )

    def _get_console_format(self) -> str:
        """Get format string for console output."""
        if self.format_type == "detailed":
            return (
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            )
        else:
            return "<green>{time:HH:mm:ss}</green> | " "<level>{level: <5}</level> | " "<level>{message}</level>"

    def _get_file_format(self) -> str:
        """Get format string for file output."""
        if self.format_type == "structured":
            return "{message}"  # JSON serialization handles structure
        else:
            return "{time:YYYY-MM-DD HH:mm:ss.SSS} | " "{level: <8} | " "{name}:{function}:{line} | " "{message}"

    def _redact_sensitive_data(self, data: Any) -> Any:
        """Redact sensitive data from log messages."""
        if not self.redact_sensitive:
            return data

        if isinstance(data, dict):
            return {
                key: "[REDACTED]" if any(pattern in key.lower() for pattern in self.sensitive_patterns) else self._redact_sensitive_data(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._redact_sensitive_data(item) for item in data]
        elif isinstance(data, str):
            # Simple string redaction for common patterns
            for pattern in self.sensitive_patterns:
                if pattern in data.lower():
                    return "[REDACTED_STRING]"
            return data
        else:
            return data

    def log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None, audit: bool = False):
        """
        Log a message with optional structured data.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            extra: Additional structured data
            audit: Whether this is an audit event
        """
        extra = extra or {}

        # Redact sensitive data
        if self.redact_sensitive:
            extra = self._redact_sensitive_data(extra)

        # Add metadata
        log_data = {"timestamp": datetime.utcnow().isoformat(), "level": level, "message": message, "audit": audit, **extra}

        # Use loguru to log
        logger_method = getattr(logger, level.lower(), logger.info)
        logger_method(json.dumps(log_data) if self.format_type == "structured" else message, extra={"audit": audit, **extra})

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.log("DEBUG", message, kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.log("INFO", message, kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.log("WARNING", message, kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self.log("ERROR", message, kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.log("CRITICAL", message, kwargs)

    def audit(self, message: str, **kwargs):
        """Log audit event."""
        self.log("INFO", message, kwargs, audit=True)

    def log_task_start(self, task_id: str, task_type: str, description: str, **metadata):
        """Log the start of a task."""
        self.audit(f"Task started: {task_type}", task_id=task_id, task_type=task_type, description=description, action="task_start", **metadata)

    def log_task_complete(self, task_id: str, task_type: str, success: bool, **metadata):
        """Log the completion of a task."""
        self.audit(
            f"Task {'completed' if success else 'failed'}: {task_type}",
            task_id=task_id,
            task_type=task_type,
            success=success,
            action="task_complete",
            **metadata,
        )

    def log_tool_call(self, tool_name: str, parameters: Dict[str, Any], result: Any):
        """Log a tool invocation."""
        self.audit(
            f"Tool called: {tool_name}",
            tool_name=tool_name,
            parameters=self._redact_sensitive_data(parameters),
            result_type=type(result).__name__,
            action="tool_call",
        )

    def log_plugin_event(self, plugin_id: str, event: str, **metadata):
        """Log plugin-related events."""
        self.audit(f"Plugin {event}: {plugin_id}", plugin_id=plugin_id, event=event, action="plugin_event", **metadata)

    def log_security_event(self, event_type: str, severity: str, description: str, **metadata):
        """Log security-related events."""
        self.audit(
            f"Security event: {event_type}", event_type=event_type, severity=severity, description=description, action="security_event", **metadata
        )


# Global logger instance
_logger_instance: Optional[FridayLogger] = None


def initialize_logger(config: Dict[str, Any]) -> FridayLogger:
    """Initialize the global logger instance."""
    global _logger_instance
    _logger_instance = FridayLogger(config)
    return _logger_instance


def get_logger() -> FridayLogger:
    """Get the global logger instance."""
    if _logger_instance is None:
        raise RuntimeError("Logger not initialized. Call initialize_logger() first.")
    return _logger_instance


# Convenience functions for common log operations
def debug(message: str, **kwargs):
    """Log debug message."""
    get_logger().debug(message, **kwargs)


def info(message: str, **kwargs):
    """Log info message."""
    get_logger().info(message, **kwargs)


def warning(message: str, **kwargs):
    """Log warning message."""
    get_logger().warning(message, **kwargs)


def error(message: str, **kwargs):
    """Log error message."""
    get_logger().error(message, **kwargs)


def critical(message: str, **kwargs):
    """Log critical message."""
    get_logger().critical(message, **kwargs)


def audit(message: str, **kwargs):
    """Log audit event."""
    get_logger().audit(message, **kwargs)
