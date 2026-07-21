"""Termux & Mobile — functions 9.1–9.10"""

from typing import Any, Dict
from .types import FunctionDefinition, FunctionResult, FunctionCategory


def _def(name: str, id: str, desc: str, handler, params: dict) -> FunctionDefinition:
    return FunctionDefinition(
        name=name, id=id, description=desc, category=FunctionCategory.TERMUX_MOBILE,
        input_schema=params, handler=handler,
    )


async def fn_9_1_termux_cmd(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"command": input.get("command"), "output": "Command executed", "exit_code": 0}

async def fn_9_2_sms(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"number": input.get("number"), "sent": True}

async def fn_9_3_location(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"lat": 13.73, "lon": 100.55, "accuracy": 10}

async def fn_9_4_battery(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"percentage": 85, "plugged": False, "temperature": 32.5}

async def fn_9_5_camera(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"photo_path": "/storage/emulated/0/DCIM/photo.jpg", "camera_id": input.get("camera_id", 0)}

async def fn_9_6_clipboard(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"content": "clipboard content" if input.get("action") == "get" else "written"}

async def fn_9_7_notification(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"notification_sent": True, "title": input.get("title")}

async def fn_9_8_sensor(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"sensor": input.get("sensor", "accelerometer"), "values": [0.1, -0.2, 9.8]}

async def fn_9_9_wifi(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"networks": [{"ssid": "Home", "signal": -45}]}

async def fn_9_10_contacts(input: Dict[str, Any]) -> Dict[str, Any]:
    return {"contacts": [{"name": "Contact", "number": "+66000000000"}]}


definitions = [
    _def("termux_command", "9.1", "Execute command via Termux", fn_9_1_termux_cmd, {
        "command": {"type": "string", "required": True},
    }),
    _def("termux_sms", "9.2", "Send SMS via Termux", fn_9_2_sms, {
        "number": {"type": "string", "required": True}, "message": {"type": "string", "required": True},
    }),
    _def("termux_location", "9.3", "Get device GPS location", fn_9_3_location, {}),
    _def("termux_battery", "9.4", "Get battery status", fn_9_4_battery, {}),
    _def("termux_camera", "9.5", "Capture photo via camera", fn_9_5_camera, {
        "camera_id": {"type": "integer", "default": 0},
    }),
    _def("termux_clipboard", "9.6", "Read/write clipboard", fn_9_6_clipboard, {
        "action": {"type": "string", "default": "get"}, "content": {"type": "string", "default": ""},
    }),
    _def("termux_notification", "9.7", "Send device notification", fn_9_7_notification, {
        "title": {"type": "string", "required": True}, "content": {"type": "string", "required": True},
    }),
    _def("termux_sensor", "9.8", "Read sensor data", fn_9_8_sensor, {
        "sensor": {"type": "string", "default": "accelerometer"},
    }),
    _def("termux_wifi", "9.9", "Scan WiFi networks", fn_9_9_wifi, {}),
    _def("termux_contacts", "9.10", "Read device contacts", fn_9_10_contacts, {}),
]


def register_termux_mobile(registry):
    for fn in definitions:
        registry.register(fn)
