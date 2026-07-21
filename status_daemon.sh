#!/bin/bash
# CK-NEXUS v1.0 - Status Check

PIDFILE="/root/.ck-nexus/daemon.pid"
DB="/root/.ck-nexus/nexus_memory.db"

echo "⚡ CK-NEXUS v1.0 STATUS"
echo "========================"

# Check daemon
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "🟢 Daemon: RUNNING (PID: $PID)"
    else
        echo "🔴 Daemon: STOPPED (stale PID)"
    fi
else
    echo "🔴 Daemon: NOT RUNNING"
fi

# Check cache
if [ -f "/workspace/ck-nexus/nexus_cache_sd.db" ]; then
    ENTRIES=$(sqlite3 /workspace/ck-nexus/nexus_cache_sd.db "SELECT COUNT(*) FROM cache" 2>/dev/null || echo "0")
    echo "📦 Cache: $ENTRIES entries"
fi

# Check VPS
if [ -f "/workspace/ck-nexus/nexus_system_sd.db" ]; then
    VPS=$(sqlite3 /workspace/ck-nexus/nexus_system_sd.db "SELECT COUNT(*) FROM autonomous_vps_servers" 2>/dev/null || echo "0")
    echo "🖥️ VPS: $VPS registered"
fi

# Check storage
FREE=$(df -h /workspace | tail -1 | awk '{print $4}')
echo "💾 Free: $FREE"

# Check log
if [ -f "/root/.ck-nexus/daemon.log" ]; then
    LINES=$(wc -l < /root/.ck-nexus/daemon.log)
    echo "📄 Log: $LINES lines"
fi

echo "========================"
