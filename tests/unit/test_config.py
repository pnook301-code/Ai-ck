import json
import pytest
from kernel.config import KernelConfig, ConfigService, ConfigSource


class TestKernelConfig:
    def test_default_values(self):
        cfg = KernelConfig()
        assert cfg.name == "ck-nexus-aios"
        assert cfg.version == "1.0.0"
        assert cfg.environment == "development"
        assert cfg.debug is True
        assert cfg.max_workers == 10

    def test_directories_created(self):
        import tempfile
        base = tempfile.mkdtemp()
        cfg = KernelConfig(
            name="test",
            config_dir=f"{base}/config",
            data_dir=f"{base}/data",
            logs_dir=f"{base}/logs",
        )
        import os
        assert os.path.isdir(f"{base}/config")
        assert os.path.isdir(f"{base}/data")
        assert os.path.isdir(f"{base}/logs")

    def test_to_dict(self):
        cfg = KernelConfig(name="test")
        d = cfg.to_dict()
        assert d["name"] == "test"
        assert d["version"] == "1.0.0"
        assert d["debug"] is True
        assert "features" in d

    def test_get_service_config(self):
        cfg = KernelConfig(services={"db": {"host": "localhost"}})
        assert cfg.get_service_config("db") == {"host": "localhost"}
        assert cfg.get_service_config("missing", "default") == "default"

    def test_from_json_file(self, temp_file):
        data = {"name": "from_file", "debug": False, "max_workers": 5}
        temp_file.write(json.dumps(data))
        temp_file.flush()
        cfg = KernelConfig.from_file(temp_file.name)
        assert cfg.name == "from_file"
        assert cfg.debug is False
        assert cfg.max_workers == 5


class TestConfigService:
    def test_default_config(self):
        svc = ConfigService()
        assert svc.config.name == "ck-nexus-aios"

    def test_get_set(self):
        svc = ConfigService()
        svc.set("max_workers", 20)
        assert svc.get("max_workers") == 20

    def test_get_default(self):
        svc = ConfigService()
        assert svc.get("nonexistent", 42) == 42

    def test_get_falls_back_to_config_attr(self):
        svc = ConfigService()
        assert svc.get("version") == "1.0.0"

    def test_set_overrides_config(self):
        svc = ConfigService()
        svc.set("name", "override")
        assert svc.get("name") == "override"

    def test_to_dict_includes_overrides(self):
        svc = ConfigService()
        svc.set("custom_key", "custom_val")
        d = svc.to_dict()
        assert d["custom_key"] == "custom_val"

    def test_source_default(self):
        svc = ConfigService()
        assert svc._source == ConfigSource.DEFAULT

    def test_reload_noop(self):
        svc = ConfigService()
        svc.reload()

    def test_custom_config(self):
        cfg = KernelConfig(name="custom")
        svc = ConfigService(config=cfg)
        assert svc.config.name == "custom"
