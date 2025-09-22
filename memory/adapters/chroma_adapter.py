"""
ChromaDB Memory Adapter

Provides semantic memory capabilities using ChromaDB for vector storage.
"""

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from core.logging import get_logger


class ChromaMemoryAdapter:
    """
    ChromaDB adapter for semantic memory storage and retrieval.

    Provides vector embedding storage, semantic similarity search,
    and document management capabilities.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ChromaDB adapter.

        Args:
            config: Configuration dictionary containing:
                - chroma_path: Path to ChromaDB storage
                - collection_name: Name of the collection
                - embedding_function: Optional custom embedding function
        """
        self.config = config
        self.logger = get_logger()

        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB is not available. Install with: pip install chromadb")

        # Configuration
        self.chroma_path = Path(config.get("chroma_path", "./data/memory/chroma"))
        self.collection_name = config.get("collection_name", "friday_memory")

        # ChromaDB components
        self.client: Optional[chromadb.PersistentClient] = None
        self.collection: Optional[chromadb.Collection] = None

        # Ensure storage directory exists
        self.chroma_path.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> bool:
        """
        Initialize ChromaDB client and collection.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Initializing ChromaDB adapter...")

            # Create ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.chroma_path),
                settings=Settings(
                    anonymized_telemetry=False,  # Disable telemetry for privacy
                    allow_reset=False  # Prevent accidental data loss
                )
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Friday AI Assistant semantic memory"}
            )

            self.logger.info(f"ChromaDB adapter initialized with collection: {self.collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB adapter: {e}")
            return False

    async def store_memory(
        self,
        content: str,
        memory_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store memory content with vector embedding.

        Args:
            content: Text content to store
            memory_id: Optional unique identifier (generates UUID if not provided)
            metadata: Optional metadata dictionary

        Returns:
            Memory ID of stored content

        Raises:
            RuntimeError: If ChromaDB is not initialized
        """
        if not self.collection:
            raise RuntimeError("ChromaDB adapter not initialized")

        # Generate ID if not provided
        if not memory_id:
            memory_id = str(uuid.uuid4())

        # Prepare metadata
        meta = metadata or {}
        meta.update({
            "content_length": len(content),
            "memory_type": "semantic"
        })

        try:
            # Store document in ChromaDB (embedding is generated automatically)
            self.collection.add(
                documents=[content],
                ids=[memory_id],
                metadatas=[meta]
            )

            self.logger.debug(f"Stored semantic memory: {memory_id}")
            return memory_id

        except Exception as e:
            self.logger.error(f"Failed to store memory {memory_id}: {e}")
            raise

    async def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve memory by ID.

        Args:
            memory_id: Unique memory identifier

        Returns:
            Memory data dictionary or None if not found
        """
        if not self.collection:
            raise RuntimeError("ChromaDB adapter not initialized")

        try:
            # Get document by ID
            result = self.collection.get(
                ids=[memory_id],
                include=["documents", "metadatas"]
            )

            if result["ids"] and result["ids"][0] == memory_id:
                return {
                    "id": memory_id,
                    "content": result["documents"][0],
                    "metadata": result["metadatas"][0] if result["metadatas"] else {}
                }

            return None

        except Exception as e:
            self.logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            return None

    async def search_similar(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar memories.

        Args:
            query: Query text for similarity search
            n_results: Maximum number of results to return
            where: Optional metadata filter conditions

        Returns:
            List of similar memory dictionaries with similarity scores
        """
        if not self.collection:
            raise RuntimeError("ChromaDB adapter not initialized")

        try:
            # Perform similarity search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            memories = []
            for i in range(len(results["ids"][0])):
                memories.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "similarity_score": 1.0 - results["distances"][0][i]  # Convert distance to similarity
                })

            self.logger.debug(f"Found {len(memories)} similar memories for query: {query[:50]}...")
            return memories

        except Exception as e:
            self.logger.error(f"Failed to search similar memories: {e}")
            return []

    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update existing memory content or metadata.

        Args:
            memory_id: Memory identifier
            content: New content (if provided)
            metadata: New metadata (if provided)

        Returns:
            True if successful, False otherwise
        """
        if not self.collection:
            raise RuntimeError("ChromaDB adapter not initialized")

        try:
            # Get existing memory
            existing = await self.retrieve_memory(memory_id)
            if not existing:
                self.logger.warning(f"Memory {memory_id} not found for update")
                return False

            # Prepare update data
            update_content = content if content is not None else existing["content"]
            update_metadata = existing["metadata"].copy()
            if metadata:
                update_metadata.update(metadata)

            # Delete existing and re-add with updates
            self.collection.delete(ids=[memory_id])
            self.collection.add(
                documents=[update_content],
                ids=[memory_id],
                metadatas=[update_metadata]
            )

            self.logger.debug(f"Updated semantic memory: {memory_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update memory {memory_id}: {e}")
            return False

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete memory by ID.

        Args:
            memory_id: Memory identifier

        Returns:
            True if successful, False otherwise
        """
        if not self.collection:
            raise RuntimeError("ChromaDB adapter not initialized")

        try:
            self.collection.delete(ids=[memory_id])
            self.logger.debug(f"Deleted semantic memory: {memory_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    async def count_memories(self, where: Optional[Dict[str, Any]] = None) -> int:
        """
        Count total memories in collection.

        Args:
            where: Optional metadata filter conditions

        Returns:
            Total count of memories
        """
        if not self.collection:
            return 0

        try:
            result = self.collection.get(where=where, include=[])
            return len(result["ids"])

        except Exception as e:
            self.logger.error(f"Failed to count memories: {e}")
            return 0

    async def close(self):
        """Close ChromaDB connections."""
        self.logger.info("Closing ChromaDB adapter...")

        # ChromaDB client doesn't need explicit closing
        self.client = None
        self.collection = None

        self.logger.info("ChromaDB adapter closed")

    def get_status(self) -> Dict[str, Any]:
        """
        Get adapter status information.

        Returns:
            Status dictionary
        """
        return {
            "initialized": self.collection is not None,
            "collection_name": self.collection_name,
            "chroma_path": str(self.chroma_path),
            "chromadb_available": CHROMADB_AVAILABLE
        }