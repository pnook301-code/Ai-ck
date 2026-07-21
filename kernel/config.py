"""
CK-NEXUS Kernel Configuration
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path
import os


@dataclass
class KernelConfig:
    """Main kernel configuration"""
    # Runtime
    name: str = "ck-nexus-aios"
    version: str = "1.0.0"
    environment: str = "development"  # development, staging, production
    debug: bool = True
    
    # Paths
    config_dir: str = field(default_factory=lambda: os.path.expanduser("~/.ck-nexus"))
    data_dir: str = field(default_factory=lambda: os.path.expanduser("~/.ck-nexus/data"))
    plugins_dir: str = field(default_factory=lambda: os.path.expanduser("~/.ck-nexus/plugins"))
    logs_dir: str = field(default_factory=lambda: os.path.expanduser("~/.ck-nexus/logs"))
    
    # Runtime
    max_workers: int = 10
    request_timeout: float = 30.0
    shutdown_timeout: float = 10.0
    
    # Feature flags
    features: Dict[str, bool] = field(default_factory=lambda: {
        "telemetry": True,
        "hot_reload": True,
        "plugin_marketplace": False,
        "multi_tenant": False,
    })
    
    # Services config
    services: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Ensure directories exist
        for dir_path in [self.config_dir, self.data_dir, self.plugins_dir, self.logs_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_file(cls, path: str) -> "KernelConfig":
        """Load config from JSON/YAML file"""
        import json
        path_obj = Path(path)
        with open(path_obj) as f:
            if path_obj.suffix in ('.yaml', '.yml'):
                import yaml
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "version": self.version,
            "environment": self.environment,
            "debug": self.debug,
            "config_dir": self.config_dir,
            "data_dir": self.data_dir,
            "plugins_dir": self.plugins_dir,
            "logs_dir": self.logs_dir,
            "max_workers": self.max_workers,
            "request_timeout": self.request_timeout,
            "shutdown_timeout": self.shutdown_timeout,
            "features": self.features,
            "services": self.services,
        }
    
    def get_service_config(self, service_name: str, default: Any = None) -> Any:
        """Get configuration for a specific service"""
        return self.services.get(service_name, default)
    
    def set_service_config(self, service_name: str, config: Dict[str, Any]):
        """Set configuration for a specific service"""
        self.services[service_name] = config