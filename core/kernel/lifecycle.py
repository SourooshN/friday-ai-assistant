"""
Friday Lifecycle Manager

Manages the startup, shutdown, and lifecycle events of the Friday system.
"""

import asyncio
import signal
import sys
from typing import Callable, List


class LifecycleManager:
    """
    Manages the lifecycle of Friday AI Assistant components.

    Handles startup, shutdown, and graceful error recovery.
    Provides hooks for components to register lifecycle callbacks.
    """

    def __init__(self):
        self.logger = None  # Will be set after logger initialization
        self._startup_hooks: List[Callable] = []
        self._shutdown_hooks: List[Callable] = []
        self._running = False
        self._shutdown_requested = False

    def set_logger(self, logger):
        """Set the logger instance after it's initialized."""
        self.logger = logger

    def add_startup_hook(self, hook: Callable):
        """
        Add a startup hook to be called during system initialization.

        Args:
            hook: Callable to execute during startup
        """
        self._startup_hooks.append(hook)

    def add_shutdown_hook(self, hook: Callable):
        """
        Add a shutdown hook to be called during system shutdown.

        Args:
            hook: Callable to execute during shutdown
        """
        self._shutdown_hooks.append(hook)

    async def startup(self) -> bool:
        """
        Execute startup sequence.

        Returns:
            True if startup successful, False otherwise
        """
        if self.logger:
            self.logger.info("Friday AI Assistant starting up...")

        try:
            # Execute startup hooks
            for hook in self._startup_hooks:
                if self.logger:
                    self.logger.debug(f"Executing startup hook: {hook.__name__}")

                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()

            self._running = True

            if self.logger:
                self.logger.info("Friday AI Assistant startup complete")
                self.logger.audit("System startup", action="startup", success=True)

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Startup failed: {e}", error=str(e))
                self.logger.audit("System startup failed", action="startup", success=False, error=str(e))
            return False

    async def shutdown(self):
        """Execute shutdown sequence."""
        if self._shutdown_requested:
            return

        self._shutdown_requested = True

        if self.logger:
            self.logger.info("Friday AI Assistant shutting down...")

        try:
            # Execute shutdown hooks in reverse order
            for hook in reversed(self._shutdown_hooks):
                try:
                    if self.logger:
                        self.logger.debug(f"Executing shutdown hook: {hook.__name__}")

                    if asyncio.iscoroutinefunction(hook):
                        await hook()
                    else:
                        hook()

                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Shutdown hook failed: {e}", hook=hook.__name__)

            self._running = False

            if self.logger:
                self.logger.info("Friday AI Assistant shutdown complete")
                self.logger.audit("System shutdown", action="shutdown", success=True)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Shutdown failed: {e}", error=str(e))
                self.logger.audit("System shutdown failed", action="shutdown", success=False, error=str(e))

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            if self.logger:
                self.logger.info(f"Received signal {signum}, initiating shutdown...")

            # Try to get running loop first
            try:
                loop = asyncio.get_running_loop()
                # We're in a running loop, schedule the shutdown using call_soon_threadsafe
                loop.call_soon_threadsafe(lambda: asyncio.create_task(self.shutdown()))
            except RuntimeError:
                # No running loop, use asyncio.run
                asyncio.run(self.shutdown())

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Windows doesn't support SIGHUP
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, signal_handler)

    @property
    def is_running(self) -> bool:
        """Check if the system is currently running."""
        return self._running

    @property
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_requested

    async def wait_for_shutdown(self):
        """Wait for shutdown to be requested."""
        while not self._shutdown_requested:
            await asyncio.sleep(0.1)

    def force_shutdown(self):
        """Force immediate shutdown without running hooks."""
        if self.logger:
            self.logger.warning("Force shutdown requested")
        self._shutdown_requested = True
        self._running = False

        # Try to stop the event loop cooperatively instead of sys.exit
        try:
            loop = asyncio.get_running_loop()
            loop.stop()
        except RuntimeError:
            # No running loop, fall back to sys.exit
            sys.exit(1)
