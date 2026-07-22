# CK-NEXUS AIOS — Changelog

## [1.0.0-rc1] - 2026-07-21

### Added
- Knowledge Graph Engine with 76 entities, 81 relations
- Global AI Research Knowledge Base (8 languages)
- Shadow Bridge Functions (11.1-11.10)
- Function Registry expanded to 110 functions
- Production website (landing page)
- LiteLLM config with 100+ AI models
- Docker Compose stack (7 services)
- Provider Router with zero-downtime switching
- One-command VPS installer

### Fixed
- datetime.utcnow() deprecation (4 locations)
- Ruff lint errors (154 → 0)
- Unused variable warnings
- Lambda expression in commands.py

### Changed
- Function count: 100 → 110
- Test assertions updated to 110
- Coverage: 86%

## [0.9.0] - 2026-07-20

### Added
- Shadow Bridge (Legit ↔ Shadow connection)
- ICE Engine (Architect → Critic → Judge)
- SandboxExecutor (isolated Python execution)
- Video Analysis Module
- 6 Specialist Agents
- 117 integration tests
- 14 critical+high security fixes

### Fixed
- SHA256 → bcrypt password hashing
- Token TTL enforcement
- Event handler error safety
- BFS traversal O(n) → O(1)
- Stats caching with dirty tracking
