"""Bridge module — connects Legit ↔ Shadow / external systems"""

from .shadow_bridge import ShadowBridge, SHADOW_HOME, SHADOW_SCRIPTS

__all__ = ["ShadowBridge", "SHADOW_HOME", "SHADOW_SCRIPTS"]
