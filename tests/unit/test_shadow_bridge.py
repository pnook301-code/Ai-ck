"""Tests for Shadow Bridge module"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


SHADOW_HOME = os.environ.get("CK_SHADOW_HOME", "/opt/ck-nexus-aios")
skip_if_no_shadow = pytest.mark.skipif(
    not Path(SHADOW_HOME).exists(),
    reason=f"Shadow system not found at {SHADOW_HOME}"
)


class TestShadowBridge:
    def test_import(self):
        from kernel.bridge import ShadowBridge
        assert ShadowBridge is not None

    def test_list_scripts(self):
        from kernel.bridge.shadow_bridge import ShadowBridge, SHADOW_SCRIPTS
        bridge = ShadowBridge()
        scripts = bridge.list_scripts()
        assert len(scripts) >= 10
        assert "nexus_cli" in scripts
        assert "api_key_gen" in scripts

    def test_resolve_script(self):
        from kernel.bridge.shadow_bridge import ShadowBridge
        bridge = ShadowBridge(shadow_home="/tmp")
        script = bridge._resolve_script("nexus_cli")
        assert script is not None
        assert script.name == "nexus_cli.py"
        unknown = bridge._resolve_script("nonexistent")
        assert unknown is None

    def test_status(self):
        from kernel.bridge.shadow_bridge import ShadowBridge
        bridge = ShadowBridge()
        status = bridge.get_status()
        assert "shadow_home" in status
        assert status["scripts_available"] >= 10

    @skip_if_no_shadow
    @pytest.mark.asyncio
    async def test_connect_local(self):
        from kernel.bridge.shadow_bridge import ShadowBridge
        bridge = ShadowBridge()
        connected = await bridge.connect()
        assert connected is True

    @skip_if_no_shadow
    @pytest.mark.asyncio
    async def test_execute_script(self):
        from kernel.bridge.shadow_bridge import ShadowBridge
        bridge = ShadowBridge()
        await bridge.connect()
        result = await bridge.execute("api_key_gen", args=["--help"])
        assert "success" in result

    def test_ssh_config_disabled(self):
        from kernel.bridge.shadow_bridge import ShadowBridge
        bridge = ShadowBridge(ssh_config={"host": "192.168.1.100"})
        assert bridge._ssh_config is not None

    @pytest.mark.asyncio
    async def test_connect_ssh_disabled(self):
        from kernel.bridge.shadow_bridge import ShadowBridge
        bridge = ShadowBridge(ssh_config={"host": "remote"})
        connected = await bridge.connect()
        assert connected is False


class TestShadowFunctions:
    @pytest.mark.asyncio
    async def test_execute_unknown_script(self):
        from kernel.bridge.shadow_bridge import ShadowBridge
        bridge = ShadowBridge()
        result = await bridge.execute("nonexistent_script")
        assert result["success"] is False
        assert "Unknown" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        from kernel.bridge.shadow_bridge import ShadowBridge
        bridge = ShadowBridge()
        result = await bridge.execute("nonexistent")
        assert result["success"] is False
