"""
Friday Configuration Manager

Handles loading and management of configuration files for different environments.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigManager:
    """
    Manages configuration loading and access for Friday AI Assistant.

    Supports environment-specific configs (dev, staging, prod) and
    provides a unified interface for accessing configuration values.
    """

    def __init__(self, environment: Optional[str] = None, config_dir: Optional[Path] = None):
        self.environment = environment or os.getenv("FRIDAY_ENV", "dev")
        self.config_dir = config_dir or Path("config")
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """Load configuration from environment-specific YAML file."""
        config_file = self.config_dir / f"{self.environment}.yaml"

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}") from e

        # Validate required configuration sections
        self._validate_config()

    def _validate_config(self):
        """Validate that required configuration sections are present."""
        required_sections = ["environment", "models", "memory", "logging", "plugins", "security"]

        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"Missing required configuration section: {section}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Configuration key in dot notation (e.g., "models.primary")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """
        Set configuration value by dot-notation key.

        Args:
            key: Configuration key in dot notation
            value: Value to set
        """
        keys = key.split(".")
        config = self._config

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set the final value
        config[keys[-1]] = value

    def has(self, key: str) -> bool:
        """
        Check if configuration key exists.

        Args:
            key: Configuration key in dot notation

        Returns:
            True if key exists, False otherwise
        """
        return self.get(key) is not None

    @property
    def environment_name(self) -> str:
        """Get the current environment name."""
        return self.environment

    @property
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get("debug", False)

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "dev"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "prod"

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get("logging", {})

    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration."""
        return self.get("models", {})

    def get_memory_config(self) -> Dict[str, Any]:
        """Get memory configuration."""
        return self.get("memory", {})

    def get_plugin_config(self) -> Dict[str, Any]:
        """Get plugin configuration."""
        return self.get("plugins", {})

    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration."""
        return self.get("security", {})

    def get_feature_flags(self) -> Dict[str, bool]:
        """Get feature flags."""
        return self.get("features", {})

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature flag is enabled."""
        return self.get(f"features.{feature}", False)

    def reload(self):
        """Reload configuration from file."""
        self._load_config()

    def to_dict(self) -> Dict[str, Any]:
        """Get the entire configuration as a dictionary."""
        return self._config.copy()
