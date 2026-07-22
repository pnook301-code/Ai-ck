#!/bin/bash
# ================================================================
# CK-NEXUS Shadow Bridge Setup — Windows ↔ Linux Auto-Connect
# ================================================================
# Run this on the LINUX server to set up:
# 1. SSH server for Windows to connect
# 2. Shadow Bridge configuration
# 3. Firewall rules
# 4. Auto-start service
# ================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  CK-NEXUS Shadow Bridge Setup (Linux)${NC}"
echo -e "${BLUE}============================================${NC}"

# ---- Config ----
SHADOW_HOME="${CK_SHADOW_HOME:-/opt/ck-nexus-shadow}"
SHADOW_PORT="${SHADOW_PORT:-22}"
MAIN_PORT="${MAIN_PORT:-3000}"
API_PORT="${API_PORT:-4000}"
WIN_IP="${WINDOWS_IP:-172.16.0.2}"
WIN_USER="${WINDOWS_USER:-Administrator}"

echo -e "${YELLOW}Config:${NC}"
echo "  Shadow Home:   $SHADOW_HOME"
echo "  SSH Port:      $SHADOW_PORT"
echo "  Windows IP:    $WIN_IP"
echo "  Windows User:  $WIN_USER"
echo ""

# ---- Step 1: Install SSH server ----
echo -e "${GREEN}[1/5] Installing SSH server...${NC}"
if ! command -v sshd &> /dev/null; then
    apt-get update -qq
    apt-get install -y -qq openssh-server
fi
systemctl enable sshd
systemctl start sshd
echo -e "${GREEN}  SSH server: OK${NC}"

# ---- Step 2: Configure SSH for key-based auth ----
echo -e "${GREEN}[2/5] Configuring SSH key authentication...${NC}"

SSH_DIR="/root/.ssh"
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

# Generate key pair if not exists
if [ ! -f "$SSH_DIR/id_ed25519" ]; then
    ssh-keygen -t ed25519 -f "$SSH_DIR/id_ed25519" -N "" -C "ck-nexus-shadow"
fi

# Configure sshd for key auth + password fallback
cat > /etc/ssh/sshd_config.d/ck-nexus.conf << 'SSHEOF'
# CK-NEXUS Shadow Bridge SSH Config
Port 22
PermitRootLogin prohibit-password
PubkeyAuthentication yes
PasswordAuthentication yes
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
AllowTcpForwarding yes
ClientAliveInterval 60
ClientAliveCountMax 3
SSHEOF

systemctl restart sshd
echo -e "${GREEN}  SSH config: OK${NC}"

# ---- Step 3: Create Shadow directories ----
echo -e "${GREEN}[3/5] Creating Shadow directories...${NC}"
mkdir -p "$SHADOW_HOME"/{scripts,logs,data,config}
chmod 700 "$SHADOW_HOME"

# Create config file
cat > "$SHADOW_HOME/config/bridge.json" << CFGEOF
{
  "bridge_mode": "linux_host",
  "ssh_port": $SHADOW_PORT,
  "main_port": $MAIN_PORT,
  "api_port": $API_PORT,
  "windows_ip": "$WIN_IP",
  "windows_user": "$WIN_USER",
  "allowed_commands": [
    "nexus_cli.py",
    "api_key_demo.py",
    "auto_system.py",
    "vps_auto_reg.py"
  ],
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
CFGEOF

echo -e "${GREEN}  Shadow dirs: OK${NC}"

# ---- Step 4: Firewall rules ----
echo -e "${GREEN}[4/5] Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    ufw allow 22/tcp       # SSH
    ufw allow $MAIN_PORT/tcp   # Chat UI
    ufw allow $API_PORT/tcp    # API Gateway
    ufw allow 5678/tcp     # n8n
    ufw allow 6333/tcp     # Qdrant
    ufw --force enable
    echo -e "${GREEN}  UFW: OK${NC}"
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=22/tcp
    firewall-cmd --permanent --add-port=$MAIN_PORT/tcp
    firewall-cmd --permanent --add-port=$API_PORT/tcp
    firewall-cmd --permanent --add-port=5678/tcp
    firewall-cmd --permanent --add-port=6333/tcp
    firewall-cmd --reload
    echo -e "${GREEN}  firewalld: OK${NC}"
else
    echo -e "${YELLOW}  No firewall found — skipping${NC}"
fi

# ---- Step 5: Create systemd service ----
echo -e "${GREEN}[5/5] Creating Shadow Bridge service...${NC}"
cat > /etc/systemd/system/ck-nexus-shadow.service << SVCEOF
[Unit]
Description=CK-NEXUS Shadow Bridge
After=network.target sshd.service

[Service]
Type=simple
User=root
WorkingDirectory=$SHADOW_HOME
ExecStart=/usr/bin/python3 $SHADOW_HOME/scripts/shadow_bridge_server.py
Restart=always
RestartSec=10
Environment=CK_SHADOW_HOME=$SHADOW_HOME

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
# Don't enable yet — server script not created
echo -e "${GREEN}  Service file: OK${NC}"

# ---- Print connection info ----
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}  Shadow Bridge Setup Complete!${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo "  Linux SSH Key:     $SSH_DIR/id_ed25519"
echo "  Linux Internal IP: $LOCAL_IP"
echo "  Config:            $SHADOW_HOME/config/bridge.json"
echo ""
echo -e "${YELLOW}  On Windows, run:${NC}"
echo "    ssh -i <key> root@$LOCAL_IP"
echo ""
echo -e "${YELLOW}  To enable auto-start:${NC}"
echo "    systemctl enable --now ck-nexus-shadow"
echo ""
echo -e "${GREEN}  CK-NEXUS ports:${NC}"
echo "    Chat UI:    http://$LOCAL_IP:$MAIN_PORT"
echo "    API:        http://$LOCAL_IP:$API_PORT"
echo "    n8n:        http://$LOCAL_IP:5678"
echo "    Qdrant:     http://$LOCAL_IP:6333"
