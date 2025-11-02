"""
Unit tests for ChromaDB integration in Friday AI Assistant
"""

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from core.logging import initialize_logger
from memory.adapters.chroma_adapter import CHROMADB_AVAILABLE, ChromaMemoryAdapter
from memory.manager import MemoryManager


@pytest_asyncio.fixture
async def temp_chroma_config():
    """Create temporary ChromaDB configuration for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    config = {"chroma_path": str(temp_dir / "chroma_test"), "collection_name": "friday_test_collection"}
    yield config
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest_asyncio.fixture
async def chroma_adapter(temp_chroma_config):
    """Create and initialize ChromaMemoryAdapter for testing."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")

    # Initialize basic logging for tests
    logger_config = {"level": "DEBUG", "log_to_console": False, "log_to_file": False, "format": "simple"}
    initialize_logger(logger_config)

    adapter = ChromaMemoryAdapter(temp_chroma_config)
    success = await adapter.initialize()
    if not success:
        pytest.skip("Failed to initialize ChromaDB adapter")

    yield adapter
    await adapter.close()


@pytest_asyncio.fixture
async def memory_manager(temp_chroma_config):
    """Create MemoryManager with test configuration."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")

    # Initialize basic logging for tests
    logger_config = {"level": "DEBUG", "log_to_console": False, "log_to_file": False, "format": "simple"}
    initialize_logger(logger_config)

    # Create test memory configuration
    memory_config = {"local": {"sqlite_path": str(temp_chroma_config["chroma_path"]) + "/test.db"}, "vector": temp_chroma_config}

    manager = MemoryManager(memory_config)
    await manager.initialize()

    yield manager
    await manager.close()


class TestChromaMemoryAdapter:
    """Test ChromaMemoryAdapter functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, temp_chroma_config):
        """Test adapter initialization."""
        if not CHROMADB_AVAILABLE:
            pytest.skip("ChromaDB not available")

        # Initialize basic logging for tests
        logger_config = {"level": "DEBUG", "log_to_console": False, "log_to_file": False, "format": "simple"}
        initialize_logger(logger_config)

        adapter = ChromaMemoryAdapter(temp_chroma_config)
        success = await adapter.initialize()

        assert success is True
        assert adapter.collection is not None
        assert adapter.client is not None

        await adapter.close()

    @pytest.mark.asyncio
    async def test_store_and_retrieve_memory(self, chroma_adapter):
        """Test storing and retrieving memories."""
        # Store a memory
        content = "This is a test memory about artificial intelligence."
        memory_id = await chroma_adapter.store_memory(content)

        assert memory_id is not None

        # Retrieve the memory
        retrieved = await chroma_adapter.retrieve_memory(memory_id)

        assert retrieved is not None
        assert retrieved["id"] == memory_id
        assert retrieved["content"] == content
        assert "metadata" in retrieved

    @pytest.mark.asyncio
    async def test_store_memory_with_metadata(self, chroma_adapter):
        """Test storing memory with metadata."""
        content = "Test memory with metadata"
        # ChromaDB only accepts str, int, float, bool in metadata - not lists
        metadata = {"category": "test", "importance": "high", "tags": "testing,memory"}

        memory_id = await chroma_adapter.store_memory(content, metadata=metadata)
        retrieved = await chroma_adapter.retrieve_memory(memory_id)

        assert retrieved["metadata"]["category"] == "test"
        assert retrieved["metadata"]["importance"] == "high"
        assert retrieved["metadata"]["content_length"] == len(content)

    @pytest.mark.asyncio
    async def test_search_similar_memories(self, chroma_adapter):
        """Test semantic similarity search."""
        # Store multiple related memories
        memories = [
            "I love programming in Python",
            "Python is a great programming language",
            "Machine learning with artificial intelligence",
            "Cats are wonderful pets",
            "Dogs make great companions",
        ]

        memory_ids = []
        for content in memories:
            memory_id = await chroma_adapter.store_memory(content)
            memory_ids.append(memory_id)

        # Search for programming-related content
        results = await chroma_adapter.search_similar("Python programming", n_results=3)

        assert len(results) <= 3
        assert len(results) >= 2  # Should find the Python-related memories

        # Check that results contain similarity scores
        for result in results:
            assert "similarity_score" in result
            assert 0 <= result["similarity_score"] <= 1
            assert "content" in result
            assert "id" in result

    @pytest.mark.asyncio
    async def test_update_memory(self, chroma_adapter):
        """Test updating memory content and metadata."""
        # Store initial memory
        original_content = "Original content"
        memory_id = await chroma_adapter.store_memory(original_content)

        # Update content
        new_content = "Updated content with new information"
        success = await chroma_adapter.update_memory(memory_id, content=new_content)

        assert success is True

        # Verify update
        retrieved = await chroma_adapter.retrieve_memory(memory_id)
        assert retrieved["content"] == new_content

        # Update metadata only
        new_metadata = {"updated": True, "version": 2}
        success = await chroma_adapter.update_memory(memory_id, metadata=new_metadata)

        assert success is True

        retrieved = await chroma_adapter.retrieve_memory(memory_id)
        assert retrieved["metadata"]["updated"] is True
        assert retrieved["metadata"]["version"] == 2

    @pytest.mark.asyncio
    async def test_delete_memory(self, chroma_adapter):
        """Test deleting memories."""
        # Store a memory
        content = "Memory to be deleted"
        memory_id = await chroma_adapter.store_memory(content)

        # Verify it exists
        retrieved = await chroma_adapter.retrieve_memory(memory_id)
        assert retrieved is not None

        # Delete it
        success = await chroma_adapter.delete_memory(memory_id)
        assert success is True

        # Verify it's gone
        retrieved = await chroma_adapter.retrieve_memory(memory_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_count_memories(self, chroma_adapter):
        """Test counting memories."""
        initial_count = await chroma_adapter.count_memories()

        # Add some memories
        for i in range(3):
            await chroma_adapter.store_memory(f"Test memory {i}")

        final_count = await chroma_adapter.count_memories()
        assert final_count == initial_count + 3

    @pytest.mark.asyncio
    async def test_status(self, chroma_adapter):
        """Test adapter status reporting."""
        status = chroma_adapter.get_status()

        assert status["initialized"] is True
        assert status["collection_name"] == "friday_test_collection"
        assert status["chromadb_available"] is True
        assert "chroma_path" in status


class TestMemoryManagerIntegration:
    """Test MemoryManager integration with ChromaMemoryAdapter."""

    @pytest.mark.asyncio
    async def test_semantic_memory_operations(self, memory_manager):
        """Test semantic memory operations through MemoryManager."""
        # Store semantic memory
        content = "Friday AI Assistant semantic memory test"
        memory_id = await memory_manager.store_semantic_memory(content)

        assert memory_id is not None

        # Retrieve semantic memory
        retrieved = await memory_manager.get_semantic_memory(memory_id)
        assert retrieved is not None
        assert retrieved["content"] == content

        # Search similar memories
        results = await memory_manager.search_similar_memories("Friday AI test", n_results=1)
        assert len(results) >= 1
        assert any(memory_id in result["id"] for result in results)

    @pytest.mark.asyncio
    async def test_memory_manager_status(self, memory_manager):
        """Test MemoryManager status with ChromaDB."""
        status = memory_manager.get_status()

        assert status["sqlite_connected"] is True
        assert status["chromadb_available"] is True
        assert status["chroma_adapter_connected"] is True
        assert status["initialized"] is True

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, memory_manager):
        """Test concurrent memory operations."""
        # Store multiple memories concurrently
        contents = ["Concurrent memory test 1", "Concurrent memory test 2", "Concurrent memory test 3"]

        tasks = [memory_manager.store_semantic_memory(content) for content in contents]

        memory_ids = await asyncio.gather(*tasks)

        # Verify all memories were stored
        assert len(memory_ids) == 3
        assert all(id is not None for id in memory_ids)

        # Retrieve all memories concurrently
        retrieve_tasks = [memory_manager.get_semantic_memory(memory_id) for memory_id in memory_ids]

        memories = await asyncio.gather(*retrieve_tasks)

        # Verify all memories were retrieved
        assert len(memories) == 3
        assert all(memory is not None for memory in memories)

        stored_contents = [memory["content"] for memory in memories]
        assert set(stored_contents) == set(contents)


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_memory(self, chroma_adapter):
        """Test retrieving non-existent memory."""
        result = await chroma_adapter.retrieve_memory("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_nonexistent_memory(self, chroma_adapter):
        """Test updating non-existent memory."""
        success = await chroma_adapter.update_memory("nonexistent-id", "new content")
        assert success is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_memory(self, chroma_adapter):
        """Test deleting non-existent memory."""
        # Should not raise an error, just return True
        success = await chroma_adapter.delete_memory("nonexistent-id")
        assert success is True

    @pytest.mark.asyncio
    async def test_operations_without_initialization(self, temp_chroma_config):
        """Test operations on uninitialized adapter."""
        if not CHROMADB_AVAILABLE:
            pytest.skip("ChromaDB not available")

        # Initialize basic logging for tests
        logger_config = {"level": "DEBUG", "log_to_console": False, "log_to_file": False, "format": "simple"}
        initialize_logger(logger_config)

        adapter = ChromaMemoryAdapter(temp_chroma_config)
        # Don't initialize

        with pytest.raises(RuntimeError, match="ChromaDB adapter not initialized"):
            await adapter.store_memory("test content")


# Skip all tests if ChromaDB is not available
pytestmark = pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="ChromaDB not available")
