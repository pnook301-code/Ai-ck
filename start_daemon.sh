#!/bin/bash
cd /workspace/ck-nexus
export PYTHONUNBUFFERED=1

# Kill old daemon
pkill -f "python3.*headless_mainframe" 2>/dev/null
sleep 1

# Start new daemon
nohup python3 -u headless_mainframe.py >> /root/.ck-nexus/daemon.log 2>&1 &
echo $! > /root/.ck-nexus/daemon.pid
echo "Daemon started with PID: $(cat /root/.ck-nexus/daemon.pid)"
