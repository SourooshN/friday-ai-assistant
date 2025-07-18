"""
Long-term Memory for Friday AI Assistant
Handles persistent memory with vector storage
"""

import asyncio
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import chromadb
from chromadb.config import Settings
from loguru import logger
import hashlib

from scripts.utils.helpers import ensure_directory, PROJECT_ROOT


class LongTermMemory:
    """Long-term persistent memory with vector search"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize long-term memory"""
        self.config = config
        
        # Vector database config
        self.vector_config = config.get('vector_db', {})
        self.vector_path = Path(self.vector_config.get('path', './data/memory/vectors'))
        self.collection_name = self.vector_config.get('collection_name', 'friday_memory')
        
        # SQLite config for structured data
        self.sqlite_config = config.get('long_term', {})
        self.db_path = Path(self.sqlite_config.get('path', './data/memory/long_term.db'))
        
        # Ensure directories exist
        ensure_directory(self.vector_path.parent)
        ensure_directory(self.db_path.parent)
        
        # Initialize databases
        self.chroma_client = None
        self.collection = None
        self.sqlite_conn = None
        
        logger.info("Initialized LongTermMemory")

    async def initialize(self):
        """Initialize database connections"""
        await self._init_vector_db()
        await self._init_sqlite()
        logger.info("Long-term memory databases initialized")

    async def _init_vector_db(self):
        """Initialize ChromaDB for vector storage"""
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.vector_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Friday's long-term memory"}
            )
            
            logger.info(f"ChromaDB initialized with collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    async def _init_sqlite(self):
        """Initialize SQLite for structured data"""
        try:
            self.sqlite_conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self.sqlite_conn.row_factory = sqlite3.Row
            
            # Create tables
            cursor = self.sqlite_conn.cursor()
            
            # Memory metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_metadata (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT,
                    importance REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # Agent history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    task_id TEXT,
                    task_type TEXT,
                    success BOOLEAN,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    duration REAL,
                    result TEXT,
                    metadata TEXT
                )
            """)
            
            # Knowledge facts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    source TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    UNIQUE(subject, predicate, object)
                )
            """)
            
            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.sqlite_conn.commit()
            logger.info("SQLite database initialized with tables")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite: {e}")
            raise

    async def store(
        self,
        content: str,
        type: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> str:
        """Store content in long-term memory"""
        
        # Generate ID
        memory_id = self._generate_id(content)
        
        try:
            # Store in vector database
            self.collection.add(
                documents=[content],
                ids=[memory_id],
                metadatas=[{
                    "type": type,
                    "timestamp": datetime.now().isoformat(),
                    "importance": importance,
                    **(metadata or {})
                }]
            )
            
            # Store metadata in SQLite
            cursor = self.sqlite_conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO memory_metadata 
                (id, type, timestamp, importance, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                memory_id,
                type,
                datetime.now(),
                importance,
                json.dumps(metadata or {})
            ))
            self.sqlite_conn.commit()
            
            logger.debug(f"Stored long-term memory: {memory_id} (type: {type})")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to store in long-term memory: {e}")
            raise

    async def search(
        self,
        query: str,
        type: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search long-term memory using vector similarity"""
        
        try:
            # Build query filter
            where = {"type": type} if type else None
            
            # Search vector database
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=where
            )
            
            if not results['ids'][0]:
                return []
            
            # Get additional metadata from SQLite
            memory_items = []
            cursor = self.sqlite_conn.cursor()
            
            for i, memory_id in enumerate(results['ids'][0]):
                # Skip if similarity is below threshold
                distance = results['distances'][0][i]
                similarity = 1 - distance  # Convert distance to similarity
                
                if similarity < threshold:
                    continue
                
                # Get metadata from SQLite
                cursor.execute(
                    "SELECT * FROM memory_metadata WHERE id = ?",
                    (memory_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    memory_items.append({
                        'id': memory_id,
                        'content': results['documents'][0][i],
                        'type': row['type'],
                        'timestamp': row['timestamp'],
                        'importance': row['importance'],
                        'similarity': similarity,
                        'metadata': json.loads(row['metadata'] or '{}')
                    })
                    
                    # Update access count
                    cursor.execute("""
                        UPDATE memory_metadata 
                        SET access_count = access_count + 1,
                            last_accessed = ?
                        WHERE id = ?
                    """, (datetime.now(), memory_id))
            
            self.sqlite_conn.commit()
            
            return memory_items
            
        except Exception as e:
            logger.error(f"Failed to search long-term memory: {e}")
            return []

    async def retrieve(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve specific memory by ID"""
        
        try:
            # Get from vector database
            result = self.collection.get(ids=[memory_id])
            
            if not result['ids']:
                return None
            
            # Get metadata from SQLite
            cursor = self.sqlite_conn.cursor()
            cursor.execute(
                "SELECT * FROM memory_metadata WHERE id = ?",
                (memory_id,)
            )
            row = cursor.fetchone()
            
            if row:
                # Update access count
                cursor.execute("""
                    UPDATE memory_metadata 
                    SET access_count = access_count + 1,
                        last_accessed = ?
                    WHERE id = ?
                """, (datetime.now(), memory_id))
                self.sqlite_conn.commit()
                
                return {
                    'id': memory_id,
                    'content': result['documents'][0],
                    'type': row['type'],
                    'timestamp': row['timestamp'],
                    'importance': row['importance'],
                    'access_count': row['access_count'],
                    'metadata': json.loads(row['metadata'] or '{}')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            return None

    async def forget(self, memory_id: str) -> bool:
        """Remove memory by ID"""
        
        try:
            # Remove from vector database
            self.collection.delete(ids=[memory_id])
            
            # Remove from SQLite
            cursor = self.sqlite_conn.cursor()
            cursor.execute("DELETE FROM memory_metadata WHERE id = ?", (memory_id,))
            self.sqlite_conn.commit()
            
            logger.debug(f"Forgot memory: {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to forget memory {memory_id}: {e}")
            return False

    # Knowledge Management
    
    async def add_fact(
        self,
        subject: str,
        predicate: str,
        object: str,
        confidence: float = 1.0,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a knowledge fact (triple)"""
        
        try:
            cursor = self.sqlite_conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO knowledge_facts
                (subject, predicate, object, confidence, source, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                subject,
                predicate,
                object,
                confidence,
                source,
                json.dumps(metadata or {})
            ))
            self.sqlite_conn.commit()
            
            # Also store as searchable memory
            fact_text = f"{subject} {predicate} {object}"
            await self.store(
                fact_text,
                type="fact",
                metadata={
                    "subject": subject,
                    "predicate": predicate,
                    "object": object,
                    "confidence": confidence
                },
                importance=confidence
            )
            
            logger.debug(f"Added fact: {fact_text}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add fact: {e}")
            return False

    async def query_facts(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query knowledge facts"""
        
        cursor = self.sqlite_conn.cursor()
        
        # Build query
        conditions = []
        params = []
        
        if subject:
            conditions.append("subject = ?")
            params.append(subject)
        if predicate:
            conditions.append("predicate = ?")
            params.append(predicate)
        if object:
            conditions.append("object = ?")
            params.append(object)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        cursor.execute(f"""
            SELECT * FROM knowledge_facts 
            WHERE {where_clause}
            ORDER BY confidence DESC, timestamp DESC
        """, params)
        
        facts = []
        for row in cursor.fetchall():
            facts.append({
                'subject': row['subject'],
                'predicate': row['predicate'],
                'object': row['object'],
                'confidence': row['confidence'],
                'source': row['source'],
                'timestamp': row['timestamp'],
                'metadata': json.loads(row['metadata'] or '{}')
            })
        
        return facts

    # User Preferences
    
    async def set_preference(self, key: str, value: Any, category: Optional[str] = None):
        """Set a user preference"""
        
        cursor = self.sqlite_conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_preferences
            (key, value, category, timestamp)
            VALUES (?, ?, ?, ?)
        """, (key, json.dumps(value), category, datetime.now()))
        self.sqlite_conn.commit()
        
        logger.debug(f"Set preference: {key} = {value}")

    async def get_preference(self, key: str) -> Optional[Any]:
        """Get a user preference"""
        
        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            "SELECT value FROM user_preferences WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        
        if row:
            return json.loads(row['value'])
        return None

    # Agent History
    
    async def log_agent_task(
        self,
        agent_name: str,
        task_id: str,
        task_type: str,
        success: bool,
        duration: float,
        result: Any,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log agent task execution"""
        
        cursor = self.sqlite_conn.cursor()
        cursor.execute("""
            INSERT INTO agent_history
            (agent_name, task_id, task_type, success, duration, result, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_name,
            task_id,
            task_type,
            success,
            duration,
            json.dumps(result),
            json.dumps(metadata or {})
        ))
        self.sqlite_conn.commit()

    # Maintenance
    
    async def cleanup(self, days_to_keep: int = 30):
        """Clean up old memories"""
        
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        
        # Get old memories
        cursor = self.sqlite_conn.cursor()
        cursor.execute("""
            SELECT id FROM memory_metadata
            WHERE timestamp < ? AND importance < 0.8
        """, (cutoff_date,))
        
        old_memories = cursor.fetchall()
        
        for row in old_memories:
            await self.forget(row['id'])
        
        logger.info(f"Cleaned up {len(old_memories)} old memories")

    async def optimize(self):
        """Optimize databases"""
        
        # Optimize SQLite
        self.sqlite_conn.execute("VACUUM")
        self.sqlite_conn.execute("ANALYZE")
        
        logger.info("Optimized long-term memory databases")

    # Statistics
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        
        cursor = self.sqlite_conn.cursor()
        
        # Memory count by type
        cursor.execute("""
            SELECT type, COUNT(*) as count 
            FROM memory_metadata 
            GROUP BY type
        """)
        type_counts = {row['type']: row['count'] for row in cursor.fetchall()}
        
        # Total memories
        cursor.execute("SELECT COUNT(*) as total FROM memory_metadata")
        total_memories = cursor.fetchone()['total']
        
        # Knowledge facts
        cursor.execute("SELECT COUNT(*) as total FROM knowledge_facts")
        total_facts = cursor.fetchone()['total']
        
        # Agent history
        cursor.execute("""
            SELECT agent_name, COUNT(*) as count, 
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes
            FROM agent_history 
            GROUP BY agent_name
        """)
        agent_stats = {
            row['agent_name']: {
                'total': row['count'],
                'successes': row['successes']
            }
            for row in cursor.fetchall()
        }
        
        return {
            'total_memories': total_memories,
            'memory_types': type_counts,
            'total_facts': total_facts,
            'agent_statistics': agent_stats,
            'database_size': self.db_path.stat().st_size if self.db_path.exists() else 0
        }

    # Serialization
    
    async def save(self):
        """Save/checkpoint the database"""
        
        # SQLite auto-saves, but we can force a checkpoint
        self.sqlite_conn.commit()
        
        # ChromaDB persists automatically
        logger.info("Long-term memory saved")

    async def load(self):
        """Load memory from disk"""
        
        # Databases are already persistent, just ensure they're initialized
        if not self.chroma_client:
            await self.initialize()

    # Private methods
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID for content"""
        
        timestamp = str(datetime.now().timestamp())
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"mem_{timestamp}_{content_hash}"

    async def close(self):
        """Close database connections"""
        
        if self.sqlite_conn:
            self.sqlite_conn.close()
        
        logger.info("Long-term memory connections closed")