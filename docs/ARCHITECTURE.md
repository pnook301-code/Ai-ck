# CK-NEXUS AIOS — Architecture

## System Overview

CK-NEXUS AIOS is a modular Enterprise AI Operating System built on Python 3.12+ with clean architecture principles.

## Core Components

```
┌─────────────────────────────────────────────────────────┐
│                    Client Layer                          │
│  Web UI │ REST API │ CLI │ n8n Workflows                 │
├─────────────────────────────────────────────────────────┤
│                  Gateway Layer                           │
│  LiteLLM (100+ Models) │ Provider Router │ Auto Failover │
├─────────────────────────────────────────────────────────┤
│                  CK-NEXUS Core                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │Knowledge │ │  ICE     │ │ 6 Agents │ │ 110 Fns  │   │
│  │  Graph   │ │  Engine  │ │          │ │          │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │  Video   │ │ Security │ │  Shadow  │ │  State   │   │
│  │ Analyzer │ │  Layer   │ │  Bridge  │ │ Manager  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
├─────────────────────────────────────────────────────────┤
│                   Data Layer                             │
│  Qdrant (Vector) │ PostgreSQL │ Redis (Cache)            │
└─────────────────────────────────────────────────────────┘
```

## Module Map

| Module | Path | Purpose |
|--------|------|---------|
| Config | kernel/config.py | System configuration |
| Container | kernel/container.py | DI container |
| EventBus | kernel/events.py | Event-driven communication |
| CommandBus | kernel/commands.py | Command pattern |
| Logger | kernel/logger.py | Structured logging |
| Security | kernel/security.py | Auth, bcrypt, JWT |
| State | kernel/state.py | State management + snapshots |
| Health | kernel/health.py | Health checks |
| Metrics | kernel/metrics.py | System metrics |
| Cache | kernel/cache.py | LRU caching |
| Registry | kernel/registry.py | Service registry |
| Runtime | kernel/runtime.py | Application runtime |
| Bootstrap | kernel/bootstrap.py | System startup |
| Lifecycle | kernel/lifecycle.py | Component lifecycle |
| Orchestrator | kernel/orchestrator.py | Main orchestrator |
| Function Registry | kernel/fn/ | 110 async functions |
| Agent Runtime | kernel/agents/ | 6 specialist agents |
| Knowledge Graph | kernel/memory/ | Typed entity/relation store |
| Video Analysis | kernel/video/ | Scene detection, transcription |
| ICE Engine | kernel/ice/ | Iterative consensus |
| Sandbox | kernel/sandbox/ | Isolated execution |
| Shadow Bridge | kernel/bridge/ | Legit ↔ Shadow connection |
| Knowledge Pipeline | knowledge/ | Text extraction, entity inference |

## Data Flow

1. **Input** → Client sends request (text, video, command)
2. **Orchestration** → OrchestratorEngine routes to appropriate handler
3. **Processing** → Agent/Function processes the request
4. **Knowledge** → Results stored in Knowledge Graph
5. **Response** → Output returned to client
6. **Persistence** → State saved to PostgreSQL/Qdrant
