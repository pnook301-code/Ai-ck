#!/usr/bin/env python3
"""
API Failover System - Automatic provider switching for CK-NEXUS
Circuit breaker, health checks, and multi-provider routing
"""

import time
import json
import random
import threading
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, skip
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class ProviderConfig:
    """Configuration for a single provider."""
    name: str
    api_key: str
    base_url: str
    model: str
    priority: int = 0
    cost_per_token: float = 0.0
    enabled: bool = True
    max_retries: int = 3
    timeout: float = 30.0


@dataclass
class CircuitBreaker:
    """Circuit breaker for a single provider."""
    failure_threshold: int = 3
    recovery_timeout: float = 30.0
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0
    success_count: int = 0
    total_requests: int = 0
    total_failures: int = 0
    
    def record_success(self):
        self.total_requests += 1
        self.success_count += 1
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
    
    def record_failure(self):
        self.total_requests += 1
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def should_try(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def get_stats(self) -> Dict:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "success_rate": (self.success_count / self.total_requests * 100) if self.total_requests > 0 else 0
        }


class APIFailoverRouter:
    """
    Automatic API failover router with circuit breaker pattern.
    Routes requests across multiple providers with automatic switching.
    """
    
    def __init__(self, providers: List[ProviderConfig] = None, config_path: str = None):
        self.providers: Dict[str, ProviderConfig] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.request_log: List[Dict] = []
        self.lock = threading.Lock()
        self.current_index = 0
        
        if providers:
            for p in providers:
                self.add_provider(p)
        
        if config_path:
            self.load_config(config_path)
    
    def add_provider(self, provider: ProviderConfig):
        """Add a provider to the router."""
        self.providers[provider.name] = provider
        self.circuit_breakers[provider.name] = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30.0
        )
    
    def remove_provider(self, name: str):
        """Remove a provider from the router."""
        self.providers.pop(name, None)
        self.circuit_breakers.pop(name, None)
    
    def get_available_providers(self) -> List[ProviderConfig]:
        """Get providers that are enabled and circuit breaker is not open."""
        available = []
        for name, provider in self.providers.items():
            if provider.enabled and self.circuit_breakers[name].should_try():
                available.append(provider)
        return sorted(available, key=lambda p: p.priority)
    
    def get_next_provider(self) -> Optional[ProviderConfig]:
        """Get the next provider using round-robin with priority fallback."""
        available = self.get_available_providers()
        if not available:
            return None
        
        with self.lock:
            self.current_index = self.current_index % len(available)
            provider = available[self.current_index]
            self.current_index = (self.current_index + 1) % len(available)
        
        return provider
    
    def route_request(self, request_func: Callable, *args, **kwargs) -> Dict:
        """
        Route a request through available providers with automatic failover.
        
        Args:
            request_func: Function that takes provider and makes the API call
            *args, **kwargs: Arguments to pass to the request function
        
        Returns:
            Dict with response and metadata
        """
        attempted = []
        last_error = None
        
        for attempt in range(len(self.providers)):
            provider = self.get_next_provider()
            if not provider:
                break
            
            attempted.append(provider.name)
            start_time = time.time()
            
            try:
                result = request_func(provider, *args, **kwargs)
                latency = time.time() - start_time
                
                self.circuit_breakers[provider.name].record_success()
                
                self._log_request({
                    "provider": provider.name,
                    "model": provider.model,
                    "status": "success",
                    "latency": latency,
                    "attempt": len(attempted),
                    "attempted": attempted
                })
                
                return {
                    "response": result,
                    "provider": provider.name,
                    "model": provider.model,
                    "attempt": len(attempted),
                    "latency": latency,
                    "attempted": attempted
                }
            
            except Exception as e:
                latency = time.time() - start_time
                last_error = str(e)
                
                self.circuit_breakers[provider.name].record_failure()
                
                self._log_request({
                    "provider": provider.name,
                    "model": provider.model,
                    "status": "failed",
                    "error": last_error,
                    "latency": latency,
                    "attempt": len(attempted),
                    "attempted": attempted
                })
                
                continue
        
        return {
            "error": f"All providers failed. Attempted: {attempted}",
            "last_error": last_error,
            "attempted": attempted
        }
    
    def _log_request(self, log_entry: Dict):
        log_entry["timestamp"] = time.time()
        self.request_log.append(log_entry)
        if len(self.request_log) > 1000:
            self.request_log = self.request_log[-500:]
    
    def get_stats(self) -> Dict:
        """Get router statistics."""
        provider_stats = {}
        for name in self.providers:
            provider_stats[name] = {
                "config": {
                    "priority": self.providers[name].priority,
                    "model": self.providers[name].model,
                    "enabled": self.providers[name].enabled
                },
                "circuit": self.circuit_breakers[name].get_stats()
            }
        
        recent = self.request_log[-100:] if self.request_log else []
        success_rate = sum(1 for r in recent if r["status"] == "success") / len(recent) * 100 if recent else 0
        
        return {
            "providers": provider_stats,
            "available": [p.name for p in self.get_available_providers()],
            "recent_requests": len(recent),
            "recent_success_rate": success_rate,
            "total_requests": len(self.request_log)
        }
    
    def health_check(self) -> Dict:
        """Check health of all providers."""
        health = {}
        for name, provider in self.providers.items():
            cb = self.circuit_breakers[name]
            health[name] = {
                "enabled": provider.enabled,
                "circuit_state": cb.state.value,
                "can_accept": cb.should_try(),
                "failure_count": cb.failure_count,
                "success_rate": cb.get_stats()["success_rate"]
            }
        return health
    
    def load_config(self, config_path: str):
        """Load configuration from JSON file."""
        try:
            with open(config_path) as f:
                config = json.load(f)
            
            # Support both flat and nested config
            providers_data = config.get("providers", config)
            
            for name, p in providers_data.items():
                if not isinstance(p, dict):
                    continue
                # Skip entries without API key or base_url (like LINE config)
                api_key = p.get("key", "")
                base_url = p.get("base_url", "")
                if not api_key and not base_url:
                    continue
                
                provider = ProviderConfig(
                    name=name,
                    api_key=api_key,
                    base_url=base_url,
                    model=p.get("model", ""),
                    priority=p.get("priority", 0),
                    cost_per_token=p.get("cost_per_token", 0),
                    enabled=p.get("enabled", True)
                )
                self.add_provider(provider)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def save_config(self, config_path: str):
        """Save configuration to JSON file."""
        providers = []
        for name, p in self.providers.items():
            providers.append({
                "name": p.name,
                "api_key": p.api_key,
                "base_url": p.base_url,
                "model": p.model,
                "priority": p.priority,
                "cost_per_token": p.cost_per_token,
                "enabled": p.enabled
            })
        
        with open(config_path, 'w') as f:
            json.dump({"providers": providers}, f, indent=2)


