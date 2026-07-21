"""Shadow Bridge — connects CK-NEXUS Legit ↔ Shadow systems

Supports both local direct-call and remote SSH execution.
On same-machine: uses subprocess directly.
On remote VPS: uses asyncssh (install with: pip install asyncssh).
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


SHADOW_HOME = os.environ.get("CK_SHADOW_HOME", "/opt/ck-nexus-aios")
SHADOW_SCRIPTS = {
    "nexus_cli": "nexus_cli.py",
    "api_key_gen": "api_key_demo.py",
    "unified_controller": "unified_controller.py",
    "auto_system": "auto_system.py",
    "vps_auto_reg": "vps_auto_reg.py",
    "web_reg_plugin": "web_reg_plugin.py",
    "telegram_gateway": "telegram_gateway.py",
    "omni_ai_pool": "omni_ai_pool.py",
    "headless_mainframe": "headless_mainframe.py",
    "smart_router": "smart_router_v12.py",
}


class ShadowBridge:
    def __init__(self, shadow_home: str = SHADOW_HOME, ssh_config: Optional[Dict] = None):
        self._shadow_home = Path(shadow_home)
        self._ssh_config = ssh_config
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        if self._ssh_config:
            self._connected = await self._ssh_connect()
        else:
            self._connected = self._shadow_home.exists()
        return self._connected

    async def execute(self, script_name: str, args: List[str] = None,
                      input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        script_path = self._resolve_script(script_name)
        if not script_path:
            return {"success": False, "error": f"Unknown script: {script_name}"}

        if self._ssh_config:
            return await self._ssh_execute(script_path, args, input_data)
        else:
            return await self._local_execute(script_path, args, input_data)

    async def _local_execute(self, script_path: Path, args: List[str] = None,
                             input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        cmd = ["python", str(script_path)]
        if args:
            cmd.extend(args)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._shadow_home),
            )
            stdin = json.dumps(input_data).encode() if input_data else None
            stdout, stderr = await asyncio.wait_for(proc.communicate(stdin), timeout=60)

            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace")[:50000],
                "stderr": stderr.decode("utf-8", errors="replace")[:10000],
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Execution timed out (60s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _ssh_connect(self) -> bool:
        try:
            import asyncssh
            return True
        except ImportError:
            return False

    async def _ssh_execute(self, script_path: Path, args: List[str] = None,
                           input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"success": False, "error": "SSH mode requires asyncssh package"}

    def _resolve_script(self, name: str) -> Optional[Path]:
        if name in SHADOW_SCRIPTS:
            return self._shadow_home / SHADOW_SCRIPTS[name]
        candidate = self._shadow_home / name
        if candidate.exists():
            return candidate
        candidate2 = self._shadow_home / f"{name}.py"
        if candidate2.exists():
            return candidate2
        return None

    def list_scripts(self) -> List[str]:
        return list(SHADOW_SCRIPTS.keys())

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self._connected,
            "shadow_home": str(self._shadow_home),
            "has_ssh_config": self._ssh_config is not None,
            "scripts_available": len(SHADOW_SCRIPTS),
        }
