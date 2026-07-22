"""CK-NEXUS AIOS — FastAPI Backend Server."""
import time
import json
import os
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="CK-NEXUS AIOS",
    description="Enterprise AI Operating System — 142 Functions, Multi-tenant, Full Observability",
    version="1.0.0",
)

_start_time = time.time()

_registry = None
_tenant_mgr = None
_audit_log = None
_license_mgr = None


def _get_registry():
    global _registry
    if _registry is None:
        from kernel.fn import FunctionRegistry, register_all_categories
        _registry = FunctionRegistry()
        register_all_categories(_registry)
    return _registry


def _get_tenant():
    global _tenant_mgr
    if _tenant_mgr is None:
        from kernel.enterprise.tenant import TenantManager
        _tenant_mgr = TenantManager()
    return _tenant_mgr


def _get_audit():
    global _audit_log
    if _audit_log is None:
        from kernel.enterprise.audit import AuditLogger
        _audit_log = AuditLogger()
    return _audit_log


def _get_license():
    global _license_mgr
    if _license_mgr is None:
        from kernel.enterprise.license import LicenseManager
        _license_mgr = LicenseManager()
    return _license_mgr


class FunctionCallRequest(BaseModel):
    function_id: str
    input_data: Dict[str, Any] = {}


class ChatRequest(BaseModel):
    message: str
    tenant_id: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "ok", "uptime": round(time.time() - _start_time, 1), "version": "1.0.0"}


@app.get("/api/stats")
async def stats():
    reg = _get_registry()
    func_stats = reg.get_stats()
    return {
        "functions": func_stats,
        "tenants": _get_tenant().get_stats(),
        "audit": _get_audit().get_stats(),
        "licenses": _get_license().get_stats(),
        "uptime": round(time.time() - _start_time, 1),
    }


@app.get("/api/functions")
async def list_functions(category: Optional[str] = None):
    reg = _get_registry()
    fns = reg.list_functions()
    result = []
    for fn in fns:
        if category and fn.category.value != category:
            continue
        result.append({
            "id": fn.id, "name": fn.name, "description": fn.description,
            "category": fn.category.value, "input_schema": fn.input_schema,
        })
    return {"functions": result, "count": len(result)}


@app.post("/api/functions/execute")
async def execute_function(req: FunctionCallRequest):
    reg = _get_registry()
    fn_def = reg.get_definition(req.function_id)
    if not fn_def:
        raise HTTPException(status_code=404, detail=f"Function {req.function_id} not found")
    result = await reg.execute(req.function_id, req.input_data)
    return {"success": result.success, "output": result.output, "error": result.error, "duration_ms": result.duration_ms}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    msg = req.message.lower().strip()
    reg = _get_registry()
    from kernel.enterprise.audit import AuditAction
    _get_audit().log(AuditAction.API_CALL, details={"message": req.message[:100]})

    if any(w in msg for w in ["status", "health", "how are you"]):
        func_stats = reg.get_stats()
        uptime = round(time.time() - _start_time, 1)
        return {"reply": f"CK-NEXUS AIOS is healthy. {func_stats['registered']} functions loaded. Uptime: {uptime}s.", "type": "system"}

    if "help" in msg:
        cats = {}
        for fn in reg.list_functions():
            cats.setdefault(fn.category.value, []).append(fn.name)
        summary = "\n".join([f"  {cat}: {len(fns)} functions" for cat, fns in sorted(cats.items())])
        total = reg.get_stats()["registered"]
        return {"reply": f"Available categories:\n{summary}\n\nTotal: {total} functions across {len(cats)} categories.", "type": "info"}

    if "tenant" in msg and "create" in msg:
        tenant = _get_tenant().create_tenant("Web User Tenant")
        return {"reply": f"Tenant created: {tenant.id} ({tenant.name}, plan: {tenant.plan.value})", "type": "success"}

    if "tenant" in msg and ("list" in msg or "show" in msg):
        tenants = _get_tenant().list_tenants()
        if not tenants:
            return {"reply": "No tenants found. Create one with 'create tenant'.", "type": "info"}
        lines = [f"  {t.id}: {t.name} ({t.plan.value}, {t.status.value})" for t in tenants]
        return {"reply": f"Tenants:\n" + "\n".join(lines), "type": "info"}

    if "license" in msg and "generate" in msg:
        from kernel.enterprise.license import LicenseTier
        tenants = _get_tenant().list_tenants()
        if not tenants:
            return {"reply": "No tenants. Create a tenant first.", "type": "warning"}
        lic = _get_license().generate_license(tenants[0].id, LicenseTier.PROFESSIONAL, duration_days=30)
        return {"reply": f"License generated:\nKey: {lic.key}\nTier: {lic.tier.value}\nFeatures: {', '.join(lic.features)}", "type": "success"}

    if "audit" in msg:
        events = _get_audit().query(limit=5)
        if not events:
            return {"reply": "No audit events yet.", "type": "info"}
        lines = [f"  [{e.action.value}] {e.severity.value}" for e in events]
        return {"reply": f"Recent audit events:\n" + "\n".join(lines), "type": "info"}

    if "function" in msg or "category" in msg or "list" in msg:
        cats = {}
        for fn in reg.list_functions():
            cats.setdefault(fn.category.value, []).append(fn.id + " " + fn.name)
        parts = []
        for cat, fns in sorted(cats.items()):
            parts.append(f"\n  {cat.upper()} ({len(fns)}):")
            for f in fns[:5]:
                parts.append(f"     {f}")
            if len(fns) > 5:
                parts.append(f"     ... +{len(fns) - 5} more")
        return {"reply": "Function Registry:\n" + "\n".join(parts), "type": "info"}

    return {"reply": f"I understand '{req.message}'.\n\nCommands:\n  status     - System health\n  help       - Show all commands\n  create tenant - Create new tenant\n  list tenants  - Show all tenants\n  generate license - Create license key\n  audit      - Show audit events\n  functions  - List all functions\n\nOr use /api/functions/execute to call any function directly.", "type": "assistant"}


@app.get("/api/knowledge")
async def knowledge_stats():
    kg_path = os.path.join(BASE_DIR, "knowledge", "global_ai_research.json")
    if os.path.exists(kg_path):
        with open(kg_path) as f:
            data = json.load(f)
        entities = data.get("entities", {})
        relations = data.get("relations", {})
        types = {}
        for e_id, e_data in entities.items():
            if isinstance(e_data, dict):
                t = e_data.get("type", "unknown")
            else:
                t = "unknown"
            types[t] = types.get(t, 0) + 1
        return {"entities": len(entities), "relations": len(relations), "entity_types": types}
    return {"entities": 0, "relations": 0, "entity_types": {}}


@app.get("/api/observability")
async def observability():
    return {"metrics": "Prometheus ready", "logs": "Structured JSON logging", "tracing": "Distributed tracing", "alerts": "Rule engine active"}


@app.get("/api/cloud")
async def cloud_info():
    return {"providers": ["Hetzner", "DigitalOcean", "AWS", "GCP", "Oracle"], "functions": 10, "one_click_deploy": True}


@app.get("/api/kubernetes")
async def k8s_info():
    return {"resources": ["Deployment", "Service", "Ingress", "HPA", "PDB", "Namespace", "ConfigMap", "Secret"], "helm": True, "functions": 12}


web_dir = os.path.join(BASE_DIR, "web")
if os.path.isdir(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/", response_class=FileResponse)
    async def serve_index():
        return os.path.join(web_dir, "index.html")

    @app.get("/app", response_class=FileResponse)
    async def serve_app():
        return os.path.join(web_dir, "app.html")