def create_default_router() -> APIFailoverRouter:
    """Create a router with default CK-NEXUS providers."""
    router = APIFailoverRouter()
    
    # Load from config if exists
    config_path = Path.home() / ".ck-nexus" / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
            
            providers = config.get("providers", config)
            
            if "groq" in providers and providers["groq"].get("key"):
                router.add_provider(ProviderConfig(
                    name="groq",
                    api_key=providers["groq"]["key"],
                    base_url=providers["groq"].get("base_url", "https://api.groq.com/openai/v1"),
                    model=providers["groq"].get("model", "llama-3.3-70b-versatile"),
                    priority=0
                ))
            
            if "openrouter" in providers and providers["openrouter"].get("key"):
                router.add_provider(ProviderConfig(
                    name="openrouter",
                    api_key=providers["openrouter"]["key"],
                    base_url=providers["openrouter"].get("base_url", "https://openrouter.ai/api/v1"),
                    model=providers["openrouter"].get("model", "meta-llama/llama-3.3-70b-versatile:free"),
                    priority=1
                ))
            
            if "openai" in providers and providers["openai"].get("key"):
                router.add_provider(ProviderConfig(
                    name="openai",
                    api_key=providers["openai"]["key"],
                    base_url=providers["openai"].get("base_url", "https://api.openai.com/v1"),
                    model=providers["openai"].get("model", "gpt-4"),
                    priority=2
                ))
        
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
    
    if not router.providers:
        router.add_provider(ProviderConfig(
            name="groq",
            api_key="",
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile",
            priority=0
        ))
    
    return router


if __name__ == "__main__":
    router = create_default_router()
    
    print("🔄 API Failover Router")
    print("=" * 60)
    print(f"   Providers: {list(router.providers.keys())}")
    print(f"   Available: {[p.name for p in router.get_available_providers()]}")
    print()
    
    stats = router.get_stats()
    for name, info in stats["providers"].items():
        cb = info["circuit"]
        print(f"   📡 {name}:")
        print(f"      Priority: {info['config']['priority']}")
        print(f"      Model: {info['config']['model']}")
        print(f"      Circuit: {cb['state']}")
        print(f"      Success Rate: {cb['success_rate']:.1f}%")
