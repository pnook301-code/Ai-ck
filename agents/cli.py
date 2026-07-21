#!/usr/bin/env python3
"""CK-NEXUS Agent CLI - manage and interact with agents"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_manager import AgentManager


BANNER = """
\033[36m╔══════════════════════════════════════════════════════════╗
║                 CK-NEXUS Agent System                    ║
║              Multi-Agent Orchestration                   ║
╠══════════════════════════════════════════════════════════╣
║  Commands:                                               ║
║    status          - Show all agents                     ║
║    audit           - Full system audit                   ║
║    plan <task>     - Plan a task                         ║
║    run <task>      - Execute task with agents            ║
║    delegate <agent> <task> - Delegate to specific agent  ║
║    agent <name>    - Show agent details                  ║
║    log             - Show workflow log                   ║
║    help            - Show this help                      ║
║    quit            - Exit                                ║
╚══════════════════════════════════════════════════════════╝\033[0m
"""


def format_result(result):
    if isinstance(result, dict):
        return json.dumps(result, indent=2, default=str)
    return str(result)


def main():
    print(BANNER)

    manager = AgentManager()
    print(f"Agents loaded: {len(manager.agents)}")
    print(f"Agents: {', '.join(manager.agents.keys())}")
    print()

    while True:
        try:
            user_input = input("\033[33mAgent>\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        parts = user_input.split(maxsplit=2)
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if cmd in ("quit", "exit", "q"):
            print("Shutting down agents...")
            break

        if cmd == "help":
            print(BANNER)
            continue

        if cmd == "status":
            status = manager.get_status()
            print(format_result(status))
            continue

        if cmd == "audit":
            print("Running full system audit...")
            result = manager.run_full_audit()
            print(format_result(result))
            continue

        if cmd == "plan" and args:
            task = " ".join(args)
            plan = manager.orchestrator.plan(task)
            print(f"Plan created: {plan['id']}")
            print(f"Steps: {len(plan['steps'])}")
            for step in plan["steps"]:
                print(f"  {step['step']}. [{step['agent']}] {step['description']}")
            continue

        if cmd == "run" and args:
            task = " ".join(args)
            print(f"Executing: {task}")
            result = manager.execute(task)
            print(format_result(result))
            continue

        if cmd == "delegate" and len(args) >= 2:
            agent_name = args[0]
            task = " ".join(args[1:])
            result = manager.delegate(agent_name, task)
            print(format_result(result))
            continue

        if cmd == "agent" and args:
            agent = manager.get_agent(args[0])
            if agent:
                print(format_result(agent.get_status()))
                print("\nRecent log:")
                for entry in agent.get_recent_log(5):
                    print(f"  {entry['time']}: {entry['entry']}")
            else:
                print(f"Agent not found: {args[0]}")
            continue

        if cmd == "log":
            log = manager.get_workflow_log()
            for entry in log[-20:]:
                print(f"  {entry['time']}: {entry['entry']}")
            continue

        print(f"Unknown command: {cmd}. Type 'help' for commands.")

    print("Agent system shutdown complete.")


if __name__ == "__main__":
    main()
