"""
Friday Core Kernel

The main kernel that manages the entire Friday AI Assistant system.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from .config import ConfigManager
from .lifecycle import LifecycleManager
from ..logging import initialize_logger, get_logger
from ..orchestrator import TaskOrchestrator
from ..policy import PolicyEngine
# Defer imports to avoid circular dependencies
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from plugins import PluginHost
    from memory import MemoryManager
    from security import SecretStore


class FridayKernel:
    """
    The core kernel of Friday AI Assistant.

    Responsible for:
    - System initialization and configuration
    - Component lifecycle management
    - Security policy enforcement
    - Resource monitoring and management
    - Plugin and task orchestration
    """

    def __init__(self, environment: Optional[str] = None, config_dir: Optional[Path] = None):
        """
        Initialize the Friday kernel.

        Args:
            environment: Environment name (dev, staging, prod)
            config_dir: Path to configuration directory
        """
        # Core components
        self.config = ConfigManager(environment, config_dir)
        self.lifecycle = LifecycleManager()
        self.logger = None  # Will be initialized after config is loaded

        # System components (initialized during startup)
        self.orchestrator: Optional[TaskOrchestrator] = None
        self.policy_engine: Optional[PolicyEngine] = None
        self.plugin_host: Optional[Any] = None  # PluginHost
        self.memory_manager: Optional[Any] = None  # MemoryManager
        self.secret_store: Optional[Any] = None  # SecretStore

        # State
        self._initialized = False

    async def initialize(self) -> bool:
        """
        Initialize the Friday kernel and all subsystems.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Initialize logging first
            logging_config = self.config.get_logging_config()
            self.logger = initialize_logger(logging_config)
            self.lifecycle.set_logger(self.logger)

            self.logger.info(f"Initializing Friday AI Assistant in {self.config.environment_name} mode")

            # Setup signal handlers for graceful shutdown
            self.lifecycle.setup_signal_handlers()

            # Initialize core components
            await self._initialize_components()

            # Register lifecycle hooks
            self._register_lifecycle_hooks()

            # Start the system
            startup_success = await self.lifecycle.startup()

            if startup_success:
                self._initialized = True
                self.logger.info("Friday kernel initialization complete")
                return True
            else:
                self.logger.error("Friday kernel initialization failed")
                return False

        except Exception as e:
            if self.logger:
                self.logger.error(f"Kernel initialization error: {e}")
            else:
                print(f"Kernel initialization error: {e}")
            return False

    async def _initialize_components(self):
        """Initialize all system components."""
        self.logger.debug("Initializing system components...")

        # Import here to avoid circular imports
        from security import SecretStore
        from memory import MemoryManager
        from plugins import PluginHost

        # Initialize security components first
        self.secret_store = SecretStore(self.config.get_security_config())
        self.policy_engine = PolicyEngine(self.config.get_security_config())

        # Initialize memory management
        memory_config = self.config.get_memory_config()
        self.memory_manager = MemoryManager(memory_config)

        # Initialize plugin host
        plugin_config = self.config.get_plugin_config()
        self.plugin_host = PluginHost(plugin_config, self.policy_engine)

        # Initialize task orchestrator
        self.orchestrator = TaskOrchestrator(
            config=self.config,
            plugin_host=self.plugin_host,
            memory_manager=self.memory_manager,
            policy_engine=self.policy_engine
        )

        self.logger.debug("System components initialized")

    def _register_lifecycle_hooks(self):
        """Register startup and shutdown hooks for all components."""
        # Startup hooks
        if self.memory_manager:
            self.lifecycle.add_startup_hook(self.memory_manager.initialize)

        if self.plugin_host:
            self.lifecycle.add_startup_hook(self.plugin_host.load_enabled_plugins)

        if self.orchestrator:
            self.lifecycle.add_startup_hook(self.orchestrator.start)

        # Shutdown hooks (executed in reverse order)
        if self.orchestrator:
            self.lifecycle.add_shutdown_hook(self.orchestrator.stop)

        if self.plugin_host:
            self.lifecycle.add_shutdown_hook(self.plugin_host.shutdown_all_plugins)

        if self.memory_manager:
            self.lifecycle.add_shutdown_hook(self.memory_manager.close)

        if self.secret_store:
            self.lifecycle.add_shutdown_hook(self.secret_store.clear_all)

    async def run(self):
        """
        Run the Friday system.

        This method blocks until shutdown is requested.
        """
        if not self._initialized:
            success = await self.initialize()
            if not success:
                return

        self.logger.info("Friday AI Assistant is now running")

        try:
            # Wait for shutdown signal
            await self.lifecycle.wait_for_shutdown()
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Shutdown the Friday system gracefully."""
        if self.lifecycle:
            await self.lifecycle.shutdown()

    async def submit_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Submit a task to the orchestrator.

        Args:
            task_description: Natural language description of the task
            context: Additional context for the task

        Returns:
            Task ID for tracking
        """
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")

        return await self.orchestrator.submit_task(task_description, context or {})

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a task.

        Args:
            task_id: Task identifier

        Returns:
            Task status information
        """
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")

        return await self.orchestrator.get_task_status(task_id)

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system status.

        Returns:
            System status information
        """
        status = {
            "initialized": self._initialized,
            "running": self.lifecycle.is_running if self.lifecycle else False,
            "environment": self.config.environment_name,
            "components": {}
        }

        if self.orchestrator:
            status["components"]["orchestrator"] = self.orchestrator.get_status()

        if self.plugin_host:
            status["components"]["plugins"] = self.plugin_host.get_status()

        if self.memory_manager:
            status["components"]["memory"] = self.memory_manager.get_status()

        return status

    @property
    def is_initialized(self) -> bool:
        """Check if the kernel is initialized."""
        return self._initialized

    @property
    def is_running(self) -> bool:
        """Check if the kernel is running."""
        return self.lifecycle.is_running if self.lifecycle else False