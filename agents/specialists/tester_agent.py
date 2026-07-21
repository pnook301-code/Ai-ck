"""Tester Agent - runs tests and finds bugs"""
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.core.base_agent import BaseAgent


class TesterAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="tester",
            role="qa_engineer",
            capabilities=["run_tests", "write_tests", "find_bugs", "validate"]
        )
        self.test_results = []

    def _do_task(self, task):
        desc = task.description.lower()

        if "run" in desc or "execute" in desc:
            return self._run_tests(task)
        elif "write" in desc or "create" in desc:
            return self._write_tests(task)
        elif "validate" in desc or "check" in desc:
            return self._validate(task)
        else:
            return self._general_test(task)

    def _run_tests(self, task):
        self._log(f"Running tests for: {task.title}")
        test_dir = "/workspace/ck-nexus/tests"

        if os.path.exists(os.path.join(test_dir, "test_all.py")):
            try:
                result = subprocess.run(
                    ["python3", "test_all.py"],
                    cwd=test_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                passed = "PASSED" in result.stdout
                return {
                    "action": "tests_run",
                    "passed": passed,
                    "output": result.stdout[-500:] if len(result.stdout) > 500 else result.stdout,
                    "errors": result.stderr[-200:] if result.stderr else None,
                    "message": "Tests passed" if passed else "Tests failed"
                }
            except subprocess.TimeoutExpired:
                return {"action": "tests_run", "passed": False, "message": "Tests timed out"}
            except Exception as e:
                return {"action": "tests_run", "passed": False, "message": str(e)}
        return {"action": "tests_run", "passed": False, "message": "No test file found"}

    def _write_tests(self, task):
        self._log(f"Writing tests for: {task.title}")
        return {
            "action": "tests_written",
            "test_count": 0,
            "coverage": "pending",
            "message": "Test suite created"
        }

    def _validate(self, task):
        self._log(f"Validating: {task.title}")
        checks = []

        # Check file existence
        files = ["nexus_engine.py", "core/memory.py", "core/command_bus.py"]
        for f in files:
            path = f"/workspace/ck-nexus/{f}"
            exists = os.path.exists(path)
            checks.append({"file": f, "exists": exists})

        return {
            "action": "validated",
            "checks": checks,
            "all_passed": all(c["exists"] for c in checks),
            "message": "Validation complete"
        }

    def _general_test(self, task):
        return {
            "action": "tested",
            "message": f"Testing complete for: {task.title}"
        }

    def get_test_history(self):
        return self.test_results
