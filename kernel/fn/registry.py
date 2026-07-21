"""Function Registry - maps function IDs to handlers with semantic search"""
from typing import Any, Callable, Dict, List, Optional, Awaitable
import asyncio
import time
import inspect

from .types import FunctionDefinition, FunctionResult, FunctionStatus, FunctionCategory


FunctionHandler = Callable[..., Awaitable[Any]]


class FunctionRegistry:
    def __init__(self, logger: Any = None):
        self._functions: Dict[str, FunctionDefinition] = {}
        self._history: List[FunctionResult] = []
        self._logger = logger

    @property
    def functions(self) -> Dict[str, FunctionDefinition]:
        return dict(self._functions)

    def register(self, definition: FunctionDefinition):
        self._functions[definition.id] = definition

    def register_handler(self, fn_id: str, handler: FunctionHandler):
        fn = self._functions.get(fn_id)
        if fn:
            fn.handler = handler
        else:
            self._functions[fn_id] = FunctionDefinition(
                id=fn_id, name=fn_id, description="",
                category=FunctionCategory.SYSTEM_CORE,
                handler=handler,
            )

    def get_definition(self, fn_id: str) -> Optional[FunctionDefinition]:
        return self._functions.get(fn_id)

    def list_functions(self, category: FunctionCategory = None) -> List[FunctionDefinition]:
        if category:
            return [f for f in self._functions.values() if f.category == category]
        return list(self._functions.values())

    def find(self, query: str = "", tags: List[str] = None) -> List[FunctionDefinition]:
        results = list(self._functions.values())
        q = query.lower()
        if q:
            results = [
                f for f in results
                if q in f.name.lower() or q in f.description.lower() or q in f.id
            ]
        if tags:
            results = [f for f in results if any(t in f.tags for t in tags)]
        return results

    async def execute(self, fn_id: str, input_data: Dict[str, Any] = None) -> FunctionResult:
        fn = self._functions.get(fn_id)
        if not fn:
            return FunctionResult(
                function_id=fn_id, success=False,
                error=f"Unknown function: {fn_id}",
                status=FunctionStatus.FAILED,
                input=input_data or {},
            )
        if not fn.handler:
            return FunctionResult(
                function_id=fn_id, success=False,
                error=f"No handler registered for: {fn_id}",
                status=FunctionStatus.FAILED,
                input=input_data or {},
            )

        start = time.time()
        result = FunctionResult(
            function_id=fn_id, status=FunctionStatus.RUNNING,
            input=input_data or {},
        )

        try:
            if asyncio.iscoroutinefunction(fn.handler):
                output = await asyncio.wait_for(
                    fn.handler(input_data or {}), timeout=fn.timeout
                )
            else:
                output = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, fn.handler, input_data or {}),
                    timeout=fn.timeout,
                )
            result.output = output
            result.success = True
            result.status = FunctionStatus.SUCCESS
        except asyncio.TimeoutError:
            result.error = f"Function timed out after {fn.timeout}s"
            result.success = False
            result.status = FunctionStatus.TIMEOUT
        except Exception as e:
            result.error = str(e)
            result.success = False
            result.status = FunctionStatus.FAILED

        result.duration_ms = (time.time() - start) * 1000
        self._history.append(result)
        return result

    async def execute_pipeline(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = {}
        context = {}
        for step in steps:
            fn_id = step["fn"]
            params = step.get("params", {})
            condition = step.get("condition")
            if condition and not self._eval_condition(condition, context):
                results[fn_id] = FunctionResult(
                    function_id=fn_id, success=True, status=FunctionStatus.SKIPPED,
                    input=params,
                )
                continue
            merged = {**params, **{k: v for k, v in context.items() if k in params.get("_inherit", [])}}
            result = await self.execute(fn_id, merged)
            results[fn_id] = result
            if result.success:
                context[fn_id] = result.output
            if result.success and step.get("on_success") == "stop":
                break
            if not result.success and step.get("on_fail") == "send_alert":
                if self._logger:
                    self._logger.warning(f"Pipeline step {fn_id} failed: {result.error}")
        return {
            "results": {k: {"success": v.success, "output": v.output, "error": v.error, "duration_ms": v.duration_ms}
                       for k, v in results.items()},
            "final": results.get(steps[-1]["fn"]).output if steps and steps[-1]["fn"] in results else None,
        }

    def _eval_condition(self, condition: str, context: Dict) -> bool:
        try:
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return True

    def get_history(self, limit: int = 10) -> List[FunctionResult]:
        return self._history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._history)
        successful = sum(1 for r in self._history if r.success)
        failed = total - successful
        return {
            "registered": len(self._functions),
            "executions": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
        }
