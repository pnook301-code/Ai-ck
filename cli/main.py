#!/usr/bin/env python3
"""CK-NEXUS CLI - Interactive terminal interface"""
import sys
import os
import json
import readline

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus_engine import NexusEngine

BANNER = """
\033[36m╔══════════════════════════════════════════════════════════╗
║                    CK-NEXUS AI OS                        ║
║              Enterprise AI Operating System              ║
║                    v0.1.0                                ║
╠══════════════════════════════════════════════════════════╣
║  Chat:                                                  ║
║    <message>       - Chat with AI (default)              ║
║                                                          ║
║  System:                                                 ║
║    /help           - Show all commands                   ║
║    /status         - System status                       ║
║    /providers      - AI provider status                  ║
║    /test           - Test all providers                  ║
║    /clear          - Clear screen                        ║
║    /quit           - Exit                                ║
║                                                          ║
║  LINE (OAuth2):                                          ║
║    /line auth id=<id> secret=<secret> - Start OAuth      ║
║    /line code=<code>        - Complete OAuth             ║
║    /line status    - LINE auth status                    ║
║    /line test      - Test LINE connection                ║
║    /line profile   - Get bot profile                     ║
║    /line logout    - Disconnect LINE                     ║
║    /send to=<id> <msg> - Send LINE message               ║
║    /notify <msg>   - LINE notification                   ║
╚══════════════════════════════════════════════════════════╝\033[0m
"""

def format_response(result):
    if "error" in result:
        return f"\033[31mError: {result['error']}\033[0m"

    lines = []
    if "response" in result:
        lines.append(result["response"])
        meta = []
        if result.get("provider"): meta.append(f"{result['provider']}")
        if result.get("model"): meta.append(f"{result['model']}")
        if result.get("tokens"): meta.append(f"{result['tokens']}t")
        if meta:
            lines.append(f"\033[90m[{', '.join(meta)}]\033[0m")
    else:
        lines.append(json.dumps(result, indent=2, default=str))

    return "\n".join(lines)

def main():
    print(BANNER)

    engine = NexusEngine()
    print(f"Session: {engine.session_id}")

    status = engine.router.get_status()
    providers = [f"{name}{'✓' if info.get('configured') else '✗'}" for name, info in status.items()]
    print(f"Providers: {', '.join(providers)}")

    plugins = engine.plugins.discover()
    if plugins:
        print(f"Plugins: {', '.join(plugins)}")
    print()

    while True:
        try:
            user_input = input("\033[36mCK-NEXUS>\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd = user_input[1:].strip()
            if cmd in ("quit", "exit", "q"):
                print("Shutting down...")
                break
            if cmd == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                continue
            if cmd == "help":
                print(BANNER)
                continue

            result = engine.process_input(user_input[1:])
            print(format_response(result))
            continue

        result = engine.process_input(user_input)
        print(format_response(result))

    engine.shutdown()

if __name__ == "__main__":
    main()
