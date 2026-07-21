# CK-NEXUS AIOS — Improvement Plan

## Critical Issues to Fix

### 1. Security (2 Critical)

**1.1 Weak Password Hashing**
- File: `kernel/security.py:109-115`
- Issue: Uses raw SHA-256 instead of bcrypt/argon2
- Fix: Replace with `bcrypt` or `argon2`

**1.2 Token TTL Never Enforced**
- File: `kernel/security.py:85-88`
- Issue: `create_token()` accepts `ttl` parameter but never uses it
- Fix: Store creation time and check expiry on authenticate

### 2. Architecture (3 High)

**2.1 God Object: OrchestratorEngine**
- File: `kernel/orchestrator.py`
- Issue: Owns 10 components, violates SRP
- Fix: Extract MemoryHandler, KnowledgeHandler, VideoHandler

**2.2 No Abstract Interfaces for Video**
- File: `kernel/video/analyzer.py`
- Issue: No ABCs for frame_extractor/transcriber
- Fix: Create BaseFrameExtractor, BaseTranscriber ABCs

**2.3 Schema Validation Not Enforced**
- File: `knowledge/schema.py`
- Issue: Validators exist but never called
- Fix: Call `validate_entity()` in KnowledgePipeline

### 3. Performance (2 High)

**3.1 BFS Uses O(n) List.pop(0)**
- File: `kernel/memory/knowledge_graph.py:167-182`
- Issue: Uses `queue.pop(0)` instead of `deque.popleft()`
- Fix: Use `collections.deque`

**3.2 Unbounded In-Memory Growth**
- File: `kernel/orchestrator.py:37`
- Issue: `_watch_results` dict never evicted
- Fix: Add LRU cache with max size

### 4. Test Coverage (2 High)

**4.1 No Knowledge Pipeline Tests**
- Missing: `tests/unit/test_knowledge_pipeline.py`
- Coverage: 0% for KnowledgePipeline class

**4.2 No Orchestrator Event Handler Tests**
- Missing: Tests for `_on_kg_add_entity`, `_on_video_watch`, etc.
- Coverage: 0% for event handlers

---

## Medium Priority Fixes

| Issue | File | Fix |
|-------|------|-----|
| Token TTL | security.py:85 | Store creation time, check expiry |
| Path Traversal | knowledge_graph.py:278 | Validate path before write |
| Event Handler Crashes | orchestrator.py:88 | Wrap in try/except |
| Incomplete Incoming Load | knowledge_graph.py:326 | Fix deduplication |
| Stats Recomputation | knowledge_graph.py:63 | Cache stats incrementally |
| Deprecated utcnow() | events.py:15 | Use datetime.now(datetime.UTC) |
| __import__ hack | manager.py:58 | Use regular import |
| Whisper Model Retention | transcriber.py:70 | Add cleanup method |

---

## Next Feature Ideas

### 1. Persistent Knowledge Graph Backend
- SQLite or Neo4j for production persistence
- Backup/restore functionality
- Multi-user graph isolation

### 2. Real-Time Video Streaming
- WebRTC live camera feeds
- Screen recording integration
- Live transcription

### 3. Multi-Language Transcription
- Auto-detect language
- Support 50+ languages
- Translation pipeline

### 4. Agent Collaboration Workflows
- Agent-to-agent communication
- Task handoff protocols
- Collaborative problem solving

### 5. Plugin System
- Dynamic plugin loading
- Third-party integrations
- Marketplace for community plugins
