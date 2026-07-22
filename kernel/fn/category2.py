"""Input Gateways — functions 2.1–2.10"""

from typing import Any, Dict
from .types import FunctionDefinition, FunctionCategory


def _def(name: str, id: str, desc: str, handler, params: dict) -> FunctionDefinition:
    return FunctionDefinition(
        name=name, id=id, description=desc, category=FunctionCategory.INPUT_GATEWAYS,
        input_schema=params, handler=handler,
    )


async def fn_2_1_url_input(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"received": True, "url": input.get("url"), "depth": input.get("depth", 0)}

async def fn_2_2_domain_input(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"domain": input.get("domain")}

async def fn_2_3_ip_input(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"ip": input.get("ip"), "port_range": input.get("port_range", "1-1024")}

async def fn_2_4_file_input(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"file_url": input.get("file_url"), "file_type": input.get("file_type", "auto")}

async def fn_2_5_bulk_url(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"urls": input.get("urls", []), "concurrency": input.get("concurrency", 5)}

async def fn_2_6_cidr_input(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"cidr": input.get("cidr")}

async def fn_2_7_email_input(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"email": input.get("email")}

async def fn_2_8_hash_input(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"hash": input.get("hash"), "hash_type": input.get("hash_type", "auto")}

async def fn_2_9_query_input(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"query": input.get("query")}

async def fn_2_10_webhook_input(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"webhook_url": input.get("webhook_url"), "configured": True}


definitions = [
    _def("url_input", "2.1", "Submit URL for processing", fn_2_1_url_input, {
        "url": {"type": "string", "required": True}, "depth": {"type": "integer", "default": 0},
    }),
    _def("domain_input", "2.2", "Submit domain for analysis", fn_2_2_domain_input, {
        "domain": {"type": "string", "required": True},
    }),
    _def("ip_input", "2.3", "Submit IP address for scanning", fn_2_3_ip_input, {
        "ip": {"type": "string", "required": True}, "port_range": {"type": "string", "default": "1-1024"},
    }),
    _def("file_input_gateway", "2.4", "Upload or provide file URL for processing", fn_2_4_file_input, {
        "file_url": {"type": "string", "required": True}, "file_type": {"type": "string", "default": "auto"},
    }),
    _def("bulk_url_input", "2.5", "Submit list of URLs for batch processing", fn_2_5_bulk_url, {
        "urls": {"type": "array", "required": True}, "concurrency": {"type": "integer", "default": 5},
    }),
    _def("cidr_input", "2.6", "Submit CIDR range for network scan", fn_2_6_cidr_input, {
        "cidr": {"type": "string", "required": True},
    }),
    _def("email_input", "2.7", "Submit email address for analysis", fn_2_7_email_input, {
        "email": {"type": "string", "required": True},
    }),
    _def("hash_input", "2.8", "Submit file hash for lookup", fn_2_8_hash_input, {
        "hash": {"type": "string", "required": True}, "hash_type": {"type": "string", "default": "auto"},
    }),
    _def("query_input", "2.9", "Submit natural language query", fn_2_9_query_input, {
        "query": {"type": "string", "required": True},
    }),
    _def("webhook_input", "2.10", "Configure webhook listener for external triggers", fn_2_10_webhook_input, {
        "webhook_url": {"type": "string", "required": True}, "secret": {"type": "string", "default": ""},
    }),
]


def register_input_gateways(registry):
    for fn in definitions:
        registry.register(fn)
