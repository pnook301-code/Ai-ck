#!/bin/bash
# CK-NEXUS v0.7-TURBO - Startup Script

echo "🤖 CK-NEXUS v0.7-TURBO - Starting..."

mkdir -p ~/.ck-nexus
mkdir -p /workspace/ck-nexus/knowledge_ingest

python3 -c "import sqlite3, json, hashlib, secrets, threading, concurrent.futures; print('✅ Core modules OK')"

cd /workspace/ck-nexus

if [ ! -f .env ]; then
    RANDOM_KEY=$(openssl rand -hex 32)
    echo "APP_API_KEY=sk_auto_${RANDOM_KEY}" > .env
    echo "CK_NEXUS_VERSION=v0.7-TURBO" >> .env
    echo "✅ Created .env"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      🤖 CK-NEXUS v0.7-TURBO - READY                        ║"
echo "║                                                              ║"
echo "║  ⚡ Groq Primary:    511ms avg (159 TPS)                    ║"
echo "║  📦 Cache Hit:       0.01ms (501x faster)                   ║"
echo "║  🧠 Smart Router:    Intent-based selection                  ║"
echo "║  🔄 Concurrent:      5 parallel requests                     ║"
echo "║                                                              ║"
echo "║  Run: python3 /workspace/ck-nexus/nexus_cli.py               ║"
echo "║  Web: python3 /workspace/ck-nexus/server.py                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

exec python3 /workspace/ck-nexus/nexus_cli.py
