#!/bin/bash
# CK-NEXUS v1.4 - VPS DEPLOYER
# Deploy n8n + AI on all VPS nodes

echo "🚀 CK-NEXUS VPS DEPLOYER"
echo "========================="

# Load VPS IPs from database
cd /workspace/ck-nexus
VPS_LIST=$(python3 -c "
import sqlite3
conn = sqlite3.connect('nexus_system_sd.db')
for row in conn.execute('SELECT provider_name, notes FROM autonomous_vps_servers WHERE notes LIKE \"%SSH_IP:%\"').fetchall():
    notes = row[1] or ''
    if 'SSH_IP:' in notes:
        ip = notes.split('SSH_IP:')[1].split('|')[0].strip()
        pw = notes.split('SSH_PASSWORD:')[1].split('|')[0].strip() if 'SSH_PASSWORD:' in notes else ''
        print(f'{row[0]}|{ip}|{pw}')
conn.close()
")

if [ -z "$VPS_LIST" ]; then
    echo "⚠️ No VPS with IP found. Need to create servers first."
    exit 0
fi

echo "$VPS_LIST" | while IFS='|' read -r NAME IP PASS; do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🖥️  Deploying to: $NAME ($IP)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # SSH command
    if [ -n "$PASS" ]; then
        SSH_CMD="sshpass -p '$PASS' ssh -o StrictHostKeyChecking=no root@$IP"
    else
        SSH_CMD="ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no root@$IP"
    fi

    # Deploy n8n via Docker
    DEPLOY_SCRIPT='
#!/bin/bash
set -e

echo "[VPS] Installing Docker..."
apt-get update -y
apt-get install -y docker.io docker-compose curl

echo "[VPS] Starting Docker..."
systemctl enable docker
systemctl start docker

echo "[VPS] Creating n8n directory..."
mkdir -p ~/nexus_hive
cd ~/nexus_hive

echo "[VPS] Writing docker-compose.yml..."
cat > docker-compose.yml << "EOF"
version: "3"
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    restart: always
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - GENERIC_TIMEZONE=Asia/Bangkok
    volumes:
      - n8n_data:/home/node/.local/share/n8n
volumes:
  n8n_data:
EOF

echo "[VPS] Starting n8n..."
docker-compose up -d

echo "[VPS] Waiting for n8n..."
sleep 15

if curl -s http://localhost:5678 > /dev/null 2>&1; then
    echo "N8N_DEPLOYED_SUCCESSFULLY"
    echo "DEPLOYED" > ~/nexus_hive/status.txt
else
    echo "N8N_DEPLOY_FAILED"
    echo "FAILED" > ~/nexus_hive/status.txt
fi

echo "[VPS] Installing Python AI tools..."
apt-get install -y python3-pip

echo "[VPS] Setup complete!"
'

    echo "📡 Sending deploy script to $IP..."
    if [ -n "$PASS" ]; then
        sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no root@"$IP" "$DEPLOY_SCRIPT" 2>&1 | tail -5
    else
        ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no root@"$IP" "$DEPLOY_SCRIPT" 2>&1 | tail -5
    fi

    if [ $? -eq 0 ]; then
        echo "✅ $NAME: DEPLOYED"
    else
        echo "❌ $NAME: FAILED"
    fi
done

echo ""
echo "========================="
echo "✅ Deployment complete"
