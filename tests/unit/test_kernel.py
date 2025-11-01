"""
Unit tests for Friday Kernel
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from core.kernel import FridayKernel


class TestFridayKernel:
    """Test cases for the Friday kernel."""

    @pytest.fixture
    async def temp_config_dir(self):
        """Create a temporary config directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create a minimal test config
        config_content = """
environment: test
debug: true

models:
  primary: test

memory:
  local:
    sqlite_path: ./test_memory.db
    chroma_path: ./test_chroma

logging:
  level: DEBUG
  path: ./test_logs
  console: false
  file: true

plugins:
  enabled: []
  disabled: []

security:
  chain_of_trust: true
  crypto_checks: true
"""

        config_file = temp_dir / "test.yaml"
        with open(config_file, "w") as f:
            f.write(config_content)

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_kernel_initialization(self, temp_config_dir):
        """Test kernel can be created."""
        kernel = FridayKernel(environment="test", config_dir=temp_config_dir)
        assert kernel is not None
        assert not kernel.is_initialized

    @pytest.mark.asyncio
    async def test_kernel_initialize_and_shutdown(self, temp_config_dir):
        """Test kernel initialization and shutdown."""
        kernel = FridayKernel(environment="test", config_dir=temp_config_dir)

        # Initialize
        success = await kernel.initialize()
        assert success
        assert kernel.is_initialized

        # Check system status
        status = kernel.get_system_status()
        assert status["initialized"]
        assert status["environment"] == "test"

        # Shutdown
        await kernel.shutdown()

    @pytest.mark.asyncio
    async def test_task_submission(self, temp_config_dir):
        """Test task submission."""
        kernel = FridayKernel(environment="test", config_dir=temp_config_dir)

        success = await kernel.initialize()
        assert success

        try:
            # Submit a test task
            task_id = await kernel.submit_task("Test task")
            assert task_id is not None

            # Check task status
            status = await kernel.get_task_status(task_id)
            assert "id" in status or "error" not in status

        finally:
            await kernel.shutdown()
