#!/usr/bin/env python3
"""CK-NEXUS AIOS CLI — manage the AI Operating System from the command line."""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import time

CK_HOME = os.environ.get("CK_HOME", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PID_FILE = os.path.join(CK_HOME, ".ck-nexus.pid")
BACKUP_DIR = os.path.join(CK_HOME, "backups")
VERSION = "1.0.0"


def _print_banner():
    print(f"\n  CK-NEXUS AIOS CLI v{VERSION}\n")


def _read_pid():
    if not os.path.exists(PID_FILE):
        return 0
    try:
        return int(open(PID_FILE).read().strip())
    except (ValueError, OSError):
        return 0


def _write_pid(pid):
    with open(PID_FILE, "w") as f:
        f.write(str(pid))


def _remove_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def _is_running(pid):
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def cmd_start(args):
    _print_banner()
    pid = _read_pid()
    if _is_running(pid):
        print(f"  Already running (PID {pid})")
        return 0

    host = args.host or os.environ.get("CK_HOST", "0.0.0.0")
    port = args.port or int(os.environ.get("CK_PORT", "8080"))
    env = os.environ.copy()
    env["CK_HOST"] = host
    env["CK_PORT"] = str(port)
    if args.reload:
        env["CK_RELOAD"] = "true"

    cmd = [sys.executable, os.path.join(CK_HOME, "run.py")]
    proc = subprocess.Popen(cmd, cwd=CK_HOME, env=env, stdout=subprocess.PIPE if not args.foreground else None, stderr=subprocess.PIPE if not args.foreground else None, start_new_session=not args.foreground)
    _write_pid(proc.pid)

    if args.foreground:
        print(f"  Started on http://{host}:{port} (PID {proc.pid})")
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            proc.wait(timeout=10)
            _remove_pid()
    else:
        time.sleep(1)
        if _is_running(proc.pid):
            print(f"  Started on http://{host}:{port} (PID {proc.pid})")
            print(f"  Dashboard: http://{host}:{port}/app")
        else:
            print("  Failed to start")
            _remove_pid()
            return 1
    return 0


def cmd_stop(args):
    _print_banner()
    pid = _read_pid()
    if not _is_running(pid):
        print("  Not running")
        _remove_pid()
        return 0
    sig = signal.SIGKILL if args.force else signal.SIGTERM
    try:
        os.kill(pid, sig)
        for _ in range(30):
            if not _is_running(pid):
                break
            time.sleep(0.5)
    except ProcessLookupError:
        pass
    _remove_pid()
    print("  Stopped.")
    return 0


def cmd_status(args):
    _print_banner()
    pid = _read_pid()
    running = _is_running(pid)
    print(f"  Version:  {VERSION}")
    print(f"  Home:     {CK_HOME}")
    print(f"  PID:      {pid if running else 'N/A'}")
    print(f"  Status:   {'RUNNING' if running else 'STOPPED'}")
    backup_count = len([f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz")]) if os.path.isdir(BACKUP_DIR) else 0
    print(f"  Backups:  {backup_count}")
    return 0


def cmd_backup(args):
    _print_banner()
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    name = args.name or f"ck-nexus-{ts}"
    path = os.path.join(BACKUP_DIR, f"{name}.tar.gz")
    exclude = {".git", "__pycache__", ".pytest_cache", "backups", "node_modules", ".venv"}
    print(f"  Creating backup: {name}.tar.gz")
    count = 0
    with tarfile.open(path, "w:gz") as tar:
        for root, dirs, files in os.walk(CK_HOME):
            dirs[:] = [d for d in dirs if d not in exclude]
            for f in files:
                if f.endswith((".pyc",)):
                    continue
                fp = os.path.join(root, f)
                tar.add(fp, arcname=os.path.relpath(fp, CK_HOME))
                count += 1
    size = os.path.getsize(path) / 1024
    print(f"  Backup created: {path}")
    print(f"  Files: {count} | Size: {size:.1f} KB")
    return 0


def cmd_restore(args):
    _print_banner()
    backup_file = args.file
    if not backup_file:
        if not os.path.isdir(BACKUP_DIR):
            print("  No backups directory")
            return 1
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz")])
        if not backups:
            print("  No backups found")
            return 1
        for i, b in enumerate(backups):
            print(f"    {i+1}. {b}")
        try:
            choice = int(input("  Select: ")) - 1
            backup_file = os.path.join(BACKUP_DIR, backups[choice])
        except (ValueError, IndexError, EOFError):
            print("  Invalid selection")
            return 1

    if not os.path.isfile(backup_file):
        print(f"  File not found: {backup_file}")
        return 1

    pid = _read_pid()
    if _is_running(pid):
        os.kill(pid, signal.SIGTERM)
        time.sleep(3)
        _remove_pid()

    print(f"  Restoring from: {os.path.basename(backup_file)}")
    target = args.target or CK_HOME
    with tarfile.open(backup_file, "r:gz") as tar:
        tar.extractall(path=target)
    print(f"  Restored to: {target}")
    return 0


def cmd_update(args):
    _print_banner()
    git_dir = os.path.join(CK_HOME, ".git")
    if os.path.isdir(git_dir):
        print("  Pulling latest...")
        subprocess.run(["git", "pull", "--rebase"], cwd=CK_HOME)
    if not args.skip_deps:
        print("  Updating dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], cwd=CK_HOME)
    pid = _read_pid()
    if _is_running(pid):
        print("  Restarting...")
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        _remove_pid()
        subprocess.Popen([sys.executable, os.path.join(CK_HOME, "run.py")], cwd=CK_HOME, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    print("  Update complete.")
    return 0


def main():
    parser = argparse.ArgumentParser(prog="ck-nexus", description="CK-NEXUS AIOS CLI")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("start", help="Start server")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    p.add_argument("-f", "--foreground", action="store_true")
    p.add_argument("--reload", action="store_true")

    p = sub.add_parser("stop", help="Stop server")
    p.add_argument("-f", "--force", action="store_true")

    sub.add_parser("status", help="Show status")

    p = sub.add_parser("backup", help="Create backup")
    p.add_argument("--name", default=None)

    p = sub.add_parser("restore", help="Restore backup")
    p.add_argument("-f", "--file", default=None)
    p.add_argument("-t", "--target", default=None)

    p = sub.add_parser("update", help="Update system")
    p.add_argument("--skip-deps", action="store_true")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    return {"start": cmd_start, "stop": cmd_stop, "status": cmd_status, "backup": cmd_backup, "restore": cmd_restore, "update": cmd_update}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
