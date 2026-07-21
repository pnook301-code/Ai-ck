"""Service Lifetime enumeration"""
from enum import Enum


class ServiceLifetime(Enum):
    """Service lifetime scopes"""
    SINGLETON = "singleton"      # One instance for entire application
    SCOPED = "scoped"            # One instance per scope/request
    TRANSIENT = "transient"      # New instance every time