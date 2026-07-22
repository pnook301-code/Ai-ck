"""
CK-NEXUS Provider-Agnostic API Layer
Zero-downtime switching between AI providers
"""

import os
import json
import time
import asyncio
import hashlib
from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum


class ProviderTier(Enum):
    FRONTIER = "frontier"       # Claude Opus, GPT-5.5, Gemini Pro
    STANDARD = "standard"       # Claude Sonnet, GPT-4o, Gemini Flash
    ECONOMY = "economy"         # DeepSeek V3, Gemini Flash Lite
    FREE = "free"               # Groq Llama, Gemma, Mixtral
    SPECIALIZED = "specialized"  # Codestral, Perplexity, Qwen


@dataclass
class ProviderConfig:
    name: str
    tier: ProviderTier
    base_url: str
    api_key_env: str
    models: List[str]
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    max_context: int = 128000
    supports_vision: bool = False
    supports_tools: bool = True
    supports_streaming: bool = True
    rate_limit_rpm: int = 60
    priority: int = 100


PROVIDERS: Dict[str, ProviderConfig] = {
    # ── OpenAI ──────────────────────────────────────────────────
    "openai": ProviderConfig(
        name="OpenAI", tier=ProviderTier.FRONTIER,
        base_url="https://api.openai.com/v1", api_key_env="OPENAI_API_KEY",
        models=["gpt-5.5-sol", "gpt-5.6-sol", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo",
                "o3", "o3-mini", "o3-pro", "o4-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"],
        cost_per_1k_input=0.0025, cost_per_1k_output=0.01, max_context=1000000,
        supports_vision=True, supports_tools=True,
    ),
    # ── Anthropic ───────────────────────────────────────────────
    "anthropic": ProviderConfig(
        name="Anthropic", tier=ProviderTier.FRONTIER,
        base_url="https://api.anthropic.com/v1", api_key_env="ANTHROPIC_API_KEY",
        models=["claude-opus-4", "claude-sonnet-4", "claude-3.5-sonnet", "claude-3.5-haiku"],
        cost_per_1k_input=0.015, cost_per_1k_output=0.075, max_context=200000,
        supports_vision=True, supports_tools=True,
    ),
    # ── Google Gemini ───────────────────────────────────────────
    "gemini": ProviderConfig(
        name="Google Gemini", tier=ProviderTier.FRONTIER,
        base_url="https://generativelanguage.googleapis.com/v1", api_key_env="GEMINI_API_KEY",
        models=["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
        cost_per_1k_input=0.00125, cost_per_1k_output=0.01, max_context=2000000,
        supports_vision=True, supports_tools=True,
    ),
    # ── DeepSeek ────────────────────────────────────────────────
    "deepseek": ProviderConfig(
        name="DeepSeek", tier=ProviderTier.ECONOMY,
        base_url="https://api.deepseek.com/v1", api_key_env="DEEPSEEK_API_KEY",
        models=["deepseek-v3", "deepseek-r1"],
        cost_per_1k_input=0.00027, cost_per_1k_output=0.0011, max_context=131072,
        supports_tools=True,
    ),
    # ── Groq (FREE) ────────────────────────────────────────────
    "groq": ProviderConfig(
        name="Groq (Free)", tier=ProviderTier.FREE,
        base_url="https://api.groq.com/openai/v1", api_key_env="GROQ_API_KEY",
        models=["groq-llama-3.3-70b", "groq-llama-3.1-8b", "groq-mixtral-8x7b",
                "groq-gemma2-9b", "groq-llama-3.2-11b"],
        cost_per_1k_input=0.0, cost_per_1k_output=0.0, max_context=131072,
        supports_vision=True,
    ),
    # ── Together AI ─────────────────────────────────────────────
    "together": ProviderConfig(
        name="Together AI", tier=ProviderTier.ECONOMY,
        base_url="https://api.together.xyz/v1", api_key_env="TOGETHER_API_KEY",
        models=["together-llama-3.3-70b", "together-qwen-72b", "together-deepseek-v3"],
        cost_per_1k_input=0.00088, cost_per_1k_output=0.00088, max_context=131072,
    ),
    # ── OpenRouter ──────────────────────────────────────────────
    "openrouter": ProviderConfig(
        name="OpenRouter", tier=ProviderTier.STANDARD,
        base_url="https://openrouter.ai/api/v1", api_key_env="OPENROUTER_API_KEY",
        models=["openrouter-auto", "openrouter-claude-opus", "openrouter-gpt-4o",
                "openrouter-deepseek-r1"],
        cost_per_1k_input=0.005, cost_per_1k_output=0.015, max_context=200000,
    ),
    # ── Mistral ─────────────────────────────────────────────────
    "mistral": ProviderConfig(
        name="Mistral", tier=ProviderTier.STANDARD,
        base_url="https://api.mistral.ai/v1", api_key_env="MISTRAL_API_KEY",
        models=["mistral-large", "mistral-medium", "mistral-small", "codestral"],
        cost_per_1k_input=0.002, cost_per_1k_output=0.006, max_context=128000,
    ),
    # ── xAI ─────────────────────────────────────────────────────
    "xai": ProviderConfig(
        name="xAI (Grok)", tier=ProviderTier.STANDARD,
        base_url="https://api.x.ai/v1", api_key_env="XAI_API_KEY",
        models=["grok-3", "grok-3-mini", "grok-2"],
        cost_per_1k_input=0.003, cost_per_1k_output=0.015, max_context=131072,
        supports_vision=True,
    ),
    # ── Cohere ──────────────────────────────────────────────────
    "cohere": ProviderConfig(
        name="Cohere", tier=ProviderTier.STANDARD,
        base_url="https://api.cohere.com/v2", api_key_env="COHERE_API_KEY",
        models=["command-r-plus", "command-r", "command-r-light"],
        cost_per_1k_input=0.003, cost_per_1k_output=0.015, max_context=128000,
    ),
    # ── AWS Bedrock ─────────────────────────────────────────────
    "bedrock": ProviderConfig(
        name="AWS Bedrock", tier=ProviderTier.FRONTIER,
        base_url="https://bedrock-runtime.us-east-1.amazonaws.com", api_key_env="AWS_ACCESS_KEY_ID",
        models=["bedrock-claude-opus", "bedrock-claude-sonnet", "bedrock-titan"],
        cost_per_1k_input=0.015, cost_per_1k_output=0.075, max_context=200000,
    ),
    # ── Azure OpenAI ────────────────────────────────────────────
    "azure": ProviderConfig(
        name="Azure OpenAI", tier=ProviderTier.FRONTIER,
        base_url="", api_key_env="AZURE_API_KEY",
        models=["azure-gpt-4o", "azure-gpt-4o-mini", "azure-o3-mini"],
        cost_per_1k_input=0.005, cost_per_1k_output=0.015, max_context=128000,
    ),
    # ── Perplexity ──────────────────────────────────────────────
    "perplexity": ProviderConfig(
        name="Perplexity", tier=ProviderTier.SPECIALIZED,
        base_url="https://api.perplexity.ai", api_key_env="PERPLEXITY_API_KEY",
        models=["perplexity-pro", "perplexity-reasoning"],
        cost_per_1k_input=0.003, cost_per_1k_output=0.015, max_context=128000,
    ),
    # ── Alibaba Qwen ────────────────────────────────────────────
    "dashscope": ProviderConfig(
        name="Alibaba Qwen", tier=ProviderTier.STANDARD,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="DASHSCOPE_API_KEY",
        models=["qwen-max", "qwen-plus", "qwen-turbo"],
        cost_per_1k_input=0.002, cost_per_1k_output=0.006, max_context=131072,
    ),
}


# ── Model Aliases ──────────────────────────────────────────────────────
MODEL_ALIASES = {
    # Smart aliases
    "auto":      ("groq", "groq-llama-3.3-70b"),
    "fast":      ("groq", "groq-llama-3.3-70b"),
    "smart":     ("openai", "gpt-5.5-sol"),
    "cheap":     ("deepseek", "deepseek-v3"),
    "free":      ("groq", "groq-llama-3.3-70b"),
    "reasoning": ("anthropic", "claude-opus-4"),
    "code":      ("deepseek", "deepseek-v3"),
    "vision":    ("openai", "gpt-4o"),
    "multilingual": ("gemini", "gemini-2.5-pro"),
    "creative":  ("anthropic", "claude-opus-4"),
    "analysis":  ("openai", "gpt-5.5-sol"),
    "fastest":   ("groq", "groq-llama-3.1-8b"),
    "best":      ("openai", "gpt-5.5-sol"),
    "safest":    ("anthropic", "claude-opus-4"),
    "cheapest":  ("deepseek", "deepseek-v3"),
    "open":      ("together", "together-llama-3.3-70b"),
    "chinese":   ("dashscope", "qwen-max"),
    "korean":    ("gemini", "gemini-2.5-pro"),
    "japanese":  ("openai", "gpt-4o"),
    "arabic":    ("openai", "gpt-4o"),
    "thai":      ("gemini", "gemini-2.5-pro"),
}


class ProviderRouter:
    """
    Smart router that selects the best provider based on:
    - Model alias resolution
    - Provider health
    - Cost optimization
    - Rate limit awareness
    """

    def __init__(self):
        self._health: Dict[str, float] = {}
        self._failures: Dict[str, int] = {}
        self._last_request: Dict[str, float] = {}

    def resolve(self, model: str) -> tuple[str, str]:
        if model in MODEL_ALIASES:
            provider_name, model_id = MODEL_ALIASES[model]
            return provider_name, model_id

        for pname, pconfig in PROVIDERS.items():
            if model in pconfig.models:
                return pname, model

        for pname, pconfig in PROVIDERS.items():
            for m in pconfig.models:
                if model in m:
                    return pname, m

        return "groq", "groq-llama-3.3-70b"

    def should_fallback(self, provider: str) -> bool:
        return self._failures.get(provider, 0) >= 3

    def record_failure(self, provider: str):
        self._failures[provider] = self._failures.get(provider, 0) + 1

    def record_success(self, provider: str):
        self._failures[provider] = 0
        self._health[provider] = time.time()

    def get_healthy_providers(self) -> List[str]:
        return [p for p, f in self._failures.items() if f < 3]

    def suggest_cheapest(self, task_type: str = "general") -> str:
        suggestions = {
            "general": ("groq", "groq-llama-3.3-70b"),
            "complex": ("openai", "gpt-5.5-sol"),
            "code": ("deepseek", "deepseek-v3"),
            "free": ("groq", "groq-llama-3.3-70b"),
            "fast": ("groq", "groq-llama-3.1-8b"),
            "vision": ("openai", "gpt-4o"),
        }
        return suggestions.get(task_type, ("groq", "groq-llama-3.3-70b"))
