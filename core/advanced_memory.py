#!/usr/bin/env python3
"""
Advanced Memory System for CK-NEXUS
Hierarchical memory with short-term and long-term storage
Based on xMemory and GAM research
"""

import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class MemoryUnit:
    """A single memory unit."""
    id: str
    content: str
    timestamp: float
    memory_type: str  # episodic, semantic, procedural
    importance: float = 0.5
    access_count: int = 0
    last_accessed: float = 0
    metadata: Dict = field(default_factory=dict)


class HierarchicalMemory:
    """
    Hierarchical memory system with short-term and long-term storage.
    
    Architecture (based on GAM):
    - Episodic Buffer: Short-term, recent conversations
    - Topic Network: Long-term, organized by themes
    - Semantic Store: Consolidated knowledge
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".ck-nexus" / "memory.db")
        self.conn = sqlite3.connect(self.db_path)
        self._init_tables()
        
        # In-memory caches
        self.episodic_buffer: List[MemoryUnit] = []
        self.topic_network: Dict[str, List[MemoryUnit]] = defaultdict(list)
        self.semantic_store: Dict[str, MemoryUnit] = {}
        
        # Configuration
        self.buffer_max_size = 100
        self.consolidation_threshold = 0.7
        self._load_from_db()
    
    def _init_tables(self):
        """Initialize database tables."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT,
                timestamp REAL,
                memory_type TEXT,
                importance REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL,
                topic TEXT,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_links (
                source_id TEXT,
                target_id TEXT,
                link_type TEXT,
                strength REAL DEFAULT 1.0,
                FOREIGN KEY (source_id) REFERENCES memories(id),
                FOREIGN KEY (target_id) REFERENCES memories(id)
            )
        ''')
        
        self.conn.commit()
    
    def _load_from_db(self):
        """Load memories from database."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM memories ORDER BY timestamp DESC LIMIT 1000')
        
        for row in cursor.fetchall():
            memory = MemoryUnit(
                id=row[0],
                content=row[1],
                timestamp=row[2],
                memory_type=row[3],
                importance=row[4],
                access_count=row[5],
                last_accessed=row[6],
                metadata=json.loads(row[7]) if row[7] else {}
            )
            
            # Classify into hierarchy
            if time.time() - memory.timestamp < 3600:  # Last hour
                self.episodic_buffer.append(memory)
            else:
                topic = memory.metadata.get('topic', 'general')
                self.topic_network[topic].append(memory)
    
    def store(self, content: str, memory_type: str = "episodic", 
              importance: float = 0.5, metadata: Dict = None) -> MemoryUnit:
        """Store a new memory."""
        memory_id = f"mem_{int(time.time() * 1000)}"
        
        memory = MemoryUnit(
            id=memory_id,
            content=content,
            timestamp=time.time(),
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {}
        )
        
        # Add to episodic buffer
        self.episodic_buffer.append(memory)
        
        # Save to database
        self._save_to_db(memory)
        
        # Consolidate if buffer is full
        if len(self.episodic_buffer) > self.buffer_max_size:
            self._consolidate()
        
        return memory
    
    def retrieve(self, query: str, top_k: int = 5, 
                 memory_type: str = None) -> List[MemoryUnit]:
        """Retrieve relevant memories using hierarchical search."""
        results = []
        
        # Search episodic buffer (short-term)
        for memory in self.episodic_buffer:
            if memory_type and memory.memory_type != memory_type:
                continue
            score = self._score_memory(memory, query)
            if score > 0.3:
                results.append((score, memory))
        
        # Search topic network (medium-term)
        for topic, memories in self.topic_network.items():
            for memory in memories:
                if memory_type and memory.memory_type != memory_type:
                    continue
                score = self._score_memory(memory, query)
                if score > 0.3:
                    results.append((score, memory))
        
        # Search semantic store (long-term)
        for memory in self.semantic_store.values():
            if memory_type and memory.memory_type != memory_type:
                continue
            score = self._score_memory(memory, query)
            if score > 0.3:
                results.append((score, memory))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: -x[0])
        return [memory for _, memory in results[:top_k]]
    
    def _score_memory(self, memory: MemoryUnit, query: str) -> float:
        """Score a memory's relevance to a query."""
        # Simple keyword matching (can be enhanced with embeddings)
        query_words = set(query.lower().split())
        memory_words = set(memory.content.lower().split())
        
        overlap = len(query_words & memory_words)
        base_score = overlap / max(len(query_words), 1)
        
        # Boost by importance and recency
        importance_boost = memory.importance * 0.3
        recency_boost = max(0, 1 - (time.time() - memory.timestamp) / 86400) * 0.2
        access_boost = min(memory.access_count / 10, 0.2)
        
        return base_score + importance_boost + recency_boost + access_boost
    
    def _consolidate(self):
        """Consolidate episodic buffer into topic network."""
        # Sort by importance
        self.episodic_buffer.sort(key=lambda m: -m.importance)
        
        # Move less important memories to topic network
        to_consolidate = self.episodic_buffer[self.buffer_max_size // 2:]
        self.episodic_buffer = self.episodic_buffer[:self.buffer_max_size // 2]
        
        for memory in to_consolidate:
            topic = memory.metadata.get('topic', 'general')
            self.topic_network[topic].append(memory)
        
        # Consolidate old topic memories into semantic store
        for topic, memories in list(self.topic_network.items()):
            old_memories = [m for m in memories 
                          if time.time() - m.timestamp > 86400 * 7]  # Older than 7 days
            
            for memory in old_memories:
                self.semantic_store[memory.id] = memory
                memories.remove(memory)
    
    def _save_to_db(self, memory: MemoryUnit):
        """Save memory to database."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO memories 
            (id, content, timestamp, memory_type, importance, access_count, last_accessed, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            memory.id,
            memory.content,
            memory.timestamp,
            memory.memory_type,
            memory.importance,
            memory.access_count,
            memory.last_accessed,
            json.dumps(memory.metadata)
        ))
        self.conn.commit()
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        return {
            "episodic_buffer": len(self.episodic_buffer),
            "topic_network": sum(len(m) for m in self.topic_network.values()),
            "semantic_store": len(self.semantic_store),
            "topics": list(self.topic_network.keys()),
            "total_memories": len(self.episodic_buffer) + sum(len(m) for m in self.topic_network.values()) + len(self.semantic_store)
        }
    
    def close(self):
        """Close database connection."""
        self.conn.close()


class ConversationMemory:
    """Memory for managing conversation context."""
    
    def __init__(self, memory: HierarchicalMemory = None):
        self.memory = memory or HierarchicalMemory()
        self.conversation_history: List[Dict] = []
        self.context_window: List[MemoryUnit] = []
    
    def add_turn(self, role: str, content: str, metadata: Dict = None):
        """Add a conversation turn."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        })
        
        # Store in memory
        self.memory.store(
            content=content,
            memory_type="episodic",
            importance=0.5 if role == "user" else 0.6,
            metadata={"role": role, **(metadata or {})}
        )
    
    def get_context(self, max_tokens: int = 4000) -> List[Dict]:
        """Get conversation context for LLM."""
        # Get recent turns
        recent = self.conversation_history[-20:]
        
        # Get relevant memories
        if self.conversation_history:
            last_query = self.conversation_history[-1]["content"]
            relevant = self.memory.retrieve(last_query, top_k=5)
            
            # Add as context
            context = []
            if relevant:
                context.append({
                    "role": "system",
                    "content": "Relevant memories:\n" + "\n".join(m.content for m in relevant)
                })
            
            context.extend(recent)
            return context
        
        return recent
    
    def clear(self):
        """Clear conversation history."""
        self.conversation_history = []


# Global instance
_global_memory = None

def get_memory() -> HierarchicalMemory:
    """Get global memory instance."""
    global _global_memory
    if _global_memory is None:
        _global_memory = HierarchicalMemory()
    return _global_memory


if __name__ == "__main__":
    memory = HierarchicalMemory()
    
    print("🧠 Advanced Memory System")
    print("=" * 60)
    
    # Store some memories
    memory.store("User prefers Thai language", importance=0.8, metadata={"topic": "preferences"})
    memory.store("CK-NEXUS uses Groq and OpenRouter", importance=0.7, metadata={"topic": "system"})
    memory.store("User wants autonomous control", importance=0.9, metadata={"topic": "preferences"})
    
    # Retrieve
    results = memory.retrieve("language preference")
    print(f"\n🔍 Retrieved {len(results)} memories:")
    for m in results:
        print(f"   - {m.content[:50]}... (score: {m.importance:.2f})")
    
    # Stats
    print(f"\n📊 Stats: {memory.get_stats()}")
    
    memory.close()
