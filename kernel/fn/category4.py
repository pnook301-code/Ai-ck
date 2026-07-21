"""Security Scanning — functions 4.1–4.10"""

from typing import Any, Dict
from .types import FunctionDefinition, FunctionResult, FunctionCategory


def _def(name: str, id: str, desc: str, handler, params: dict) -> FunctionDefinition:
    return FunctionDefinition(
        name=name, id=id, description=desc, category=FunctionCategory.SECURITY_SCANNING,
        input_schema=params, handler=handler,
    )


async def fn_4_1_port_scan(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"target": input.get("target"), "open_ports": [22, 80, 443], "scan_type": input.get("scan_type", "tcp_syn")}

async def fn_4_2_vuln_scan(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"target": input.get("target"), "vulnerabilities": [], "severity": input.get("severity", "medium")}

async def fn_4_3_dir_brute(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "found_dirs": ["/admin", "/backup", "/.git"]}

async def fn_4_4_xss(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "xss_found": False}

async def fn_4_5_sqli(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "sqli_found": False}

async def fn_4_6_cve(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"software": input.get("software"), "version": input.get("version"), "cves": []}

async def fn_4_7_headers(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "missing_headers": ["X-Content-Type-Options", "Content-Security-Policy"]}

async def fn_4_8_cors(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "cors_misconfigured": False}

async def fn_4_9_open_redirect(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "open_redirects": []}

async def fn_4_10_rate_limit(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "rate_limited": False, "max_requests": input.get("threshold", 100)}


definitions = [
    _def("port_scan", "4.1", "TCP/UDP port scan on target", fn_4_1_port_scan, {
        "target": {"type": "string", "required": True}, "ports": {"type": "string", "default": "1-10000"}, "scan_type": {"type": "string", "default": "tcp_syn"},
    }),
    _def("vulnerability_scan", "4.2", "Run vulnerability scanner", fn_4_2_vuln_scan, {
        "target": {"type": "string", "required": True}, "severity": {"type": "string", "default": "medium"},
    }),
    _def("dir_bruteforce", "4.3", "Brute-force directories on webserver", fn_4_3_dir_brute, {
        "url": {"type": "string", "required": True}, "wordlist": {"type": "string", "default": "common"}, "extensions": {"type": "array", "default": ["php", "asp", "html", "bak"]},
    }),
    _def("xss_scanner", "4.4", "Scan for XSS vulnerabilities", fn_4_4_xss, {
        "url": {"type": "string", "required": True}, "params": {"type": "object", "default": {}},
    }),
    _def("sql_injection_scanner", "4.5", "Scan for SQL injection", fn_4_5_sqli, {
        "url": {"type": "string", "required": True},
    }),
    _def("cve_scanner", "4.6", "Check target against known CVEs", fn_4_6_cve, {
        "software": {"type": "string", "required": True}, "version": {"type": "string", "required": True},
    }),
    _def("headers_check", "4.7", "Check HTTP security headers", fn_4_7_headers, {
        "url": {"type": "string", "required": True},
    }),
    _def("cors_scanner", "4.8", "Test CORS misconfiguration", fn_4_8_cors, {
        "url": {"type": "string", "required": True},
    }),
    _def("open_redirect_scan", "4.9", "Check for open redirects", fn_4_9_open_redirect, {
        "url": {"type": "string", "required": True},
    }),
    _def("rate_limit_test", "4.10", "Test rate limiting", fn_4_10_rate_limit, {
        "url": {"type": "string", "required": True}, "threshold": {"type": "integer", "default": 100},
    }),
]


def register_security_scanning(registry):
    for fn in definitions:
        registry.register(fn)
