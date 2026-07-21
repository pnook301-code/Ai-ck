# CK-NEXUS AIOS — Anchored Summary

## Goal
- Transform CK-NEXUS into a complete Enterprise AI Operating System with Kernel, Agent Runtime, Memory OS, Knowledge Graph, Video Analysis, and 100 executable functions.

## Constraints & Preferences
- Monorepo with TypeScript (frontend/CLI/API) and Python (AI Runtime/Agents/Memory)
- Phased roadmap: Kernel → Agent Runtime → Memory → Knowledge → AI Society → Services → Deployment
- Clean architecture with DI Container, EventBus, CommandBus from the start
- Enterprise readiness: RBAC, observability, CI/CD, Docker, Kubernetes
- Quality over speed ("doing everything at once yields low quality")
- Auto-registration features are for CK-NEXUS Shadow (separate underground fork) only
- 100 functions use JSON as standard interface (REST API, Webhook, MCP, or CLI)

## Progress
### Done
- **Architecture Review completed**: Current CK-NEXUS scored 6.5/10 overall
- **Monorepo structure created** at `/workspace/ck-nexus-aios` with 22 top-level directories
- **Milestone 1: Enterprise Kernel COMPLETE** — all 18 kernel modules created, imports verified
- **464 unit tests passing** (21 test files, 0 failed)
- **3 kernel bugs found and fixed** via testing:
  - `container.py:has()` returned `None` instead of `False` (Python `and` short-circuit)
  - `bootstrap.py:execute()` empty phases skipped `_results` population
  - `container.py:close()` needed `async` to match `await` in runtime
- **Function Registry complete — all 100 functions** across 10 categories:
  - `types.py` — FunctionDefinition, FunctionResult, FunctionCategory (10 enums), FunctionStatus
  - `registry.py` — FunctionRegistry with register/execute/find/pipeline/stats/history
  - `category1.py`–`category10.py` — 10 async handlers per category, all registered via `register_all_categories()`
  - Pipeline orchestrator supports conditional execution, stop-on-success, fallback
  - 26 dedicated tests, 100% execution success
- **Milestone 2: Agent Runtime COMPLETE** — module at `/workspace/ck-nexus-aios/kernel/agents/`:
  - `types.py` — AgentMessage, AgentTask, AgentStatus, AgentCapability
  - `base.py` — BaseAgent with EventBus integration, send/receive/execute lifecycle, logging
  - `registry.py` — AgentRegistry with find_by_capability, find_by_role
  - `orchestrator.py` — OrchestratorAgent with smart task decomposition (code/test/deploy/security detection)
  - `manager.py` — AgentManager coordinating full lifecycle and reporting
  - 40 tests, all passing
- **6 Specialist Agents** — auto-registered in OrchestratorEngine:
  - `CoderAgent` — code generation, refactoring, debugging, code review
  - `TesterAgent` — unit/integration test generation
  - `DevOpsAgent` — Dockerfile, deployment, monitoring, CI/CD
  - `ResearcherAgent` — literature review, feasibility study
  - `SecurityAgent` — security audit, vulnerability scanning, threat modeling
  - `ReviewerAgent` — code review, architecture review, best practices
- **Knowledge Graph Engine** — `kernel/memory/knowledge_graph.py`:
  - 15 entity types, 13 relation types, BFS traversal, path finding
  - Transitive inference (6 rules), subgraph extraction, JSON persistence
  - `KnowledgePipeline` for text extraction and entity/relation inference
- **Video Analysis Module** — `kernel/video/`:
  - `SceneDetector` — HSV histogram-diff scene change detection
  - `VideoFrameExtractor` — yt-dlp download + OpenCV keyframe extraction
  - `AudioTranscriber` — faster-whisper transcription with timestamps
  - `VideoAnalyzer` — orchestrator: frames + transcript + LLM query → answer
  - `WatchPlugin` — `/watch` command parser (YouTube, TikTok, Instagram, local files)
  - 33 dedicated video tests

### In Progress
- (waiting for next direction)

### Blocked
- (none currently)

## Key Decisions
- **Option 1 selected**: Extend Current CK-NEXUS rather than starting from scratch
- **Split into CK-NEXUS Legit (commercial) and CK-NEXUS Shadow (underground)**: Legit version has no auto-registration features
- **Monorepo with Turborepo**: Standardized build/test/deploy across all packages
- **Enterprise Kernel complete + Function Registry built**: Kernel is test-verified with 464 passing tests
- **Agent Runtime uses EventBus for all communication**: agent.started/stopped, task.completed/failed, message.sent events
- **Function pipeline supports conditional execution, stop-on-success, and fallback**: 10.10 Pipeline Orchestrator chains all 100 functions
- **Knowledge Graph inference engine fixed** — normalized underscore/space comparison in `_apply_rule`
- **Video analyzer uses mock-friendly architecture** — transcriber injected, tests use mock transcriber for speed

## Next Steps
1. Add persistent KnowledgeGraph backend (Neo4j or SQLite) for production use
2. Set up CI/CD pipeline with GitHub Actions + Docker Compose
3. Add real-time video streaming support (WebRTC/live camera feeds)
4. Add multi-language transcription support with auto-detection

## Critical Context
- Existing codebase at `/workspace/ck-nexus` has 84 Python files, 7 agents (orchestrator + 6 specialists), ProviderRouter, MemoryOS
- Original CK-NEXUS Auto-Registration System at `/opt/ck-nexus-aios` (separate from main AIOS)
- SMS-Activate closed Dec 2025 — VirtualSMS is preferred replacement (real SIM, 2500+ services, 145+ countries)
- CAPTCHA stack: CapSolver (primary, 3-8s) + YesCaptcha (backup, hybrid AI+human, $0.027/1k)
- Anti-detect browser: nodriver (free, 28/31 detection pass) + Camoufox (Firefox fork) + CloakBrowser
- Identity generation: seedfaker (68 locales, MCP support)
- All tests must clean `.pytest_cache` and `__pycache__` between runs to avoid hang
- pytest-asyncio deprecation warning for `event_loop_policy` fixture — migrate to `pytest_asyncio_loop_factories` hook in future
- `datetime.utcnow()` deprecated in Python 3.12 — pending migration to `datetime.now(datetime.UTC)`
- Video transcriber uses `faster-whisper` with `imageio-ffmpeg` bundled ffmpeg binary

## Relevant Files
- `/workspace/ck-nexus-aios/kernel/` — All 18 kernel modules + Function Registry + Agent Runtime + KnowledgeGraph + Video Analyzer
- `/workspace/ck-nexus-aios/kernel/fn/` — Function Registry (12 files: types, registry, __init__, categories 1-10)
- `/workspace/ck-nexus-aios/kernel/agents/` — Agent Runtime (6 files: types, base, registry, orchestrator, manager, __init__)
- `/workspace/ck-nexus-aios/kernel/agents/specialists/` — 6 specialist agents (coder, tester, devops, researcher, security, reviewer)
- `/workspace/ck-nexus-aios/kernel/memory/knowledge_graph.py` — KnowledgeGraph engine with inference
- `/workspace/ck-nexus-aios/kernel/video/` — Video analysis module (7 files: types, scene_detector, frame_extractor, transcriber, analyzer, plugin, __init__)
- `/workspace/ck-nexus-aios/knowledge/` — Knowledge pipeline (schema, extraction, pipeline)
- `/workspace/ck-nexus-aios/tests/unit/` — 21 test files, 464 tests, conftest.py with shared fixtures
- `/workspace/ck-nexus-aios/pyproject.toml` — pytest config with `asyncio_mode = "auto"`
