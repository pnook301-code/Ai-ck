#!/usr/bin/env python3
"""CK-NEXUS AIOS — Startup Script."""
import sys
import os
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    host = os.environ.get("CK_HOST", "0.0.0.0")
    port = int(os.environ.get("CK_PORT", "8080"))
    reload = os.environ.get("CK_RELOAD", "false").lower() == "true"

    print(f"""
╔══════════════════════════════════════════════╗
║        CK-NEXUS AIOS v1.0.0                 ║
║        Enterprise AI Operating System         ║
╠══════════════════════════════════════════════╣
║  Server:  http://{host}:{port}                 ║
║  Dashboard: http://{host}:{port}/app           ║
║  API Docs: http://{host}:{port}/docs           ║
║  Health:   http://{host}:{port}/health          ║
╚══════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "kernel.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )

if __name__ == "__main__":
    main()
