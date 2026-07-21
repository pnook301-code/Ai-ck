"""Service Lifetime enumeration"""
from enum import Enum

class ServiceLifetime(Enum):
    """Service lifetime management"""
    TRANSIENT = "transient"      # New instance every time
    SCOPED = "scoped"            # One instance per scope (request)
    SINGLETON = "singleton"      # One instance for entire application