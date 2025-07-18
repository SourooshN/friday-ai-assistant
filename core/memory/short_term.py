"""
Short-term Memory for Friday AI Assistant
Handles immediate context and working memory
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque, defaultdict
import json
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class MemoryItem:
    """Individual memory item"""
    id: str
    content: Any
    type: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    ttl: Optional[int] = None  # Time to live in seconds
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)


class ShortTermMemory:
    """Short-term memory system for immediate context"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize short-term memory"""
        self.config = config
        self.max_items = config.get('max_items', 100)
        self.default_ttl = config.get('ttl_seconds', 3600)  # 1 hour default
        
        # Memory storage
        self.memory: Dict[str, MemoryItem] = {}
        self.conversation_history: deque = deque(maxlen=50)
        self.context_stack: List[Dict[str, Any]] = []
        
        # Type-specific storage
        self.typed_memory: Dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        
        # Cleanup task
        self.cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("Initialized ShortTermMemory")

    async def start(self):
        """Start memory management tasks"""
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Started memory cleanup task")

    async def stop(self):
        """Stop memory management tasks"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped memory cleanup task")

    async def store(
        self,
        key: str,
        content: Any,
        type: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> str:
        """Store item in short-term memory"""
        
        # Enforce size limit
        if len(self.memory) >= self.max_items:
            await self._evict_oldest()
        
        item = MemoryItem(
            id=key,
            content=content,
            type=type,
            timestamp=datetime.now(),
            metadata=metadata or {},
            ttl=ttl or self.default_ttl
        )
        
        self.memory[key] = item
        
        # Also store in typed memory
        self.typed_memory[type].append(item)
        
        logger.debug(f"Stored memory item: {key} (type: {type})")
        return key

    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve item from memory"""
        item = self.memory.get(key)
        
        if item:
            # Check if expired
            if self._is_expired(item):
                await self.forget(key)
                return None
            
            # Update access info
            item.access_count += 1
            item.last_accessed = datetime.now()
            
            return item.content
        
        return None

    async def search(
        self,
        query: str = None,
        type: str = None,
        limit: int = 10,
        metadata_filter: Dict[str, Any] = None
    ) -> List[MemoryItem]:
        """Search memory with filters"""
        results = []
        
        for item in self.memory.values():
            # Skip expired items
            if self._is_expired(item):
                continue
            
            # Type filter
            if type and item.type != type:
                continue
            
            # Metadata filter
            if metadata_filter:
                if not all(item.metadata.get(k) == v for k, v in metadata_filter.items()):
                    continue
            
            # Query filter (simple substring search)
            if query:
                content_str = str(item.content).lower()
                if query.lower() not in content_str:
                    continue
            
            results.append(item)
        
        # Sort by recency and return limited results
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results[:limit]

    async def forget(self, key: str) -> bool:
        """Remove item from memory"""
        if key in self.memory:
            del self.memory[key]
            logger.debug(f"Forgot memory item: {key}")
            return True
        return False

    async def clear(self, type: Optional[str] = None):
        """Clear memory, optionally by type"""
        if type:
            keys_to_remove = [k for k, v in self.memory.items() if v.type == type]
            for key in keys_to_remove:
                del self.memory[key]
            self.typed_memory[type].clear()
            logger.info(f"Cleared {len(keys_to_remove)} items of type: {type}")
        else:
            count = len(self.memory)
            self.memory.clear()
            self.typed_memory.clear()
            self.conversation_history.clear()
            self.context_stack.clear()
            logger.info(f"Cleared all {count} memory items")

    # Conversation Management
    
    async def add_conversation_turn(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a conversation turn to history"""
        turn = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        self.conversation_history.append(turn)
        
        # Also store in regular memory
        key = f"conv_{datetime.now().timestamp()}"
        await self.store(key, turn, type="conversation", ttl=7200)  # 2 hours

    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        history = list(self.conversation_history)
        if limit:
            history = history[-limit:]
        return history

    # Context Management
    
    async def push_context(self, context: Dict[str, Any]):
        """Push a new context onto the stack"""
        context['timestamp'] = datetime.now()
        self.context_stack.append(context)
        logger.debug(f"Pushed context: {list(context.keys())}")

    async def pop_context(self) -> Optional[Dict[str, Any]]:
        """Pop the most recent context"""
        if self.context_stack:
            context = self.context_stack.pop()
            logger.debug(f"Popped context: {list(context.keys())}")
            return context
        return None

    def get_current_context(self) -> Optional[Dict[str, Any]]:
        """Get current context without removing it"""
        if self.context_stack:
            return self.context_stack[-1]
        return None

    def get_context_stack(self) -> List[Dict[str, Any]]:
        """Get entire context stack"""
        return self.context_stack.copy()

    # Working Memory Operations
    
    async def update_working_memory(self, key: str, update_func):
        """Update an item in working memory using a function"""
        current = await self.retrieve(key)
        if current is not None:
            updated = update_func(current)
            await self.store(key, updated, type="working")
            return updated
        return None

    async def get_recent_items(self, type: str = None, minutes: int = 30) -> List[MemoryItem]:
        """Get items from the last N minutes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        items = []
        for item in self.memory.values():
            if item.timestamp >= cutoff:
                if type is None or item.type == type:
                    items.append(item)
        
        items.sort(key=lambda x: x.timestamp, reverse=True)
        return items

    # Statistics and Management
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        type_counts = defaultdict(int)
        total_size = 0
        
        for item in self.memory.values():
            type_counts[item.type] += 1
            # Estimate size (simplified)
            total_size += len(str(item.content))
        
        return {
            'total_items': len(self.memory),
            'max_items': self.max_items,
            'usage_percent': (len(self.memory) / self.max_items) * 100,
            'type_distribution': dict(type_counts),
            'estimated_size_bytes': total_size,
            'conversation_history_length': len(self.conversation_history),
            'context_stack_depth': len(self.context_stack)
        }

    # Private Methods
    
    def _is_expired(self, item: MemoryItem) -> bool:
        """Check if a memory item has expired"""
        if item.ttl is None:
            return False
        
        age = (datetime.now() - item.timestamp).total_seconds()
        return age > item.ttl

    async def _evict_oldest(self):
        """Evict oldest or least recently used item"""
        if not self.memory:
            return
        
        # Find least recently accessed item
        oldest_key = min(
            self.memory.keys(),
            key=lambda k: self.memory[k].last_accessed
        )
        
        await self.forget(oldest_key)
        logger.debug(f"Evicted oldest item: {oldest_key}")

    async def _cleanup_loop(self):
        """Periodic cleanup of expired items"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                expired_keys = []
                for key, item in self.memory.items():
                    if self._is_expired(item):
                        expired_keys.append(key)
                
                for key in expired_keys:
                    await self.forget(key)
                
                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired items")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    # Serialization
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary for serialization"""
        return {
            'memory': {
                k: {
                    'content': v.content,
                    'type': v.type,
                    'timestamp': v.timestamp.isoformat(),
                    'metadata': v.metadata,
                    'ttl': v.ttl,
                    'access_count': v.access_count
                }
                for k, v in self.memory.items()
            },
            'conversation_history': list(self.conversation_history),
            'context_stack': self.context_stack
        }

    def from_dict(self, data: Dict[str, Any]):
        """Load memory from dictionary"""
        self.memory.clear()
        
        for key, item_data in data.get('memory', {}).items():
            self.memory[key] = MemoryItem(
                id=key,
                content=item_data['content'],
                type=item_data['type'],
                timestamp=datetime.fromisoformat(item_data['timestamp']),
                metadata=item_data.get('metadata', {}),
                ttl=item_data.get('ttl'),
                access_count=item_data.get('access_count', 0)
            )
        
        self.conversation_history = deque(
            data.get('conversation_history', []),
            maxlen=self.conversation_history.maxlen
        )
        self.context_stack = data.get('context_stack', [])