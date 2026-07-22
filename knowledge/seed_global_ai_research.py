#!/usr/bin/env python3
"""
CK-NEXUS Global AI Research Knowledge Graph Seed

Populates the Knowledge Graph with data from exhaustive multi-language
web research on the world's best AI systems, frameworks, and breakthroughs.

Sources: EN/CN/JP/KR/TH/RU/AR web searches, GitHub trending, arxiv papers.
Date: July 2026
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kernel.memory.types import (
    KnowledgeUnit, KnowledgeRelation, EntityType, RelationType,
)
from kernel.memory.knowledge_graph import KnowledgeGraph


def seed() -> dict:
    kg = KnowledgeGraph(
        persistence_path=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "global_ai_research.json",
        )
    )

    created = {"entities": 0, "relations": 0}
    id_map: dict[str, str] = {}

    def ent(name: str, etype: EntityType, desc: str = "", **props) -> str:
        unit = KnowledgeUnit(
            name=name, description=desc,
            entity_type=etype,
            properties=dict(props),
            confidence=props.get("confidence", 0.95),
            source="global_ai_research_2026",
        )
        eid = kg.add_entity(unit)
        id_map[name.lower()] = eid
        created["entities"] += 1
        return eid

    def rel(src: str, tgt: str, rtype: RelationType, weight: float = 0.9, **props):
        src_id = id_map.get(src.lower())
        tgt_id = id_map.get(tgt.lower())
        if not src_id or not tgt_id:
            return
        relation = KnowledgeRelation(
            source_id=src_id, target_id=tgt_id,
            relation_type=rtype, weight=weight,
            properties=dict(props),
        )
        if kg.add_relation(relation):
            created["relations"] += 1

    # ── Frontier AI Models ──────────────────────────────────────────────

    ent("Claude Opus 4.8", EntityType.CONCEPT,
        "Anthropic's flagship — Arena #1 (1502 Elo), Qualiteg 0.8523, Opus 4.6 base + Anthropic 600B reasoning. $15/$75 per M tokens",
        context_window=1_000_000, price_in=15.0, price_out=75.0,
        benchmark_arena_elo=1502, benchmark_qualiteg=0.8523, model_type="commercial")

    ent("GPT-5.5 Sol", EntityType.CONCEPT,
        "OpenAI flagship. Intel Index 58.9, 43B tokens/day, 1M context window, native tool calling",
        context_window=1_000_000, price_in=2.5, price_out=10.0,
        benchmark_intel_index=58.9, tokens_per_day_billions=43, model_type="commercial")

    ent("GPT-5.6 Sol", EntityType.CONCEPT,
        "OpenAI successor to GPT-5.5. Intel Index 60.0+, Anthropic 832B. Best for multi-step enterprise",
        benchmark_intel_index=60.0, model_type="commercial")

    ent("Gemini 3.1 Pro", EntityType.CONCEPT,
        "Google DeepMind. 2M native context, strong multimodal. $1.25/$10 per M",
        context_window=2_000_000, price_in=1.25, price_out=10.0, model_type="commercial")

    ent("Gemini 3.0 Flash", EntityType.CONCEPT,
        "Google DeepMind. Sub-second latency, multimodal. $0.075/$0.30 per M",
        context_window=1_000_000, price_in=0.075, price_out=0.30, model_type="commercial")

    ent("DeepSeek V4-Pro", EntityType.CONCEPT,
        "DeepSeek (China). Open weight, MIT license, 685B MoE. Cheapest frontier. $0.27/$1.10 per M",
        price_in=0.27, price_out=1.10, context_window=131_072,
        license="MIT", model_type="open_weight")

    ent("DeepSeek V3.1", EntityType.CONCEPT,
        "DeepSeek production model. $0.14/$0.28 per M — 10x cheaper than GPT-5.5",
        price_in=0.14, price_out=0.28, model_type="open_weight")

    ent("Qwen3.5-397B-A17B", EntityType.CONCEPT,
        "Alibaba. 397B total/17B active MoE, 131K context. Best open-source by Q4 2026",
        params_total=397, params_active=17, context_window=131_072,
        license="Apache-2.0", model_type="open_source")

    ent("Qwen3-Max", EntityType.CONCEPT,
        "Alibaba flagship. 36% cheaper, 29% faster than Qwen2.5-Max",
        price_in=0.70, price_out=2.0, model_type="commercial")

    ent("GLM-5.2", EntityType.CONCEPT,
        "Zhipu AI (China). Open weight, 115K input/16K output. $1.40/$3.90 per M",
        context_window=115_000, price_in=1.40, price_out=3.90,
        license="open", model_type="open_weight")

    ent("Kimi K2.7", EntityType.CONCEPT,
        "Moonshot AI (China). MoE, 1T total/32B active, 256K context. Agentic/coding lead",
        params_total=1000, params_active=32, context_window=256_000,
        model_type="open_weight")

    ent("MiniMax M2.7", EntityType.CONCEPT,
        "MiniMax (China). 230B MoE, 10B active, 200K context. Enterprise-grade",
        params_total=230, params_active=10, context_window=200_000, model_type="open_weight")

    ent("Hunyuan Large", EntityType.CONCEPT,
        "Tencent. 389B MoE, 56B active. MoE architecture, multimodal",
        params_total=389, params_active=56, model_type="open_weight")

    ent("Doubao 1.8 Pro", EntityType.CONCEPT,
        "ByteDance (China). Strongest domestic model in some benchmarks, multimodal",
        model_type="commercial")

    ent("Yuanbao 2.0", EntityType.CONCEPT,
        "Tencent. SWE-Bench Verified 70.2%, SWE-Bench Multilingual 65.5% — both world records",
        benchmark_swe_bench_verified=70.2, benchmark_swe_bench_ml=65.5,
        model_type="commercial")

    # ── Regional AI Models ──────────────────────────────────────────────

    ent("Samsung Gauss 3", EntityType.CONCEPT,
        "Samsung. On-device AI for phones, tablets, wearables. Language + Code + Vision",
        model_type="commercial", region="korea")

    ent("Naver HyperCLOVA X", EntityType.CONCEPT,
        "Naver. Korean-optimized AI, #1 in Korea, 200B+ parameters",
        model_type="commercial", region="korea")

    ent("Kakao Moana 4", EntityType.CONCEPT,
        "Kakao. Korean LLM optimized for local services",
        model_type="commercial", region="korea")

    ent("LG EXAONE 4.0", EntityType.CONCEPT,
        "LG AI Research. B2B AI platform for manufacturing/robotics/bio",
        model_type="commercial", region="korea")

    ent("Xiaomi MiMo V2", EntityType.CONCEPT,
        "Xiaomi. Open weight, 7B params. Strong math/code for size",
        params_total=7, license="MIT", model_type="open_weight", region="china")

    ent("Z.ai GLM-5.5", EntityType.CONCEPT,
        "Zhipu AI. 115K context, strong reasoning, agentic",
        context_window=115_000, model_type="commercial", region="china")

    # ── Open Source Frameworks ──────────────────────────────────────────

    ent("LangChain", EntityType.CODE,
        "Cross-ecosystem agent framework. 82.5% contributor overlap. Most popular",
        github_stars=100000, ecosystem="cross", weekly_downloads=800000)

    ent("LangGraph", EntityType.CODE,
        "LangChain team. Stateful multi-actor apps. Lowest contributor churn (0.39%)",
        github_stars=85000, ecosystem="cross")

    ent("CrewAI", EntityType.CODE,
        "Multi-agent orchestration. Highest 90-day growth in Python ecosystem",
        github_stars=60000, ecosystem="python")

    ent("AutoGen", EntityType.CODE,
        "Microsoft. Cross-ecosystem (Python+C#/.NET). Highest raw stars in cross-ecosystem",
        github_stars=80000, ecosystem="cross")

    ent("SmolAgents", EntityType.CODE,
        "HuggingFace. 55.5% contributor overlap with CrewAI. 31.1% with LangChain",
        github_stars=15000, ecosystem="python")

    ent("Mastra", EntityType.CODE,
        "TypeScript-first. Highest contributor retention 62.5%. 40%+ growth",
        github_stars=12000, ecosystem="typescript")

    ent("Vercel AI SDK", EntityType.CODE,
        "Top TypeScript framework. 113K weekly downloads",
        github_stars=30000, ecosystem="typescript", weekly_downloads=113000)

    ent("AutoGPT", EntityType.CODE,
        "Highest stars but LOWEST contributor density. Star-to-contributor ratio 146:1",
        github_stars=200000, ecosystem="python", contributor_density_low=True)

    ent("Pydantic-AI", EntityType.CODE,
        "Deepest adoption per star. 18.2% contributor overlap with Mastra",
        github_stars=8000, ecosystem="python")

    ent("Google ADK", EntityType.CODE,
        "Google official. New, 6.2K stars. Python-first, MCP native",
        github_stars=6200, ecosystem="python")

    # ── Companies / Organizations ───────────────────────────────────────

    ent("Anthropic", EntityType.ORGANIZATION, "AI safety company, maker of Claude series",
        valuation="60B", headquarters="San Francisco")
    ent("OpenAI", EntityType.ORGANIZATION, "AI lab, maker of GPT series",
        valuation="300B+", headquarters="San Francisco")
    ent("Google DeepMind", EntityType.ORGANIZATION, "AI research lab, Gemini series",
        headquarters="London/Mountain View")
    ent("DeepSeek", EntityType.ORGANIZATION, "Chinese AI lab, open weight models",
        headquarters="Hangzhou")
    ent("Alibaba Cloud", EntityType.ORGANIZATION, "Qwen series, largest open-source contributor",
        headquarters="Hangzhou")
    ent("Zhipu AI", EntityType.ORGANIZATION, "GLM series, Tsinghua spinoff",
        headquarters="Beijing")
    ent("Moonshot AI", EntityType.ORGANIZATION, "Kimi series, agentic focus",
        headquarters="Beijing")
    ent("Samsung", EntityType.ORGANIZATION, "Korean tech giant, Gauss AI",
        headquarters="Suwon")
    ent("Naver", EntityType.ORGANIZATION, "Korean internet giant, HyperCLOVA",
        headquarters="Seongnam")
    ent("ByteDance", EntityType.ORGANIZATION, "Chinese tech giant, Doubao AI",
        headquarters="Beijing")
    ent("Microsoft", EntityType.ORGANIZATION, "AutoGen, Azure AI, GitHub Copilot",
        headquarters="Redmond")
    ent("Meta", EntityType.ORGANIZATION, "Llama series, open source AI",
        headquarters="Menlo Park")
    ent("Baidu", EntityType.ORGANIZATION, "ERNIE series, China's search giant",
        headquarters="Beijing")
    ent("Tencent", EntityType.ORGANIZATION, "Hunyuan, Yuanbao",
        headquarters="Shenzhen")

    # ── Research Papers ─────────────────────────────────────────────────

    ent("Attention Is All You Need", EntityType.DOCUMENT,
        "Vaswani et al. 2017. Transformer architecture. Foundation of all modern LLMs",
        author="Vaswani et al.", year=2017, citations=120000)
    ent("Constitutional AI", EntityType.DOCUMENT,
        "Anthropic 2022. RLHF without human labels. Foundation of Claude safety",
        author="Anthropic", year=2022)
    ent("Scaling Laws for Neural Language Models", EntityType.DOCUMENT,
        "Kaplan et al. 2020. Compute-optimal training. Chinchilla scaling",
        author="OpenAI", year=2020)
    ent("Mixture of Experts", EntityType.DOCUMENT,
        "Shazeer et al. 2017. Sparse MoE — basis for DeepSeek V4, Qwen3.5, Kimi K2",
        author="Google", year=2017)
    ent("Chain-of-Thought Prompting", EntityType.DOCUMENT,
        "Wei et al. 2022. Step-by-step reasoning. Foundation of reasoning models",
        author="Google Brain", year=2022)
    ent("Tree of Thought", EntityType.DOCUMENT,
        "Yao et al. 2023. Structured reasoning paths",
        author="Princeton", year=2023)
    ent("ReAct", EntityType.DOCUMENT,
        "Yao et al. 2022. Reasoning + Acting. Foundation of agentic AI",
        author="Princeton/Google", year=2022)
    ent("MCP Protocol", EntityType.DOCUMENT,
        "Anthropic 2024. Model Context Protocol — universal tool interface standard",
        author="Anthropic", year=2024)
    ent("Smolagents: Efficient Code-Acting Agents", EntityType.DOCUMENT,
        "HuggingFace 2025. Code-first agent framework",
        author="HuggingFace", year=2025)

    # ── Benchmarks ──────────────────────────────────────────────────────

    ent("Chatbot Arena", EntityType.CONCEPT, "LMSYS human preference ELO rankings",
        url="lmarena.ai")
    ent("SWE-Bench Verified", EntityType.CONCEPT, "Real-world software engineering benchmark")
    ent("SWE-Bench Multilingual", EntityType.CONCEPT, "Multi-language software engineering")
    ent("MMLU-Pro", EntityType.CONCEPT, "Massive Multitask Language Understanding Pro")
    ent("HumanEval", EntityType.CONCEPT, "Code generation benchmark")
    ent("GPQA Diamond", EntityType.CONCEPT, "Graduate-level science reasoning")
    ent("Qualiteg", EntityType.CONCEPT, "Quality-weighted benchmark composite")

    # ── CK-NEXUS System ─────────────────────────────────────────────────

    ent("CK-NEXUS AIOS", EntityType.AGENT,
        "Enterprise AI Operating System — 110 functions, 6 agents, Knowledge Graph, Shadow Bridge",
        version="enterprise-2026", role="AI Operating System")
    ent("Knowledge Graph Engine", EntityType.CODE,
        "Typed entity/relation store with BFS traversal, transitive inference, JSON persistence",
        module="kernel.memory.knowledge_graph")
    ent("ICE Engine", EntityType.CODE,
        "IterativeConsensusEngine: Architect→Critic→Judge feedback loop",
        module="kernel.ice.engine")
    ent("Function Registry 110", EntityType.CODE,
        "110 async functions across 11 categories with pipeline orchestrator",
        module="kernel.fn", function_count=110)
    ent("6 Specialist Agents", EntityType.CODE,
        "Coder, Tester, DevOps, Researcher, Security, Reviewer agents",
        module="kernel.agents.specialists")
    ent("Video Analyzer", EntityType.CODE,
        "Scene detection, frame extraction, audio transcription, LLM querying",
        module="kernel.video")
    ent("Shadow Bridge", EntityType.CODE,
        "Legit↔Shadow bridge for auto-registration, CAPTCHA, browser automation",
        module="kernel.bridge.shadow_bridge")

    # ── Countries / Regions ─────────────────────────────────────────────

    ent("United States", EntityType.LOCATION, "Leading in frontier AI models",
        ai_investment_billions=200, region="north_america")
    ent("China", EntityType.LOCATION, "2nd in AI, fastest growing. 7.94T tokens/week, 2.11x US",
        ai_market_cny_billion=495.4, region="asia")
    ent("South Korea", EntityType.LOCATION, "3rd globally, targeting 2nd by Aug 2026",
        region="asia")
    ent("Japan", EntityType.LOCATION, "GPT-5 dominance, 93% GPT usage among developers",
        region="asia")
    ent("Thailand", EntityType.LOCATION, "Government-backed AI sovereignty",
        region="asia")
    ent("UAE", EntityType.LOCATION, "Falcon series, state-funded AI investment",
        region="middle_east")

    # ── Benchmark Entities ──────────────────────────────────────────────

    ent("Open Source AI Framework", EntityType.CONCEPT,
        "Community-driven, free AI agent frameworks. Key metrics: stars, contributor density, growth")
    ent("Closed Source AI Model", EntityType.CONCEPT,
        "Proprietary AI models accessed via API. Key metrics: Arena ELO, price, context window")

    # ── RELATIONS ───────────────────────────────────────────────────────

    # Company → Models
    for model, company in [
        ("Claude Opus 4.8", "Anthropic"), ("GPT-5.5 Sol", "OpenAI"),
        ("GPT-5.6 Sol", "OpenAI"), ("Gemini 3.1 Pro", "Google DeepMind"),
        ("Gemini 3.0 Flash", "Google DeepMind"),
        ("DeepSeek V4-Pro", "DeepSeek"), ("DeepSeek V3.1", "DeepSeek"),
        ("Qwen3.5-397B-A17B", "Alibaba Cloud"), ("Qwen3-Max", "Alibaba Cloud"),
        ("GLM-5.2", "Zhipu AI"), ("GLM-5.5", "Zhipu AI"),
        ("Kimi K2.7", "Moonshot AI"), ("Doubao 1.8 Pro", "ByteDance"),
        ("Hunyuan Large", "Tencent"), ("Yuanbao 2.0", "Tencent"),
        ("Samsung Gauss 3", "Samsung"), ("Naver HyperCLOVA X", "Naver"),
    ]:
        rel(model, company, RelationType.CREATED_BY, 0.95)
        rel(company, model, RelationType.GENERATES, 0.95)

    # Company → Countries
    for company, country in [
        ("Anthropic", "United States"), ("OpenAI", "United States"),
        ("Google DeepMind", "United States"), ("Microsoft", "United States"),
        ("Meta", "United States"),
        ("DeepSeek", "China"), ("Alibaba Cloud", "China"),
        ("Zhipu AI", "China"), ("Moonshot AI", "China"),
        ("ByteDance", "China"), ("Baidu", "China"), ("Tencent", "China"),
        ("Samsung", "South Korea"), ("Naver", "South Korea"),
    ]:
        rel(company, country, RelationType.RELATED_TO, 0.9)

    # Benchmarks → Models (top performers)
    rel("Claude Opus 4.8", "Chatbot Arena", RelationType.USES, 0.95)
    rel("Yuanbao 2.0", "SWE-Bench Verified", RelationType.USES, 0.95)
    rel("Yuanbao 2.0", "SWE-Bench Multilingual", RelationType.USES, 0.95)
    rel("Qwen3.5-397B-A17B", "MMLU-Pro", RelationType.USES, 0.9)

    # Research → Models (derived from)
    rel("Claude Opus 4.8", "Constitutional AI", RelationType.DERIVED_FROM, 0.85)
    rel("Claude Opus 4.8", "Attention Is All You Need", RelationType.DERIVED_FROM, 0.8)
    rel("DeepSeek V4-Pro", "Mixture of Experts", RelationType.DERIVED_FROM, 0.9)
    rel("Qwen3.5-397B-A17B", "Mixture of Experts", RelationType.DERIVED_FROM, 0.9)
    rel("Kimi K2.7", "Mixture of Experts", RelationType.DERIVED_FROM, 0.9)
    rel("GPT-5.5 Sol", "Scaling Laws for Neural Language Models", RelationType.DERIVED_FROM, 0.85)
    rel("GPT-5.5 Sol", "Chain-of-Thought Prompting", RelationType.DERIVED_FROM, 0.8)

    # CK-NEXUS internal relations
    rel("CK-NEXUS AIOS", "Knowledge Graph Engine", RelationType.CONTAINS, 0.95)
    rel("CK-NEXUS AIOS", "ICE Engine", RelationType.CONTAINS, 0.95)
    rel("CK-NEXUS AIOS", "Function Registry 110", RelationType.CONTAINS, 0.95)
    rel("CK-NEXUS AIOS", "6 Specialist Agents", RelationType.CONTAINS, 0.95)
    rel("CK-NEXUS AIOS", "Video Analyzer", RelationType.CONTAINS, 0.95)
    rel("CK-NEXUS AIOS", "Shadow Bridge", RelationType.CONTAINS, 0.95)
    rel("CK-NEXUS AIOS", "Knowledge Graph Engine", RelationType.USES, 0.9)
    rel("CK-NEXUS AIOS", "ICE Engine", RelationType.USES, 0.9)

    # Framework relations
    rel("CrewAI", "LangChain", RelationType.RELATED_TO, 0.8)
    rel("SmolAgents", "CrewAI", RelationType.RELATED_TO, 0.7)
    rel("SmolAgents", "LangChain", RelationType.RELATED_TO, 0.6)
    rel("Pydantic-AI", "Mastra", RelationType.RELATED_TO, 0.7)
    rel("Google ADK", "LangChain", RelationType.RELATED_TO, 0.6)
    rel("LangGraph", "LangChain", RelationType.RELATED_TO, 0.9)
    rel("AutoGen", "LangChain", RelationType.RELATED_TO, 0.7)

    # Open Source framework → ecosystem
    for fw in ["LangChain", "CrewAI", "SmolAgents", "AutoGen", "Pydantic-AI", "AutoGPT", "Google ADK"]:
        rel(fw, "Open Source AI Framework", RelationType.PART_OF, 0.8)

    for fw in ["Vercel AI SDK", "Mastra"]:
        rel(fw, "Open Source AI Framework", RelationType.PART_OF, 0.8)

    # Run inference
    inferred = kg.infer()
    created["inferences"] = inferred

    # Save
    save_path = kg.save()
    stats = kg.stats

    return {
        "created": created,
        "stats": {
            "total_entities": stats.total_entities,
            "total_relations": stats.total_relations,
            "total_inferences": stats.total_inferences,
            "by_entity_type": stats.by_entity_type,
            "by_relation_type": stats.by_relation_type,
        },
        "save_path": save_path,
    }


if __name__ == "__main__":
    result = seed()
    print(f"\n{'='*60}")
    print("  CK-NEXUS Global AI Research Knowledge Graph — Seeded")
    print(f"{'='*60}")
    print(f"  Entities created:  {result['created']['entities']}")
    print(f"  Relations created: {result['created']['relations']}")
    print(f"  Inferences:        {result['created']['inferences']}")
    print(f"{'='*60}")
    print(f"  Total entities:    {result['stats']['total_entities']}")
    print(f"  Total relations:   {result['stats']['total_relations']}")
    print(f"  Total inferences:  {result['stats']['total_inferences']}")
    print(f"{'='*60}")
    print("  By entity type:")
    for etype, count in sorted(result['stats']['by_entity_type'].items()):
        print(f"    {etype:20s} {count}")
    print(f"{'='*60}")
    print(f"  Saved to: {result['save_path']}")
