# CK-NEXUS AIOS Documentation

## Overview

CK-NEXUS is an Enterprise AI Operating System that provides:

- **100 Executable Functions** across 10 categories
- **6 Specialist AI Agents** for automated tasks
- **Knowledge Graph** with typed entities and transitive inference
- **Video Analysis** — `/watch` command for YouTube/TikTok/Instagram videos
- **Event-Driven Architecture** with EventBus for component communication

---

## Architecture

```
OrchestratorEngine
├── MemoryOS              (episodic + semantic memory)
├── KnowledgeGraph        (typed entities + relations + inference)
├── KnowledgePipeline     (extract → infer → log)
├── FunctionRegistry      (100 functions across 10 categories)
├── AgentManager          (6 specialist agents)
├── VideoAnalyzer         (frames + transcript + LLM query)
└── EventBus              (all components communicate via events)
```

---

## Quick Start

```python
from kernel.orchestrator import OrchestratorEngine

engine = OrchestratorEngine()
engine.bootstrap()

# Process a request
result = await engine.process("scan example.com for vulnerabilities")
print(result["output"])

# Analyze a video
result = await engine.process("/watch https://youtube.com/watch?v=abc What is this?")
print(result["video"])
```

---

## Components

### 1. Function Registry (100 functions)

10 categories with 10 functions each:

| Category | Examples |
|----------|----------|
| System Core | health_check, system_info, process_list, memory_usage |
| Input Gateways | http_request, websocket_connect, file_upload, email_send |
| OSINT | dns_lookup, whois_lookup, ip_geolocation, port_scan |
| Security Scanning | vulnerability_scan, dependency_audit, config_audit |
| Offensive | password_spray, exploit_exec, meterpreter_reverse |
| Storage | file_read, file_write, database_query, cache_set |
| AI/MCP | llm_complete, embedding_generate, rag_query |
| Network/Proxy | proxy_route, traffic_capture, dns_tunnel |
| Termux/Mobile | sms_send, call_log, location_get |
| Advanced Logic | workflow_create, conditional_exec, pipeline_chain |

### 2. Specialist Agents

| Agent | Capabilities |
|-------|-------------|
| CoderAgent | code generation, refactoring, debugging, code review |
| TesterAgent | unit/integration test generation |
| DevOpsAgent | Dockerfile, deployment, monitoring, CI/CD |
| ResearcherAgent | literature review, feasibility study |
| SecurityAgent | security audit, vulnerability scanning, threat modeling |
| ReviewerAgent | code review, architecture review, best practices |

### 3. Knowledge Graph

```python
from kernel.memory import KnowledgeGraph
from kernel.memory.types import EntityType, RelationType

kg = KnowledgeGraph()

# Add entities
kg.add_entity(KnowledgeUnit(
    name="CK-NEXUS",
    entity_type=EntityType.CONCEPT,
    description="Enterprise AI Operating System"
))

# Add relations
kg.add_relation(KnowledgeRelation(
    source_id=src_id,
    target_id=tgt_id,
    relation_type=RelationType.DEPENDS_ON
))

# Traverse
results = kg.traverse(start_id, max_depth=3)

# Infer
inferred_count = kg.infer()  # Transitive inference
```

### 4. Video Analysis

```python
from kernel.video import VideoAnalyzer

analyzer = VideoAnalyzer()

# Analyze a video
result = analyzer.analyze(
    "https://youtube.com/watch?v=abc",
    query="What is the main point?",
    max_frames=100
)

print(f"Keyframes: {result.keyframes_extracted}")
print(f"Transcript segments: {len(result.transcript.segments)}")
print(f"Answer: {result.answer}")
```

---

## Event System

All components communicate via EventBus:

```python
# Listen to events
engine.event_bus.on("orchestrator.cycle.complete", handler)

# Emit events
await engine.event_bus.emit("video.watch.complete", {"result_id": "..."})
```

Key events:
- `memory.remember` / `memory.recall`
- `kg.add_entity` / `kg.add_relation` / `kg.query`
- `video.watch` / `video.watch.complete`
- `agent.delegate` / `agent.delegated`
- `fn.execute` / `fn.executed`

---

## Testing

```bash
# Run all tests
python -m pytest tests/unit/ -v

# Run specific module
python -m pytest tests/unit/test_video.py -v
```

---

## API Key Configuration

```bash
# Set environment variable
export OPENROUTER_API_KEY="sk-or-v1-..."

# Or add to .env file
echo 'OPENROUTER_API_KEY=sk-or-v1-...' >> .env
```

---

## File Structure

```
kernel/
├── agents/specialists/    (6 agents)
├── memory/knowledge_graph.py
├── video/                 (analyzer, frame_extractor, scene_detector, transcriber)
├── fn/                    (100 functions)
├── orchestrator.py        (unified engine)
└── 18 kernel modules

knowledge/
├── schema.py
├── extraction.py
└── pipeline.py

tests/unit/               (464 tests)
```
