"""Network & Proxy — functions 8.1–8.10"""

from typing import Any, Dict
from .types import FunctionDefinition, FunctionCategory


def _def(name: str, id: str, desc: str, handler, params: dict) -> FunctionDefinition:
    return FunctionDefinition(
        name=name, id=id, description=desc, category=FunctionCategory.NETWORK_PROXY,
        input_schema=params, handler=handler,
    )


async def fn_8_1_proxy(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"new_ip": "x.x.x.x", "proxy_type": input.get("proxy_type", "http")}

async def fn_8_2_tor(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"tor": input.get("action", "start") + "ed", "circuit": "established"}

async def fn_8_3_vpn(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"server": input.get("server"), "connected": True, "assigned_ip": "10.x.x.x"}

async def fn_8_4_traceroute(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"target": input.get("target"), "hops": []}

async def fn_8_5_bandwidth(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"download_mbps": 100, "upload_mbps": 50, "latency_ms": 15}

async def fn_8_6_doh(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"domain": input.get("domain"), "resolver": input.get("resolver", "cloudflare"), "records": []}

async def fn_8_7_http_req(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"url": input.get("url"), "method": input.get("method", "GET"), "status": 200, "body": "<html>...</html>"}

async def fn_8_8_pcap(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"interface": input.get("interface", "eth0"), "packets_captured": input.get("count", 100)}

async def fn_8_9_mitm(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"proxy": input.get("action", "start") + "ed", "port": input.get("port", 8080)}

async def fn_8_10_ssh_tunnel(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"host": input.get("host"), "tunnel": "established", "local_port": input.get("local_port"), "remote_port": input.get("remote_port")}


definitions = [
    _def("proxy_rotate", "8.1", "Rotate proxy IP", fn_8_1_proxy, {
        "proxy_type": {"type": "string", "default": "http"},
    }),
    _def("tor_route", "8.2", "Route traffic through Tor", fn_8_2_tor, {
        "action": {"type": "string", "default": "start"},
    }),
    _def("vpn_connect", "8.3", "Connect to VPN endpoint", fn_8_3_vpn, {
        "server": {"type": "string", "required": True}, "protocol": {"type": "string", "default": "openvpn"},
    }),
    _def("network_trace", "8.4", "Run traceroute to target", fn_8_4_traceroute, {
        "target": {"type": "string", "required": True}, "max_hops": {"type": "integer", "default": 30},
    }),
    _def("bandwidth_test", "8.5", "Test network bandwidth and latency", fn_8_5_bandwidth, {
        "target": {"type": "string", "default": "auto"},
    }),
    _def("dns_over_https", "8.6", "Resolve DNS via DoH", fn_8_6_doh, {
        "domain": {"type": "string", "required": True}, "resolver": {"type": "string", "default": "cloudflare"},
    }),
    _def("http_req", "8.7", "Send custom HTTP request", fn_8_7_http_req, {
        "url": {"type": "string", "required": True}, "method": {"type": "string", "default": "GET"}, "headers": {"type": "object", "default": {}},
    }),
    _def("capture_packets", "8.8", "Capture network packets for analysis", fn_8_8_pcap, {
        "interface": {"type": "string", "default": "eth0"}, "count": {"type": "integer", "default": 100},
    }),
    _def("mitm_proxy", "8.9", "Start/stop man-in-the-middle proxy", fn_8_9_mitm, {
        "action": {"type": "string", "default": "start"}, "port": {"type": "integer", "default": 8080},
    }),
    _def("ssh_tunnel", "8.10", "Establish SSH tunnel", fn_8_10_ssh_tunnel, {
        "host": {"type": "string", "required": True}, "local_port": {"type": "integer", "required": True}, "remote_port": {"type": "integer", "required": True},
    }),
]


def register_network_proxy(registry):
    for fn in definitions:
        registry.register(fn)
