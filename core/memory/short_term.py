"""
Short-term memory implementation for Friday AI Assistant.
Provides temporary storage for active conversations and tasks.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json


class ShortTermMemory:
    """Manages short-term memory for active tasks and conversations."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize short-term memory with optional config."""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Use provided config or defaults
        if config is None:
            config = {
                'ttl_minutes': 30,
                'max_items': 1000,
                'cleanup_interval': 300  # 5 minutes
            }
        
        self.config = config
        self.memory_store: Dict[str, Dict[str, Any]] = {}
        self.conversation_history: List[Dict[str, Any]] = []
        self.task_context: Dict[str, Any] = {}
        
        # TTL settings
        self.default_ttl = timedelta(minutes=config.get('ttl_minutes', 30))
        self.max_items = config.get('max_items', 1000)
        
        # Cleanup task
        self.cleanup_interval = config.get('cleanup_interval', 300)
        self.cleanup_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Stats
        self.stats = {
            'stores': 0,
            'retrievals': 0,
            'expirations': 0,
            'created_at': datetime.now()
        }
        
        self.logger.info("Initialized ShortTermMemory")
    
    async def start(self):
        """Start the memory cleanup task."""
        self.is_running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_expired_items())
        self.logger.info("Started memory cleanup task")
    
    async def stop(self):
        """Stop the memory cleanup task."""
        self.is_running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Stopped memory cleanup task")
    
    async def store(self, key: str, value: Any, ttl: Optional[timedelta] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store an item in short-term memory."""
        try:
            ttl = ttl or self.default_ttl
            expiry = datetime.now() + ttl
            
            self.memory_store[key] = {
                'value': value,
                'metadata': metadata or {},
                'created_at': datetime.now(),
                'expires_at': expiry,
                'access_count': 0
            }
            
            self.stats['stores'] += 1
            
            # Enforce max items limit
            if len(self.memory_store) > self.max_items:
                await self._evict_oldest_items()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store item {key}: {str(e)}")
            return False
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve an item from short-term memory."""
        try:
            if key in self.memory_store:
                item = self.memory_store[key]
                
                # Check if expired
                if datetime.now() > item['expires_at']:
                    del self.memory_store[key]
                    self.stats['expirations'] += 1
                    return None
                
                # Update access info
                item['access_count'] += 1
                item['last_accessed'] = datetime.now()
                
                self.stats['retrievals'] += 1
                return item['value']
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve item {key}: {str(e)}")
            return None
    
    async def update(self, key: str, value: Any, extend_ttl: bool = True) -> bool:
        """Update an existing item in memory."""
        if key in self.memory_store:
            item = self.memory_store[key]
            item['value'] = value
            item['modified_at'] = datetime.now()
            
            if extend_ttl:
                item['expires_at'] = datetime.now() + self.default_ttl
            
            return True
        return False
    
    async def delete(self, key: str) -> bool:
        """Delete an item from memory."""
        if key in self.memory_store:
            del self.memory_store[key]
            return True
        return False
    
    async def search(self, query: str, filter_metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """Search for items in memory."""
        matching_keys = []
        
        for key, item in self.memory_store.items():
            # Skip expired items
            if datetime.now() > item['expires_at']:
                continue
            
            # Check metadata filter
            if filter_metadata:
                item_meta = item.get('metadata', {})
                if not all(item_meta.get(k) == v for k, v in filter_metadata.items()):
                    continue
            
            # Simple text search in key and value
            if query.lower() in key.lower():
                matching_keys.append(key)
            elif isinstance(item['value'], str) and query.lower() in item['value'].lower():
                matching_keys.append(key)
            elif isinstance(item['value'], dict):
                # Search in dict values
                value_str = json.dumps(item['value'], default=str).lower()
                if query.lower() in value_str:
                    matching_keys.append(key)
        
        return matching_keys
    
    async def add_to_conversation(self, role: str, content: str, 
                                 metadata: Optional[Dict[str, Any]] = None):
        """Add an entry to conversation history."""
        entry = {
            'role': role,
            'content': content,
            'timestamp': datetime.now(),
            'metadata': metadata or {}
        }
        
        self.conversation_history.append(entry)
        
        # Limit conversation history size
        max_history = 100
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
    
    async def get_conversation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history."""
        return self.conversation_history[-limit:]
    
    async def update_task_context(self, task_id: str, context: Dict[str, Any]):
        """Update context for a specific task."""
        if task_id not in self.task_context:
            self.task_context[task_id] = {
                'created_at': datetime.now(),
                'context': {}
            }
        
        self.task_context[task_id]['context'].update(context)
        self.task_context[task_id]['updated_at'] = datetime.now()
    
    async def get_task_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get context for a specific task."""
        if task_id in self.task_context:
            return self.task_context[task_id]['context']
        return None
    
    async def clear_task_context(self, task_id: str):
        """Clear context for a specific task."""
        if task_id in self.task_context:
            del self.task_context[task_id]
    
    async def _cleanup_expired_items(self):
        """Background task to clean up expired items."""
        while self.is_running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                now = datetime.now()
                expired_keys = []
                
                for key, item in self.memory_store.items():
                    if now > item['expires_at']:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.memory_store[key]
                    self.stats['expirations'] += 1
                
                if expired_keys:
                    self.logger.info(f"Cleaned up {len(expired_keys)} expired items")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {str(e)}")
    
    async def _evict_oldest_items(self):
        """Evict oldest items when memory is full."""
        # Sort by creation time and remove oldest 10%
        items_to_remove = int(self.max_items * 0.1)
        
        sorted_keys = sorted(
            self.memory_store.keys(),
            key=lambda k: self.memory_store[k]['created_at']
        )
        
        for key in sorted_keys[:items_to_remove]:
            del self.memory_store[key]
        
        self.logger.info(f"Evicted {items_to_remove} oldest items from memory")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            'total_items': len(self.memory_store),
            'conversation_history_size': len(self.conversation_history),
            'task_contexts': len(self.task_context),
            'stats': self.stats,
            'size_mb': self._estimate_memory_size()
        }
    
    def _estimate_memory_size(self) -> float:
        """Estimate memory usage in MB."""
        # Rough estimation
        import sys
        
        total_size = 0
        total_size += sys.getsizeof(self.memory_store)
        total_size += sys.getsizeof(self.conversation_history)
        total_size += sys.getsizeof(self.task_context)
        
        # Add size of stored values
        for item in self.memory_store.values():
            total_size += sys.getsizeof(item)
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    async def clear_all(self):
        """Clear all memory."""
        self.memory_store.clear()
        self.conversation_history.clear()
        self.task_context.clear()
        self.logger.info("Cleared all short-term memory")