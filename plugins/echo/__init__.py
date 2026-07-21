"""Echo Plugin - Simple test plugin"""
import time

PLUGIN_NAME = "echo"
PLUGIN_VERSION = "1.0.0"

def on_load():
    print(f"[echo] Plugin loaded at {time.time()}")

def execute(*args, **kwargs):
    return {
        "echo": args if args else kwargs,
        "plugin": PLUGIN_NAME,
        "version": PLUGIN_VERSION,
        "timestamp": time.time()
    }

def info():
    return {"name": PLUGIN_NAME, "version": PLUGIN_VERSION, "description": "Echo plugin for testing"}
