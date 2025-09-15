"""
Long-term memory implementation for Friday AI Assistant.
Uses ChromaDB for vector storage and SQLite for structured data.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import sqlite3
from pathlib import Path
import uuid

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    chromadb = None


class LongTermMemory:
    """Manages long-term persistent memory using vector and relational databases."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize long-term memory with optional config."""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Use provided config or defaults
        if config is None:
            config = {
                'db_path': 'data/memory/friday.db',
                'chroma_path': 'data/memory/chroma',
                'collection_name': 'friday_memory'
            }
        
        self.config = config
        self.db_path = config.get('db_path', 'data/memory/friday.db')
        self.chroma_path = config.get('chroma_path', 'data/memory/chroma')
        self.collection_name = config.get('collection_name', 'friday_memory')
        
        # Database connections
        self.chroma_client = None
        self.collection = None
        self.sqlite_conn = None
        
        self.logger.info("Initialized LongTermMemory")
    
    async def initialize(self):
        """Initialize database connections."""
        # Initialize ChromaDB
        if HAS_CHROMADB:
            await self._init_vector_db()
        else:
            self.logger.warning("ChromaDB not available - vector search disabled")
        
        # Initialize SQLite
        await self._init_sqlite()
        
        self.logger.info("Long-term memory databases initialized")
    
    async def _init_vector_db(self):
        """Initialize ChromaDB for vector storage."""
        try:
            # Ensure directory exists
            Path(self.chroma_path).mkdir(parents=True, exist_ok=True)
            
            # Create client with settings
            self.chroma_client = chromadb.PersistentClient(
                path=self.chroma_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            try:
                self.collection = self.chroma_client.get_collection(self.collection_name)
            except:
                self.collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Friday AI Assistant Memory"}
                )
            
            self.logger.info(f"ChromaDB initialized with collection: {self.collection_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            self.chroma_client = None
            self.collection = None
    
    async def _init_sqlite(self):
        """Initialize SQLite for structured data."""
        try:
            # Ensure directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Connect to database
            self.sqlite_conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self.sqlite_conn.row_factory = sqlite3.Row
            
            # Create tables
            await self._create_tables()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SQLite: {str(e)}")
            raise
    
    async def _create_tables(self):
        """Create necessary database tables."""
        cursor = self.sqlite_conn.cursor()
        
        # Conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_input TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # Knowledge table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                source TEXT,
                confidence REAL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, key)
            )
        ''')
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                metadata TEXT
            )
        ''')
        
        # User preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.sqlite_conn.commit()
        self.logger.info("SQLite database initialized with tables")
    
    async def store_memory(self, content: str, metadata: Dict[str, Any],
                          memory_type: str = "general") -> str:
        """Store a memory with vector embedding."""
        memory_id = str(uuid.uuid4())
        
        # Store in vector database if available
        if self.collection:
            try:
                self.collection.add(
                    documents=[content],
                    ids=[memory_id],
                    metadatas=[{
                        **metadata,
                        'type': memory_type,
                        'timestamp': datetime.now().isoformat()
                    }]
                )
            except Exception as e:
                self.logger.error(f"Failed to store in vector DB: {str(e)}")
        
        # Also store in SQLite based on type
        if memory_type == "conversation":
            await self._store_conversation(memory_id, content, metadata)
        elif memory_type == "knowledge":
            await self._store_knowledge(content, metadata)
        
        return memory_id
    
    async def search_memories(self, query: str, limit: int = 5,
                            memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search memories using vector similarity."""
        results = []
        
        if self.collection:
            try:
                where_filter = {"type": memory_type} if memory_type else None
                
                search_results = self.collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where=where_filter
                )
                
                # Format results
                if search_results['ids'] and search_results['ids'][0]:
                    for i, id in enumerate(search_results['ids'][0]):
                        results.append({
                            'id': id,
                            'content': search_results['documents'][0][i],
                            'metadata': search_results['metadatas'][0][i],
                            'distance': search_results['distances'][0][i] if 'distances' in search_results else None
                        })
                        
            except Exception as e:
                self.logger.error(f"Vector search failed: {str(e)}")
        
        return results
    
    async def add_interaction(self, user_input: str, assistant_response: Any,
                            metadata: Optional[Dict[str, Any]] = None):
        """Store a conversation interaction."""
        interaction_id = str(uuid.uuid4())
        
        # Convert response to string if it's a dict
        if isinstance(assistant_response, dict):
            response_str = json.dumps(assistant_response, default=str)
        else:
            response_str = str(assistant_response)
        
        # Store in vector DB
        await self.store_memory(
            f"User: {user_input}\nAssistant: {response_str}",
            metadata or {},
            memory_type="conversation"
        )
        
        # Store in SQLite
        cursor = self.sqlite_conn.cursor()
        cursor.execute('''
            INSERT INTO conversations (id, user_input, assistant_response, metadata)
            VALUES (?, ?, ?, ?)
        ''', (interaction_id, user_input, response_str, 
              json.dumps(metadata) if metadata else None))
        
        self.sqlite_conn.commit()
        
        return interaction_id
    
    async def get_recent_interactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation interactions."""
        cursor = self.sqlite_conn.cursor()
        cursor.execute('''
            SELECT * FROM conversations
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        interactions = []
        for row in cursor.fetchall():
            interactions.append({
                'id': row['id'],
                'user_input': row['user_input'],
                'assistant_response': row['assistant_response'],
                'timestamp': row['timestamp'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {}
            })
        
        return interactions
    
    async def store_knowledge(self, category: str, key: str, value: Any,
                            source: Optional[str] = None,
                            confidence: float = 1.0) -> bool:
        """Store a piece of knowledge."""
        try:
            value_str = json.dumps(value) if not isinstance(value, str) else value
            
            cursor = self.sqlite_conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO knowledge 
                (id, category, key, value, source, confidence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (str(uuid.uuid4()), category, key, value_str, source, confidence))
            
            self.sqlite_conn.commit()
            
            # Also store in vector DB for searchability
            await self.store_memory(
                f"{category}: {key} = {value_str}",
                {'category': category, 'key': key, 'source': source},
                memory_type="knowledge"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store knowledge: {str(e)}")
            return False
    
    async def get_knowledge(self, category: str, key: str) -> Optional[Any]:
        """Retrieve a specific piece of knowledge."""
        cursor = self.sqlite_conn.cursor()
        cursor.execute('''
            SELECT value FROM knowledge
            WHERE category = ? AND key = ?
        ''', (category, key))
        
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row['value'])
            except:
                return row['value']
        
        return None
    
    async def search_knowledge(self, category: Optional[str] = None,
                             query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search knowledge base."""
        cursor = self.sqlite_conn.cursor()
        
        if category and not query:
            cursor.execute('''
                SELECT * FROM knowledge
                WHERE category = ?
                ORDER BY updated_at DESC
            ''', (category,))
        elif query and not category:
            cursor.execute('''
                SELECT * FROM knowledge
                WHERE key LIKE ? OR value LIKE ?
                ORDER BY updated_at DESC
            ''', (f'%{query}%', f'%{query}%'))
        elif category and query:
            cursor.execute('''
                SELECT * FROM knowledge
                WHERE category = ? AND (key LIKE ? OR value LIKE ?)
                ORDER BY updated_at DESC
            ''', (category, f'%{query}%', f'%{query}%'))
        else:
            cursor.execute('''
                SELECT * FROM knowledge
                ORDER BY updated_at DESC
                LIMIT 100
            ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'category': row['category'],
                'key': row['key'],
                'value': json.loads(row['value']) if row['value'].startswith('[') or row['value'].startswith('{') else row['value'],
                'source': row['source'],
                'confidence': row['confidence'],
                'updated_at': row['updated_at']
            })
        
        return results
    
    async def store_task_result(self, task_id: str, description: str,
                              status: str, result: Optional[Any] = None,
                              metadata: Optional[Dict[str, Any]] = None):
        """Store task execution result."""
        result_str = json.dumps(result, default=str) if result else None
        
        cursor = self.sqlite_conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO tasks 
            (id, description, status, result, completed_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (task_id, description, status, result_str,
              datetime.now() if status == 'completed' else None,
              json.dumps(metadata) if metadata else None))
        
        self.sqlite_conn.commit()
    
    async def get_task_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent task execution history."""
        cursor = self.sqlite_conn.cursor()
        cursor.execute('''
            SELECT * FROM tasks
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'id': row['id'],
                'description': row['description'],
                'status': row['status'],
                'result': json.loads(row['result']) if row['result'] else None,
                'created_at': row['created_at'],
                'completed_at': row['completed_at'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {}
            })
        
        return tasks
    
    async def set_preference(self, key: str, value: Any) -> bool:
        """Store a user preference."""
        try:
            value_str = json.dumps(value) if not isinstance(value, str) else value
            
            cursor = self.sqlite_conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_preferences (key, value)
                VALUES (?, ?)
            ''', (key, value_str))
            
            self.sqlite_conn.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set preference: {str(e)}")
            return False
    
    async def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        cursor = self.sqlite_conn.cursor()
        cursor.execute('SELECT value FROM user_preferences WHERE key = ?', (key,))
        
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row['value'])
            except:
                return row['value']
        
        return default
    
    async def _store_conversation(self, memory_id: str, content: str,
                                metadata: Dict[str, Any]):
        """Store conversation in SQLite."""
        # Already handled in add_interaction
        pass
    
    async def _store_knowledge(self, content: str, metadata: Dict[str, Any]):
        """Store knowledge in SQLite."""
        # Already handled in store_knowledge
        pass
    
    async def export_memories(self, export_type: str = "all") -> Dict[str, Any]:
        """Export memories for backup or analysis."""
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'type': export_type
        }
        
        if export_type in ['all', 'conversations']:
            export_data['conversations'] = await self.get_recent_interactions(limit=1000)
        
        if export_type in ['all', 'knowledge']:
            export_data['knowledge'] = await self.search_knowledge()
        
        if export_type in ['all', 'tasks']:
            export_data['tasks'] = await self.get_task_history(limit=1000)
        
        return export_data
    
    async def import_memories(self, import_data: Dict[str, Any]) -> bool:
        """Import memories from backup."""
        try:
            # Import conversations
            if 'conversations' in import_data:
                for conv in import_data['conversations']:
                    await self.add_interaction(
                        conv['user_input'],
                        conv['assistant_response'],
                        conv.get('metadata')
                    )
            
            # Import knowledge
            if 'knowledge' in import_data:
                for item in import_data['knowledge']:
                    await self.store_knowledge(
                        item['category'],
                        item['key'],
                        item['value'],
                        item.get('source'),
                        item.get('confidence', 1.0)
                    )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import memories: {str(e)}")
            return False
    
    async def save(self):
        """Save any pending changes."""
        if self.sqlite_conn:
            self.sqlite_conn.commit()
        self.logger.info("Long-term memory saved")
    
    def __del__(self):
        """Cleanup database connections."""
        if self.sqlite_conn:
            self.sqlite_conn.close()
        if self.chroma_client:
            # ChromaDB client doesn't need explicit closing
            pass