"""
CK-NEXUS Kernel Configuration
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path
from enum import Enum
import os
import json


class ConfigSource(Enum):
    """Configuration source types"""
    DEFAULT = "default"
    FILE = "file"
    ENV = "environment"
    CLI = "cli"


@dataclass
class KernelConfig:
    """Main kernel configuration"""
    name: str = "ck-nexus-aios"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    config_dir: str = field(default_factory=lambda: os.path.expanduser("~/.ck-nexus"))
    data_dir: str = field(default_factory=lambda: os.path.expanduser("~/.ck-nexus/data"))
    plugins_dir: str = field(default_factory=lambda: os.path.expanduser("~/.ck-nexus/plugins"))
    logs_dir: str = field(default_factory=lambda: os.path.expanduser("~/.ck-nexus/logs"))
    cache_dir: str = field(default_factory=lambda: os.path.expanduser("~/.ck-nexus/cache"))
    max_workers: int = 10
    request_timeout: float = 30.0
    shutdown_timeout: float = 10.0
    features: Dict[str, bool] = field(default_factory=lambda: {
        "telemetry": True,
        "hot_reload": True,
        "multi_tenant": False,
    })
    services: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        for dir_path in [self.config_dir, self.data_dir, self.plugins_dir, self.logs_dir, self.cache_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_file(cls, path: str) -> "KernelConfig":
        path_obj = Path(path)
        with open(path_obj) as f:
            if path_obj.suffix in ('.yaml', '.yml'):
                import yaml
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "environment": self.environment,
            "debug": self.debug,
            "max_workers": self.max_workers,
            "request_timeout": self.request_timeout,
            "shutdown_timeout": self.shutdown_timeout,
            "features": self.features,
        }

    def get_service_config(self, service_name: str, default: Any = None) -> Any:
        return self.services.get(service_name, default)


class ConfigService:
    """Configuration management service"""

    def __init__(self, config: KernelConfig = None, logger: Any = None):
        self._config = config or KernelConfig()
        self._logger = logger
        self._overrides: Dict[str, Any] = {}
        self._source = ConfigSource.DEFAULT

    @property
    def config(self) -> KernelConfig:
        return self._config

    def load(self, path: str):
        self._config = KernelConfig.from_file(path)
        self._source = ConfigSource.FILE

    def get(self, key: str, default: Any = None) -> Any:
        return self._overrides.get(key, getattr(self._config, key, default))

    def set(self, key: str, value: Any):
        self._overrides[key] = value

    def reload(self):
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {**self._config.to_dict(), **self._overrides}
