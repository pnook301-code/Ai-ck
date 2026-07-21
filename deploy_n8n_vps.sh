#!/bin/bash
# CK-NEXUS v1.4 - n8n Auto-Deploy for VPS
# Usage: ./deploy_n8n_vps.sh <IP> <PASSWORD>

set -e

VPS_IP=$1
VPS_PASS=$2

if [ -z "$VPS_IP" ] || [ -z "$VPS_PASS" ]; then
    echo "Usage: $0 <IP> <PASSWORD>"
    exit 1
fi

echo "🚀 Deploying n8n on $VPS_IP..."

# Create remote setup script
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no root@$VPS_IP << 'REMOTE_SCRIPT'
#!/bin/bash
set -e

echo "[1/6] Updating system..."
apt-get update -qq && apt-get install -y -qq curl docker.io docker-compose git

echo "[2/6] Starting Docker..."
systemctl enable docker && systemctl start docker

echo "[3/6] Creating n8n directory..."
mkdir -p /opt/n8n && cd /opt/n8n

echo "[4/6] Creating docker-compose.yml..."
cat > docker-compose.yml << 'YAML'
version: '3.8'
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n
    container_name: n8n
    restart: always
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=nexus_admin
      - N8N_BASIC_AUTH_PASSWORD=CK-Nexus-2026!
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5678
      - GENERIC_TIMEZONE=Asia/Bangkok
    volumes:
      - n8n_data:/home/node/.n8n

volumes:
  n8n_data:
YAML

echo "[5/6] Starting n8n..."
docker-compose up -d

echo "[6/6] Verifying..."
sleep 5
if docker ps | grep -q n8n; then
    echo "✅ n8n DEPLOYED SUCCESSFULLY on port 5678"
    echo "🌐 URL: http://$(hostname -I | awk '{print $1}'):5678"
    echo "👤 User: nexus_admin"
    echo "🔑 Pass: CK-Nexus-2026!"
else
    echo "⚠️ n8n container failed to start"
    docker logs n8n
fi

# Install ck-nexus worker
mkdir -p /opt/ck-nexus-worker
cat > /opt/ck-nexus-worker/worker.py << 'PYEOF'
from fastapi import FastAPI
import httpx
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "alive", "node": "ck-nexus-worker", "version": "1.4"}

@app.post("/compute")
async def compute(payload: dict):
    prompt = payload.get("prompt", "Hello")
    model = payload.get("model", "llama-3.1-8b-instant")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": "Bearer PAYLOAD_KEY"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 1024},
            timeout=30.0
        )
        return {"result": r.json()["choices"][0]["message"]["content"]}
PYEOF

pip3 install fastapi uvicorn httpx -q
cd /opt/ck-nexus-worker && nohup uvicorn worker:app --host 0.0.0.0 --port 8000 &

echo "✅ Worker API on port 8000"
REMOTE_SCRIPT

echo "✅ Deployment complete on $VPS_IP"
echo "🌐 n8n: http://$VPS_IP:5678"
echo "🤖 Worker: http://$VPS_IP:8000"
