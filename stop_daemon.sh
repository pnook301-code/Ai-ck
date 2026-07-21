#!/bin/bash
# CK-NEXUS v1.0 - Stop Daemon

PIDFILE="/root/.ck-nexus/daemon.pid"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    kill "$PID" 2>/dev/null
    rm -f "$PIDFILE"
    echo "✅ Daemon stopped (PID: $PID)"
else
    echo "⚠️ No daemon running"
fi

pkill -f "headless_mainframe" 2>/dev/null
pkill -f "server.py" 2>/dev/null
