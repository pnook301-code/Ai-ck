"""Offensive Actions & Exploitation — functions 5.1–5.10"""

from typing import Any, Dict
from .types import FunctionDefinition, FunctionResult, FunctionCategory


def _def(name: str, id: str, desc: str, handler, params: dict) -> FunctionDefinition:
    return FunctionDefinition(
        name=name, id=id, description=desc, category=FunctionCategory.OFFENSIVE_ACTIONS,
        input_schema=params, handler=handler,
    )


async def fn_5_1_exploit(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"target": input.get("target"), "cve": input.get("cve"), "exploited": False}

async def fn_5_2_password_spray(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "attempts": len(input.get("usernames", [])), "success": False}

async def fn_5_3_bruteforce(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "attempts": 0, "success": False}

async def fn_5_4_session_hijack(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "vulnerable": False}

async def fn_5_5_file_upload(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "bypass_techniques": []}

async def fn_5_6_lfi_rfi(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "vulnerable": False}

async def fn_5_7_cmd_injection(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "param": input.get("param"), "vulnerable": False}

async def fn_5_8_ssrf(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "vulnerable": False}

async def fn_5_9_idor(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "vulnerable_ids": []}

async def fn_5_10_meterpreter(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"payload_generated": False, "lhost": input.get("lhost"), "lport": input.get("lport", 4444)}


definitions = [
    _def("exploit_exec", "5.1", "Execute known exploit against target", fn_5_1_exploit, {
        "target": {"type": "string", "required": True}, "cve": {"type": "string", "required": True},
    }),
    _def("password_spray", "5.2", "Password spraying attack on login form", fn_5_2_password_spray, {
        "url": {"type": "string", "required": True}, "usernames": {"type": "array", "required": True}, "password": {"type": "string", "required": True},
    }),
    _def("bruteforce", "5.3", "Brute-force login credentials", fn_5_3_bruteforce, {
        "url": {"type": "string", "required": True}, "username": {"type": "string", "required": True}, "wordlist": {"type": "string", "default": "rockyou"}, "rate_limit": {"type": "integer", "default": 5},
    }),
    _def("session_hijack", "5.4", "Test session fixation/hijack", fn_5_4_session_hijack, {
        "url": {"type": "string", "required": True},
    }),
    _def("file_upload_exploit", "5.5", "Test file upload bypass", fn_5_5_file_upload, {
        "url": {"type": "string", "required": True},
    }),
    _def("lfi_rfi", "5.6", "Test local/remote file inclusion", fn_5_6_lfi_rfi, {
        "url": {"type": "string", "required": True}, "params": {"type": "object", "default": {}},
    }),
    _def("command_injection", "5.7", "Test OS command injection", fn_5_7_cmd_injection, {
        "url": {"type": "string", "required": True}, "param": {"type": "string", "required": True},
    }),
    _def("ssrf_test", "5.8", "Test server-side request forgery", fn_5_8_ssrf, {
        "url": {"type": "string", "required": True},
    }),
    _def("idor_test", "5.9", "Test insecure direct object references", fn_5_9_idor, {
        "url": {"type": "string", "required": True}, "ids": {"type": "array", "required": True},
    }),
    _def("meterpreter_reverse", "5.10", "Generate and deploy meterpreter payload", fn_5_10_meterpreter, {
        "lhost": {"type": "string", "required": True}, "lport": {"type": "integer", "default": 4444}, "payload_type": {"type": "string", "default": "python"},
    }),
]


def register_offensive(registry):
    for fn in definitions:
        registry.register(fn)
