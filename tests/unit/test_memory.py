"""
Unit tests for Friday Memory System
"""

import shutil
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from memory.manager import MemoryManager


class TestMemoryManager:
    """Test cases for the memory manager."""

    @pytest.fixture
    def temp_memory_dir(self):
        """Create a temporary memory directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def memory_config(self, temp_memory_dir):
        """Create test memory configuration."""
        return {
            "local": {"sqlite_path": str(temp_memory_dir / "test_memory.db"), "chroma_path": str(temp_memory_dir / "test_chroma")},
            "vector": {"collection_name": "test_collection"},
        }

    @pytest_asyncio.fixture
    async def memory_manager(self, memory_config):
        """Create and initialize a memory manager for testing."""
        manager = MemoryManager(memory_config)
        await manager.initialize()
        yield manager
        await manager.close()

    def test_memory_manager_creation(self, memory_config):
        """Test memory manager can be created."""
        manager = MemoryManager(memory_config)
        assert manager is not None

    @pytest.mark.asyncio
    async def test_memory_manager_initialization(self, memory_config):
        """Test memory manager initialization."""
        manager = MemoryManager(memory_config)
        await manager.initialize()

        status = manager.get_status()
        assert status["sqlite_connected"] is True

        await manager.close()

    @pytest.mark.asyncio
    async def test_store_and_retrieve_memory(self, memory_manager):
        """Test storing and retrieving memories."""
        # Store a memory
        await memory_manager.store_memory("test_memory_1", "This is a test memory", "test", {"tag": "unit_test"})

        # Retrieve the memory
        retrieved = await memory_manager.retrieve_memory("test_memory_1")

        assert retrieved is not None
        assert retrieved["id"] == "test_memory_1"
        assert retrieved["content"] == "This is a test memory"
        assert retrieved["type"] == "test"
        assert retrieved["metadata"]["tag"] == "unit_test"

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_memory(self, memory_manager):
        """Test retrieving a memory that doesn't exist."""
        retrieved = await memory_manager.retrieve_memory("nonexistent")
        assert retrieved is None
