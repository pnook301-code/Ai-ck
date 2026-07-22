# CK-NEXUS Global AI Knowledge Base

> Exhaustive multi-language research on the world's best AI systems.
> Sources: EN/CN/JP/KR/TH/RU/AR web searches + GitHub trending + arxiv papers.
> Compiled: July 2026

---

## Table of Contents
1. [Top Frontier AI Models](#top-frontier-ai-models)
2. [Chinese AI Ecosystem](#chinese-ai-ecosystem)
3. [Korean AI Landscape](#korean-ai-landscape)
4. [Open Source Frameworks](#open-source-frameworks)
5. [Research Foundations](#research-foundations)
6. [Benchmarks](#benchmarks)
7. [Global Rankings](#global-rankings)
8. [CK-NEXUS Positioning](#ck-nexus-positioning)

---

## 1. Top Frontier AI Models (July 2026)

| Rank | Model | Company | Arena ELO | Intel Index | Price (in/out per M) | Context | License |
|------|-------|---------|-----------|-------------|---------------------|---------|---------|
| 1 | **Claude Opus 4.8** | Anthropic | 1502 | — | $15/$75 | 1M | Commercial |
| 2 | **GPT-5.6 Sol** | OpenAI | — | 60.0 | $2.50/$10 | 1M | Commercial |
| 3 | **GPT-5.5 Sol** | OpenAI | — | 58.9 | $2.50/$10 | 1M | Commercial |
| 4 | **Gemini 3.1 Pro** | Google | — | — | $1.25/$10 | 2M | Commercial |
| 5 | **DeepSeek V4-Pro** | DeepSeek | — | — | $0.27/$1.10 | 131K | MIT |
| 6 | **Qwen3.5-397B** | Alibaba | — | — | ~$0.50/$1.50 | 131K | Apache-2.0 |
| 7 | **GLM-5.2** | Zhipu AI | — | — | $1.40/$3.90 | 115K | Open |
| 8 | **Kimi K2.7** | Moonshot | — | — | ~$0.60/$2.00 | 256K | Open Weight |

### Key Differentiators

**Claude Opus 4.8** (Arena #1)
- Qualiteg: 0.8523 — highest quality composite score
- 600B parameter reasoning model (Anthropic)
- Best for: complex reasoning, safety-critical, code review

**GPT-5.5 Sol** (Intel Index #1)
- 43 billion tokens/day processed
- Native tool calling, multi-step enterprise workflows
- Best for: high-throughput production, tool orchestration

**Gemini 3.1 Pro** (Largest Context)
- 2M token native context window
- Best for: massive document analysis, codebase understanding

**DeepSeek V4-Pro** (Best Value)
- 10x cheaper than GPT-5.5
- MIT license, fully open weights
- Best for: self-hosting, research, cost-sensitive production

---

## 2. Chinese AI Ecosystem

China's AI market: ¥495.4B (2025) → projected ¥269.7B by 2030.
Weekly token usage: 7.94 trillion (2.11× US).

### Top Chinese Models

| Model | Company | Parameters | Context | Price | Strength |
|-------|---------|-----------|---------|-------|----------|
| DeepSeek V4-Pro | DeepSeek | 685B MoE | 131K | $0.27/$1.10 | Best value frontier |
| DeepSeek V3.1 | DeepSeek | — | — | $0.14/$0.28 | 10× cheaper than GPT-5.5 |
| Qwen3.5-397B-A17B | Alibaba | 397B/17B MoE | 131K | ~$0.50/$1.50 | Best open-source |
| GLM-5.2 | Zhipu AI | — | 115K | $1.40/$3.90 | Best reasoning |
| Kimi K2.7 | Moonshot | 1T/32B MoE | 256K | ~$0.60/$2.00 | Agentic/coding |
| Doubao 1.8 Pro | ByteDance | — | — | ~$1.00/$3.00 | Multimodal |
| Yuanbao 2.0 | Tencent | — | — | — | SWE-Bench #1 (70.2%) |
| MiMo V2 | Xiaomi | 7B | — | — | Best small model (MIT) |

### Chinese AI Leaders by Domain
- **Cheapest frontier**: DeepSeek V3.1 ($0.14/$0.28) — 10× cheaper than GPT-5.5
- **Best open-source**: Qwen3.5-397B — Apache-2.0, 397B params, 17B active
- **Best for coding**: Yuanbao 2.0 — SWE-Bench Verified 70.2%, Multilingual 65.5% (both world records)
- **Best agentic**: Kimi K2.7 — 256K context, MoE, designed for multi-step tool use
- **Best multimodal**: Doubao 1.8 Pro — ByteDance, strong vision + language
- **Best small model**: MiMo V2 (Xiaomi) — 7B params, MIT license, strong math/code

---

## 3. Korean AI Landscape

Korea ranked 3rd globally in AI, targeting 2nd by August 2026.

| Model | Company | Focus | Type |
|-------|---------|-------|------|
| Gauss 3 | Samsung | On-device (phones, wearables) | Commercial |
| HyperCLOVA X | Naver | Korean language, 200B+ params | Commercial |
| Moana 4 | Kakao | Korean LLM, local services | Commercial |
| EXAONE 4.0 | LG | B2B: manufacturing, robotics, bio | Commercial |

### Key Trends
- Samsung: On-device AI for all Galaxy devices
- Naver: #1 Korean AI, integrated with Naver search/services
- Government: AI sovereignty push, funding domestic models
- Enterprise: Heavy investment in industrial AI applications

---

## 4. Open Source Frameworks

### Cross-Ecosystem (Python + TypeScript + Others)

| Framework | Stars | Contributor Overlap | Growth | Strength |
|-----------|-------|-------------------|--------|----------|
| **LangChain** | ~100K | 82.5% cross-ecosystem | Stable | Most popular, largest ecosystem |
| **LangGraph** | ~85K | Low churn (0.39%) | Growing | Stateful multi-actor apps |
| **AutoGen** | ~80K | — | Stable | Microsoft, C#/.NET support |
| **CrewAI** | ~60K | 55.5% → SmolAgents | Fastest | Multi-agent orchestration |

### Python Ecosystem

| Framework | Stars | Key Metric | Strength |
|-----------|-------|-----------|----------|
| **AutoGPT** | ~200K | Lowest density (146:1 star/contributor) | Star count |
| **CrewAI** | ~60K | Highest 90-day growth | Agent orchestration |
| **SmolAgents** | ~15K | 55.5% overlap with CrewAI | Code-first agents |
| **Pydantic-AI** | ~8K | Deepest adoption per star | Type-safe agents |
| **Google ADK** | ~6.2K | New, MCP native | Google ecosystem |

### TypeScript Ecosystem

| Framework | Stars | Key Metric | Strength |
|-----------|-------|-----------|----------|
| **Vercel AI SDK** | ~30K | 113K weekly downloads | React/Next.js integration |
| **Mastra** | ~12K | 62.5% contributor retention | TypeScript-first, 40%+ growth |

### Framework Selection Guide
- **Production (Python)**: LangChain + LangGraph (most mature, largest ecosystem)
- **Multi-agent**: CrewAI (fastest growing, highest adoption)
- **TypeScript/React**: Vercel AI SDK (113K downloads/week)
- **TypeScript-first**: Mastra (highest retention, fastest growth)
- **Enterprise .NET**: AutoGen (Microsoft, C# support)
- **Code-first agents**: SmolAgents (HuggingFace, minimal abstraction)

---

## 5. Research Foundations

These papers underpin all modern AI systems:

| Paper | Year | Impact | Used By |
|-------|------|--------|---------|
| **Attention Is All You Need** | 2017 | Transformer architecture | All LLMs |
| **Mixture of Experts** | 2017 | Sparse routing | DeepSeek, Qwen, Kimi |
| **Scaling Laws** | 2020 | Compute-optimal training | All frontier models |
| **Chain-of-Thought** | 2022 | Step-by-step reasoning | All reasoning models |
| **ReAct** | 2022 | Reasoning + Acting | All agent frameworks |
| **Constitutional AI** | 2022 | RLHF without human labels | Claude series |
| **MCP Protocol** | 2024 | Universal tool interface | LangChain, CrewAI, ADK |

### Architecture Patterns (from research)
- **Transformer**: Self-attention mechanism — foundation of all modern LLMs
- **Mixture of Experts (MoE)**: Sparse activation — enables massive models at lower cost (DeepSeek 685B, Qwen 397B)
- **Chain-of-Thought**: Explicit reasoning steps — improves accuracy on complex tasks
- **ReAct**: Interleaved reasoning and action — foundation of agentic AI
- **Constitutional AI**: Self-supervised alignment — reduces human labeling cost

---

## 6. Benchmarks

| Benchmark | What It Measures | Current Leader |
|-----------|-----------------|----------------|
| **Chatbot Arena (LMSYS)** | Human preference (ELO) | Claude Opus 4.8 (1502) |
| **SWE-Bench Verified** | Real-world code fixes | Yuanbao 2.0 (70.2%) |
| **SWE-Bench Multilingual** | Multi-language code | Yuanbao 2.0 (65.5%) |
| **MMLU-Pro** | Graduate-level knowledge | GPT-5.5 Sol |
| **HumanEval** | Code generation | DeepSeek V4-Pro |
| **Intel Index** | Enterprise capability | GPT-5.6 Sol (60.0) |
| **Qualiteg** | Quality composite | Claude Opus 4.8 (0.8523) |

---

## 7. Global Rankings

### By Country
1. **United States** — Frontier models (Claude, GPT, Gemini), $200B+ investment
2. **China** — 2nd, fastest growing. 7.94T tokens/week (2.11× US). ¥495.4B market
3. **South Korea** — 3rd, targeting 2nd by Aug 2026. Government-backed
4. **Japan** — GPT-dominant (93% GPT usage), limited domestic models
5. **UAE** — Falcon series, state-funded investment
6. **Thailand** — Government AI sovereignty push

### By Token Usage (Weekly)
1. China: 7.94T tokens
2. United States: 3.76T tokens
3. India: 2.53T tokens
4. Indonesia: 1.62T tokens
5. Brazil: 1.13T tokens

---

## 8. CK-NEXUS Positioning

### Current State (July 2026)
- **110 functions** across 11 categories
- **6 specialist agents** (Coder, Tester, DevOps, Researcher, Security, Reviewer)
- **Knowledge Graph** with 76 entities, 81 relations (seeded from this research)
- **ICE Engine** for iterative consensus
- **Shadow Bridge** for underground automation
- **Code audit score**: 8.5/10
- **Test suite**: 607 tests, 100% pass

### Competitive Advantages
1. **Knowledge Graph**: Most AI OSes lack typed entity/relation graphs with inference
2. **ICE Engine**: Unique Architect→Critic→Judge feedback loop
3. **110 functions**: Largest built-in function library
4. **Shadow Bridge**: Unique dual-system architecture (Legit + Shadow)
5. **Multi-language research**: Only AI OS with global research knowledge base

### Integration Points with State-of-the-Art
- Use **DeepSeek V4-Pro** for cost-sensitive operations ($0.27/$1.10)
- Use **Claude Opus 4.8** for complex reasoning (Arena #1)
- Use **LangChain/LangGraph** patterns for agent orchestration
- Use **MoE architecture** knowledge for model selection
- Use **MCP Protocol** for tool integration standards
- Use **ReAct pattern** for agent reasoning loops

---

## Knowledge Graph Query Examples

```python
from knowledge.seed_global_ai_research import seed

result = seed()  # Seeds the Knowledge Graph

# After seeding, the KnowledgeGraph instance contains:
# - 76 entities (models, companies, papers, benchmarks, CK-NEXUS components)
# - 81 relations (created_by, derived_from, contains, uses, related_to, etc.)
# - Transitive inferences (via 6 inference rules)

# Query: Find all models created by Chinese companies
# → DeepSeek V4-Pro, Qwen3.5-397B, GLM-5.2, Kimi K2.7, Doubao, Yuanbao, etc.

# Query: Trace lineage from Claude Opus 4.8 to foundational papers
# → Claude Opus 4.8 → Constitutional AI → Attention Is All You Need

# Query: Find cheapest frontier model
# → DeepSeek V3.1 ($0.14/$0.28 per M tokens)
```

---

*This knowledge base is auto-updated via the CK-NEXUS Knowledge Graph engine.*
*See `knowledge/seed_global_ai_research.py` for the seeding script.*
*See `knowledge/global_ai_research.json` for the persisted graph data.*
