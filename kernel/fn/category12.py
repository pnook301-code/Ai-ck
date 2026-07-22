"""Cloud functions — VPS management via provider APIs"""

from typing import Any, Dict


async def fn_12_1_list_providers(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.cloud import CloudOrchestrator
    orch = CloudOrchestrator()
    return {"providers": [p.value for p in orch.configured_providers]}


async def fn_12_2_list_plans(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.cloud import CloudOrchestrator
    orch = CloudOrchestrator()
    plans = await orch.list_all_plans()
    return plans


async def fn_12_3_list_free_plans(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.cloud import CloudOrchestrator
    orch = CloudOrchestrator()
    free = await orch.list_free_plans()
    return {"free_plans": free}


async def fn_12_4_create_vps(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.cloud import CloudOrchestrator, CloudProvider
    orch = CloudOrchestrator()
    provider_name = input_data.get("provider", "oracle")
    provider = CloudProvider(provider_name)
    op = await orch.create_vps(
        provider=provider,
        name=input_data.get("name", "ck-nexus-aios"),
        plan_id=input_data.get("plan_id", ""),
        region=input_data.get("region", ""),
        ssh_public_key=input_data.get("ssh_public_key", ""),
    )
    return op.to_dict() if hasattr(op, "to_dict") else {
        "id": op.id, "status": op.status, "error": op.error,
    }


async def fn_12_5_create_and_deploy(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.cloud import CloudOrchestrator, CloudProvider
    orch = CloudOrchestrator()
    provider_name = input_data.get("provider", "oracle")
    provider = CloudProvider(provider_name)
    op = await orch.create_and_deploy(
        provider=provider,
        name=input_data.get("name", "ck-nexus-aios"),
        plan_id=input_data.get("plan_id", ""),
        region=input_data.get("region", ""),
        ssh_public_key=input_data.get("ssh_public_key", ""),
    )
    return {
        "id": op.id, "status": op.status, "error": op.error,
        "logs": op.logs,
        "server": op.server.to_dict() if op.server else None,
    }


async def fn_12_6_delete_vps(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.cloud import CloudOrchestrator, CloudProvider
    orch = CloudOrchestrator()
    provider = CloudProvider(input_data.get("provider", "oracle"))
    server_id = input_data.get("server_id", "")
    ok = await orch.delete_vps(provider, server_id)
    return {"deleted": ok, "server_id": server_id}


async def fn_12_7_server_status(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.cloud import CloudOrchestrator, CloudProvider
    orch = CloudOrchestrator()
    provider = CloudProvider(input_data.get("provider", "oracle"))
    server_id = input_data.get("server_id", "")
    server = await orch.get_server_status(provider, server_id)
    return server.to_dict() if server else {"error": "not found"}


async def fn_12_8_list_servers(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.cloud import CloudOrchestrator
    orch = CloudOrchestrator()
    servers = await orch.list_all_servers()
    return servers


async def fn_12_9_get_recommendation(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.cloud import CloudOrchestrator
    orch = CloudOrchestrator()
    return orch.get_recommendation()


async def fn_12_10_cloud_status(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.cloud import CloudOrchestrator
    orch = CloudOrchestrator()
    return orch.get_status()


def _def(name, fn_id, desc, handler, params):
    from kernel.fn.types import FunctionDefinition, FunctionCategory
    return FunctionDefinition(
        id=fn_id, name=name, description=desc,
        category=FunctionCategory.CLOUD,
        handler=handler, input_schema=params,
    )


definitions = [
    _def("cloud_list_providers", "12.1",
         "List configured cloud providers",
         fn_12_1_list_providers, {}),
    _def("cloud_list_plans", "12.2",
         "List all VPS plans from configured providers",
         fn_12_2_list_plans, {
             "provider": {"type": "string", "default": ""},
         }),
    _def("cloud_list_free_plans", "12.3",
         "List free tier plans from all providers",
         fn_12_3_list_free_plans, {}),
    _def("cloud_create_vps", "12.4",
         "Create a VPS on specified provider",
         fn_12_4_create_vps, {
             "provider": {"type": "string", "required": True},
             "name": {"type": "string", "default": "ck-nexus-aios"},
             "plan_id": {"type": "string", "default": ""},
             "region": {"type": "string", "default": ""},
             "ssh_public_key": {"type": "string", "default": ""},
         }),
    _def("cloud_create_and_deploy", "12.5",
         "One-click: Create VPS + install CK-NEXUS automatically",
         fn_12_5_create_and_deploy, {
             "provider": {"type": "string", "required": True},
             "name": {"type": "string", "default": "ck-nexus-aios"},
             "plan_id": {"type": "string", "default": ""},
             "region": {"type": "string", "default": ""},
             "ssh_public_key": {"type": "string", "default": ""},
         }),
    _def("cloud_delete_vps", "12.6",
         "Delete a VPS server",
         fn_12_6_delete_vps, {
             "provider": {"type": "string", "required": True},
             "server_id": {"type": "string", "required": True},
         }),
    _def("cloud_server_status", "12.7",
         "Get VPS server status",
         fn_12_7_server_status, {
             "provider": {"type": "string", "required": True},
             "server_id": {"type": "string", "required": True},
         }),
    _def("cloud_list_servers", "12.8",
         "List all servers from all providers",
         fn_12_8_list_servers, {}),
    _def("cloud_recommend", "12.9",
         "Get best provider recommendation",
         fn_12_9_get_recommendation, {}),
    _def("cloud_status", "12.10",
         "Get cloud module status",
         fn_12_10_cloud_status, {}),
]


def register_cloud(registry):
    for fn in definitions:
        registry.register(fn)
