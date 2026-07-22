"""OSINT & Reconnaissance — functions 3.1–3.10"""

from typing import Any, Dict
from .types import FunctionDefinition, FunctionCategory


def _def(name: str, id: str, desc: str, handler, params: dict) -> FunctionDefinition:
    return FunctionDefinition(
        name=name, id=id, description=desc, category=FunctionCategory.OSINT,
        input_schema=params, handler=handler,
    )


async def fn_3_1_whois(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"target": input.get("target")}

async def fn_3_2_dns_enum(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"domain": input.get("domain"), "records": ["A", "MX", "NS", "TXT"]}

async def fn_3_3_subdomain(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"domain": input.get("domain"), "wordlist": input.get("wordlist", "common")}

async def fn_3_4_ssl_cert(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"host": input.get("host"), "port": input.get("port", 443)}

async def fn_3_5_tech_detect(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "tech_stack": ["nginx", "react", "python"]}

async def fn_3_6_email_osint(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"email": input.get("email")}

async def fn_3_7_social_search(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"username": input.get("username")}

async def fn_3_8_breach_check(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"email": input.get("email"), "breaches": []}

async def fn_3_9_ip_geo(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"ip": input.get("ip")}

async def fn_3_10_shodan(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"query": input.get("query")}


definitions = [
    _def("whois_lookup", "3.1", "Perform WHOIS lookup on domain/IP", fn_3_1_whois, {
        "target": {"type": "string", "required": True},
    }),
    _def("dns_enumeration", "3.2", "Enumerate DNS records", fn_3_2_dns_enum, {
        "domain": {"type": "string", "required": True}, "record_types": {"type": "array", "default": ["A", "MX", "NS", "TXT"]},
    }),
    _def("subdomain_scan", "3.3", "Discover subdomains via dictionary + APIs", fn_3_3_subdomain, {
        "domain": {"type": "string", "required": True}, "wordlist": {"type": "string", "default": "common"},
    }),
    _def("ssl_certificate", "3.4", "Inspect SSL/TLS certificate details", fn_3_4_ssl_cert, {
        "host": {"type": "string", "required": True}, "port": {"type": "integer", "default": 443},
    }),
    _def("web_tech_detect", "3.5", "Detect web technologies in use", fn_3_5_tech_detect, {
        "url": {"type": "string", "required": True},
    }),
    _def("email_osint", "3.6", "OSINT lookup on email address", fn_3_6_email_osint, {
        "email": {"type": "string", "required": True},
    }),
    _def("social_media_search", "3.7", "Search social media for username", fn_3_7_social_search, {
        "username": {"type": "string", "required": True}, "platforms": {"type": "array", "default": ["twitter", "github", "linkedin"]},
    }),
    _def("breach_check", "3.8", "Check if credentials appear in known breaches", fn_3_8_breach_check, {
        "email": {"type": "string", "required": True},
    }),
    _def("ip_geolocation", "3.9", "Get geolocation and ISP info for IP", fn_3_9_ip_geo, {
        "ip": {"type": "string", "required": True},
    }),
    _def("shodan_query", "3.10", "Query Shodan for open ports and services", fn_3_10_shodan, {
        "query": {"type": "string", "required": True},
    }),
]


def register_osint(registry):
    for fn in definitions:
        registry.register(fn)
