"""
Friday Memory Manager

Manages memory adapters including ChromaDB and SQLite.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from core.logging import get_logger
from .adapters import ChromaMemoryAdapter


class MemoryManager:
    """
    Manages memory storage using ChromaDB for vectors and SQLite for relational data.

    This is a skeleton implementation for Milestone 1.
    """

    def __init__(self, memory_config: Dict[str, Any]):
        self.config = memory_config
        self.logger = get_logger()

        # Database connections
        self.sqlite_conn: Optional[sqlite3.Connection] = None
        self.chroma_adapter: Optional[ChromaMemoryAdapter] = None

        # Configuration
        self.sqlite_path = Path(memory_config.get("local", {}).get("sqlite_path", "./data/memory/friday.db"))

        # Vector memory configuration
        vector_config = memory_config.get("vector", {})
        self.chroma_config = {
            "chroma_path": vector_config.get("chroma_path", "./data/memory/chroma"),
            "collection_name": vector_config.get("collection_name", "friday_memory")
        }

    async def initialize(self):
        """Initialize memory storage."""
        self.logger.info("Initializing memory manager...")

        # Ensure directories exist
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize SQLite
        await self._init_sqlite()

        # Initialize ChromaDB adapter if available
        if CHROMADB_AVAILABLE:
            await self._init_chroma_adapter()
        else:
            self.logger.warning("ChromaDB not available, vector storage disabled")

        self.logger.info("Memory manager initialized")

    async def _init_sqlite(self):
        """Initialize SQLite database."""
        try:
            self.sqlite_conn = sqlite3.connect(str(self.sqlite_path))
            self.sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_items (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.sqlite_conn.commit()
            self.logger.debug("SQLite database initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize SQLite: {e}")
            raise

    async def _init_chroma_adapter(self):
        """Initialize ChromaDB adapter."""
        try:
            self.chroma_adapter = ChromaMemoryAdapter(self.chroma_config)
            success = await self.chroma_adapter.initialize()
            if success:
                self.logger.debug("ChromaDB adapter initialized")
            else:
                self.logger.warning("ChromaDB adapter initialization failed")
                self.chroma_adapter = None

        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB adapter: {e}")
            self.chroma_adapter = None

    async def store_memory(self, memory_id: str, content: str, memory_type: str = "general", metadata: Dict[str, Any] = None):
        """
        Store a memory item.

        Args:
            memory_id: Unique identifier for the memory
            content: Memory content
            memory_type: Type of memory
            metadata: Additional metadata
        """
        if not self.sqlite_conn:
            self.logger.error("SQLite not initialized")
            return

        try:
            import json
            metadata_json = json.dumps(metadata or {})

            self.sqlite_conn.execute("""
                INSERT OR REPLACE INTO memory_items (id, type, content, metadata)
                VALUES (?, ?, ?, ?)
            """, (memory_id, memory_type, content, metadata_json))
            self.sqlite_conn.commit()

            self.logger.debug(f"Stored memory: {memory_id}")

        except Exception as e:
            self.logger.error(f"Failed to store memory {memory_id}: {e}")

    async def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a memory item by ID.

        Args:
            memory_id: Memory identifier

        Returns:
            Memory item or None if not found
        """
        if not self.sqlite_conn:
            return None

        try:
            cursor = self.sqlite_conn.execute("""
                SELECT id, type, content, metadata, created_at, updated_at
                FROM memory_items WHERE id = ?
            """, (memory_id,))

            row = cursor.fetchone()
            if row:
                import json
                return {
                    "id": row[0],
                    "type": row[1],
                    "content": row[2],
                    "metadata": json.loads(row[3]) if row[3] else {},
                    "created_at": row[4],
                    "updated_at": row[5]
                }

            return None

        except Exception as e:
            self.logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            return None

    async def store_semantic_memory(self, content: str, memory_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Store memory with semantic search capabilities.

        Args:
            content: Text content to store
            memory_id: Optional unique identifier
            metadata: Optional metadata

        Returns:
            Memory ID if successful, None otherwise
        """
        if not self.chroma_adapter:
            self.logger.warning("ChromaDB adapter not available for semantic memory storage")
            return None

        try:
            return await self.chroma_adapter.store_memory(content, memory_id, metadata)
        except Exception as e:
            self.logger.error(f"Failed to store semantic memory: {e}")
            return None

    async def search_similar_memories(self, query: str, n_results: int = 5, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for semantically similar memories.

        Args:
            query: Query text for similarity search
            n_results: Maximum number of results
            where: Optional metadata filter

        Returns:
            List of similar memories with scores
        """
        if not self.chroma_adapter:
            self.logger.warning("ChromaDB adapter not available for semantic search")
            return []

        try:
            return await self.chroma_adapter.search_similar(query, n_results, where)
        except Exception as e:
            self.logger.error(f"Failed to search similar memories: {e}")
            return []

    async def get_semantic_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve semantic memory by ID.

        Args:
            memory_id: Memory identifier

        Returns:
            Memory data or None if not found
        """
        if not self.chroma_adapter:
            return None

        try:
            return await self.chroma_adapter.retrieve_memory(memory_id)
        except Exception as e:
            self.logger.error(f"Failed to retrieve semantic memory {memory_id}: {e}")
            return None

    async def update_semantic_memory(self, memory_id: str, content: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update semantic memory content or metadata.

        Args:
            memory_id: Memory identifier
            content: New content (optional)
            metadata: New metadata (optional)

        Returns:
            True if successful, False otherwise
        """
        if not self.chroma_adapter:
            return False

        try:
            return await self.chroma_adapter.update_memory(memory_id, content, metadata)
        except Exception as e:
            self.logger.error(f"Failed to update semantic memory {memory_id}: {e}")
            return False

    async def delete_semantic_memory(self, memory_id: str) -> bool:
        """
        Delete semantic memory by ID.

        Args:
            memory_id: Memory identifier

        Returns:
            True if successful, False otherwise
        """
        if not self.chroma_adapter:
            return False

        try:
            return await self.chroma_adapter.delete_memory(memory_id)
        except Exception as e:
            self.logger.error(f"Failed to delete semantic memory {memory_id}: {e}")
            return False

    async def count_semantic_memories(self, where: Optional[Dict[str, Any]] = None) -> int:
        """
        Count semantic memories.

        Args:
            where: Optional metadata filter

        Returns:
            Count of semantic memories
        """
        if not self.chroma_adapter:
            return 0

        try:
            return await self.chroma_adapter.count_memories(where)
        except Exception as e:
            self.logger.error(f"Failed to count semantic memories: {e}")
            return 0

    async def close(self):
        """Close memory connections."""
        self.logger.info("Closing memory manager...")

        if self.sqlite_conn:
            self.sqlite_conn.close()
            self.sqlite_conn = None

        if self.chroma_adapter:
            await self.chroma_adapter.close()
            self.chroma_adapter = None

        self.logger.info("Memory manager closed")

    def get_status(self) -> Dict[str, Any]:
        """Get memory manager status."""
        status = {
            "sqlite_connected": self.sqlite_conn is not None,
            "chromadb_available": CHROMADB_AVAILABLE,
            "chroma_adapter_connected": self.chroma_adapter is not None,
            "sqlite_path": str(self.sqlite_path)
        }

        # Add ChromaDB adapter status if available
        if self.chroma_adapter:
            status.update(self.chroma_adapter.get_status())

        return status