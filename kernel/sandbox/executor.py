"""Sandbox executor — safely runs generated code in isolated environment"""

import asyncio
import os
import shutil
import tempfile
from typing import Any, Dict


class SandboxExecutor:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def execute(self, code: str, language: str = "python") -> Dict[str, Any]:
        sandbox_dir = tempfile.mkdtemp(prefix="ck_sandbox_")
        try:
            if language == "python":
                result = await self._run_python(code, sandbox_dir)
            else:
                result = {"status": "error", "error": f"Unsupported language: {language}"}
            return result
        finally:
            shutil.rmtree(sandbox_dir, ignore_errors=True)

    async def _run_python(self, code: str, sandbox_dir: str) -> Dict[str, Any]:
        script_path = os.path.join(sandbox_dir, "run.py")
        with open(script_path, "w") as f:
            f.write(code)

        try:
            process = await asyncio.create_subprocess_exec(
                "python", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=sandbox_dir,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout
                )
                return {
                    "status": "success" if process.returncode == 0 else "error",
                    "returncode": process.returncode,
                    "stdout": stdout.decode("utf-8", errors="replace")[:10000],
                    "stderr": stderr.decode("utf-8", errors="replace")[:10000],
                }
            except asyncio.TimeoutError:
                process.kill()
                return {"status": "timeout", "error": f"Execution exceeded {self.timeout}s"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
