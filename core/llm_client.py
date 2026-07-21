#!/usr/bin/env python3
"""
LLM Failover Client - Drop-in replacement with automatic switching
Supports Groq, OpenRouter, OpenAI with seamless failover
"""

import json
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    import httpx
except ImportError:
    httpx = None

try:
    from .failover_router import APIFailoverRouter, ProviderConfig, create_default_router
except ImportError:
    from failover_router import APIFailoverRouter, ProviderConfig, create_default_router


class LLMFailoverClient:
    """
    LLM client with automatic provider failover.
    Drop-in replacement for OpenAI client with failover.
    """
    
    def __init__(self, router: APIFailoverRouter = None):
        self.router = router or create_default_router()
        self.conversation_history: List[Dict] = []
    
    def chat(
        self,
        message: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        keep_history: bool = False
    ) -> Dict:
        """
        Send a chat message with automatic failover.
        
        Args:
            message: User message
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            keep_history: Whether to keep conversation history
        
        Returns:
            Dict with response, provider info, and metadata
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if keep_history and self.conversation_history:
            messages.extend(self.conversation_history)
        
        messages.append({"role": "user", "content": message})
        
        def make_request(provider: ProviderConfig) -> Dict:
            return self._call_provider(provider, messages, temperature, max_tokens)
        
        result = self.router.route_request(make_request)
        
        if "response" in result:
            response = result["response"]
            
            if keep_history:
                self.conversation_history.append({"role": "user", "content": message})
                self.conversation_history.append({"role": "assistant", "content": response.get("content", "")})
            
            return {
                "content": response.get("content", ""),
                "provider": result["provider"],
                "model": result["model"],
                "attempt": result["attempt"],
                "latency": result["latency"],
                "usage": response.get("usage", {})
            }
        
        return result
    
    def _call_provider(
        self,
        provider: ProviderConfig,
        messages: List[Dict],
        temperature: float,
        max_tokens: int
    ) -> Dict:
        """Make an actual API call to a provider."""
        if not httpx:
            raise ImportError("httpx required for API calls")
        
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "CK-NEXUS/0.1.0"
        }
        
        payload = {
            "model": provider.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        with httpx.Client(timeout=provider.timeout) as client:
            resp = client.post(
                f"{provider.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "usage": data.get("usage", {})
                }
            else:
                raise Exception(f"API error {resp.status_code}: {resp.text[:200]}")
    
    def stream(
        self,
        message: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        on_chunk: callable = None
    ) -> Dict:
        """Stream a chat response with failover."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        
        def make_stream_request(provider: ProviderConfig) -> Dict:
            return self._stream_provider(provider, messages, temperature, max_tokens, on_chunk)
        
        return self.router.route_request(make_stream_request)
    
    def _stream_provider(
        self,
        provider: ProviderConfig,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
        on_chunk: callable
    ) -> Dict:
        """Stream from a specific provider."""
        if not httpx:
            raise ImportError("httpx required")
        
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "CK-NEXUS/0.1.0"
        }
        
        payload = {
            "model": provider.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        full_content = ""
        
        with httpx.Client(timeout=provider.timeout) as client:
            with client.stream(
                "POST",
                f"{provider.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as resp:
                if resp.status_code != 200:
                    raise Exception(f"Stream error {resp.status_code}")
                
                for line in resp.iter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            chunk = json.loads(line[6:])
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_content += content
                                if on_chunk:
                                    on_chunk(content)
                        except json.JSONDecodeError:
                            continue
        
        return {"content": full_content}
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def get_stats(self) -> Dict:
        """Get client and router statistics."""
        return {
            "router": self.router.get_stats(),
            "history_length": len(self.conversation_history)
        }


def create_client() -> LLMFailoverClient:
    """Create a failover client with default configuration."""
    return LLMFailoverClient(create_default_router())


if __name__ == "__main__":
    client = create_client()
    
    print("🤖 LLM Failover Client")
    print("=" * 60)
    print(f"   Providers: {list(client.router.providers.keys())}")
    print()
    
    # Test chat
    result = client.chat("Say hello in one sentence")
    
    if "content" in result:
        print(f"   ✅ Response: {result['content'][:100]}...")
        print(f"   📡 Provider: {result['provider']}")
        print(f"   📊 Model: {result['model']}")
        print(f"   ⏱️ Latency: {result['latency']:.2f}s")
        print(f"   🔄 Attempt: {result['attempt']}")
    else:
        print(f"   ❌ Error: {result.get('error', 'Unknown')}")
