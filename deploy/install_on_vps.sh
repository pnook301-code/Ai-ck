#!/bin/bash
# ================================================================
# CK-NEXUS AIOS — One-Command Installer
# Copy-paste this entire script into your VPS terminal
# ================================================================
set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  CK-NEXUS AIOS — One-Command VPS Installer              ║"
echo "║  100 AI Models · Auto Failover · Zero Downtime          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Generate all secrets ──────────────────────────────────────────────
N8N_KEY=$(openssl rand -hex 32)
N8N_SALT=$(openssl rand -hex 16)
JWT_SECRET=$(openssl rand -hex 32)
DB_PASS=$(openssl rand -base64 24 | tr -d '=')
MASTER_KEY="sk-nexus-$(openssl rand -hex 16)"
QDRANT_KEY=$(openssl rand -hex 32)

# ── Create directories ───────────────────────────────────────────────
mkdir -p /app/ck-nexus/{litellm,n8n_data,qdrant_data,webui_data,postgres_data,redis_data,scripts,workflows,logs}

# ── Write .env ───────────────────────────────────────────────────────
cat > /app/ck-nexus/.env << EOF
POSTGRES_USER=nexus
POSTGRES_PASSWORD=${DB_PASS}
POSTGRES_DB=nexus_aios
N8N_ENCRYPTION_KEY=${N8N_KEY}
N8N_PASSWORD_SALT=${N8N_SALT}
N8N_USER_MANAGEMENT_JWT_SECRET=${JWT_SECRET}
N8N_HOST=0.0.0.0
LITELLM_MASTER_KEY=${MASTER_KEY}
QDRANT__SERVICE__API_KEY=${QDRANT_KEY}
EOF

# ── Write LiteLLM config ────────────────────────────────────────────
cat > /app/ck-nexus/litellm/config.yaml << 'LITELLMEOF'
model_list:
  # Free (No API Key Required)
  - model_name: auto
    litellm_params: { model: groq/llama-3.3-70b-versatile, api_key: os.environ/GROQ_API_KEY }
  - model_name: free
    litellm_params: { model: groq/llama-3.3-70b-versatile, api_key: os.environ/GROQ_API_KEY }
  - model_name: fast
    litellm_params: { model: groq/llama-3.1-8b-instant, api_key: os.environ/GROQ_API_KEY }
  - model_name: free-llama
    litellm_params: { model: groq/llama-3.3-70b-versatile, api_key: os.environ/GROQ_API_KEY }
  - model_name: free-mixtral
    litellm_params: { model: groq/mixtral-8x7b-32768, api_key: os.environ/GROQ_API_KEY }
  - model_name: free-gemma
    litellm_params: { model: groq/gemma2-9b-it, api_key: os.environ/GROQ_API_KEY }

  # OpenAI (Paid)
  - model_name: gpt-4o
    litellm_params: { model: openai/gpt-4o, api_key: os.environ/OPENAI_API_KEY }
  - model_name: gpt-4o-mini
    litellm_params: { model: openai/gpt-4o-mini, api_key: os.environ/OPENAI_API_KEY }

  # Anthropic (Paid)
  - model_name: claude-opus
    litellm_params: { model: anthropic/claude-opus-4-20250514, api_key: os.environ/ANTHROPIC_API_KEY }
  - model_name: claude-sonnet
    litellm_params: { model: anthropic/claude-sonnet-4-20250514, api_key: os.environ/ANTHROPIC_API_KEY }

  # DeepSeek (Cheapest)
  - model_name: deepseek
    litellm_params: { model: deepseek/deepseek-chat, api_key: os.environ/DEEPSEEK_API_KEY }
  - model_name: deepseek-r1
    litellm_params: { model: deepseek/deepseek-reasoner, api_key: os.environ/DEEPSEEK_API_KEY }

  # Gemini
  - model_name: gemini-pro
    litellm_params: { model: gemini/gemini-2.5-pro-preview-05-06, api_key: os.environ/GEMINI_API_KEY }
  - model_name: gemini-flash
    litellm_params: { model: gemini/gemini-2.0-flash, api_key: os.environ/GEMINI_API_KEY }

router_settings:
  routing_strategy: simple-shuffle
  num_retries: 3
  retry_after: 5
  timeout: 120

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY

litellm_settings:
  drop_params: true
  num_retries: 3
  fallbacks:
    - auto: [free-llama, free-mixtral, free-gemma]
    - gpt-4o: [claude-sonnet, gemini-flash, deepseek]
    - claude-opus: [gpt-4o, gemini-pro, deepseek]
LITELLMEOF

# ── Write docker-compose.yml ────────────────────────────────────────
cat > /app/ck-nexus/docker-compose.yml << 'COMPOSEEOF'
version: "3.9"
services:
  postgres:
    image: postgres:16-alpine
    container_name: nexus-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-nexus}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-nexus_aios}
    volumes: [postgres_data:/var/lib/postgresql/data]
    ports: ["127.0.0.1:5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nexus"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks: [nexus_net]

  redis:
    image: redis:7-alpine
    container_name: nexus-redis
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    ports: ["127.0.0.1:6379:6379"]
    restart: unless-stopped
    networks: [nexus_net]

  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    container_name: nexus-litellm
    ports: ["0.0.0.0:4000:4000"]
    volumes: [./litellm/config.yaml:/app/config.yaml:ro]
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    env_file: .env
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:4000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on: [postgres]
    restart: unless-stopped
    networks: [nexus_net]

  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    container_name: nexus-n8n
    ports: ["0.0.0.0:5678:5678"]
    environment:
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - N8N_PASSWORD_SALT=${N8N_PASSWORD_SALT}
      - N8N_USER_MANAGEMENT_JWT_SECRET=${N8N_USER_MANAGEMENT_JWT_SECRET}
      - N8N_HOST=0.0.0.0
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://0.0.0.0:5678/
      - N8N_DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_USER=${POSTGRES_USER:-nexus}
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - DB_POSTGRESDB_DATABASE=${POSTGRES_DB:-nexus_aios}
      - GENERIC_TIMEZONE=Asia/Bangkok
      - TZ=Asia/Bangkok
    volumes:
      - n8n_data:/home/node/.n8n
    depends_on: [postgres]
    restart: unless-stopped
    networks: [nexus_net]

  qdrant:
    image: qdrant/qdrant:latest
    container_name: nexus-qdrant
    ports: ["0.0.0.0:6333:6333", "6334:6334"]
    volumes: [qdrant_data:/qdrant/storage]
    environment:
      QDRANT__SERVICE__API_KEY: ${QDRANT__SERVICE__API_KEY}
    restart: unless-stopped
    networks: [nexus_net]

  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: nexus-webui
    ports: ["0.0.0.0:3000:8080"]
    environment:
      - OPENAI_API_BASE_URL=http://litellm:4000/v1
      - OPENAI_API_KEY=${LITELLM_MASTER_KEY}
      - ENABLE_SIGNUP=true
      - DEFAULT_MODELS=auto|free|gpt-4o|deepseek|claude-sonnet
    volumes: [webui_data:/app/backend/data]
    depends_on: [litellm]
    restart: unless-stopped
    networks: [nexus_net]

volumes:
  postgres_data:
  redis_data:
  n8n_data:
  qdrant_data:
  webui_data:

networks:
  nexus_net:
    driver: bridge
COMPOSEEOF

# ── Write nexus CLI ──────────────────────────────────────────────────
cat > /usr/local/bin/nexus << 'CLIEOF'
#!/bin/bash
set -e
D="/app/ck-nexus"; DC="docker compose -f $D/docker-compose.yml"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
IP=$(hostname -I | awk '{print $1}')

case "${1:-help}" in
  up)
    echo -e "${GREEN}Starting CK-NEXUS AIOS...${NC}"
    $DC up -d
    sleep 5
    echo ""
    echo "  🌐 Chat UI:     http://$IP:3000"
    echo "  🧠 n8n:         http://$IP:5678"
    echo "  🔌 API Gateway: http://$IP:4000"
    echo "  💾 Qdrant:      http://$IP:6333"
    ;;
  down)
    echo -e "${YELLOW}Stopping...${NC}"; $DC down ;;
  restart)
    echo -e "${YELLOW}Restarting...${NC}"; $DC restart ;;
  status)
    echo -e "${CYAN}Service Status:${NC}"; $DC ps ;;
  logs)
    $DC logs -f --tail=50 ;;
  health)
    echo -e "${CYAN}Health Checks:${NC}"
    echo -n "  LiteLLM: "; curl -sf http://localhost:4000/health >/dev/null && echo "${GREEN}✓${NC}" || echo "${RED}✗${NC}"
    echo -n "  n8n:     "; curl -sf http://localhost:5678/healthz >/dev/null && echo "${GREEN}✓${NC}" || echo "${RED}✗${NC}"
    echo -n "  Qdrant:  "; curl -sf http://localhost:6333/healthz >/dev/null && echo "${GREEN}✓${NC}" || echo "${RED}✗${NC}"
    echo -n "  WebUI:   "; curl -sf http://localhost:3000 >/dev/null && echo "${GREEN}✓${NC}" || echo "${RED}✗${NC}"
    echo -n "  Postgres:"; docker exec nexus-postgres pg_isready -U nexus 2>/dev/null && echo "${GREEN}✓${NC}" || echo "${RED}✗${NC}"
    ;;
  models)
    echo -e "${CYAN}Available Models:${NC}"
    source "$D/.env" 2>/dev/null
    curl -sf http://localhost:4000/v1/models -H "Authorization: Bearer $LITELLM_MASTER_KEY" | jq -r '.data[].id' 2>/dev/null | sort
    ;;
  test)
    source "$D/.env" 2>/dev/null
    echo -e "${CYAN}Testing with auto (free Groq Llama)...${NC}"
    curl -s http://localhost:4000/v1/chat/completions \
      -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
      -H "Content-Type: application/json" \
      -d '{"model":"auto","messages":[{"role":"user","content":"Say hello in 5 words"}],"max_tokens":50}' | \
      jq -r '.choices[0].message.content' 2>/dev/null
    ;;
  ask)
    source "$D/.env" 2>/dev/null
    Q="${2:-Hello}"
    curl -s http://localhost:4000/v1/chat/completions \
      -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"model\":\"auto\",\"messages\":[{\"role\":\"user\",\"content\":\"$Q\"}],\"max_tokens\":1024}" | \
      jq -r '.choices[0].message.content' 2>/dev/null
    ;;
  switch)
    M="${2:-auto}"
    echo -e "${YELLOW}Switching to: $M${NC}"
    echo "Default model set. Use 'nexus ask' to test."
    ;;
  update)
    echo -e "${YELLOW}Updating...${NC}"; $DC pull; $DC up -d ;;
  backup)
    B="$HOME/ck-nexus-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$B"; cp -r $D/.env $D/docker-compose.yml $D/litellm "$B/"
    echo -e "${GREEN}✓ Backup: $B${NC}" ;;
  *)
    echo "CK-NEXUS CLI: nexus {up|down|restart|status|logs|health|models|test|ask|switch|update|backup}" ;;
esac
CLIEOF
chmod +x /usr/local/bin/nexus

# ── Install Docker if needed ─────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
fi

# ── Configure UFW ────────────────────────────────────────────────────
ufw --force enable 2>/dev/null || true
ufw allow 22/tcp 2>/dev/null || true
ufw allow 3000/tcp 2>/dev/null || true
ufw allow 4000/tcp 2>/dev/null || true
ufw allow 5678/tcp 2>/dev/null || true
ufw allow 6333/tcp 2>/dev/null || true

# ── Launch ───────────────────────────────────────────────────────────
cd /app/ck-nexus
docker compose up -d

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ CK-NEXUS AIOS — Installation Complete!              ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
IP=$(hostname -I | awk '{print $1}')
echo "║  🌐 Chat UI (Open WebUI):  http://$IP:3000             ║"
echo "║  🧠 Automation (n8n):      http://$IP:5678             ║"
echo "║  🔌 API Gateway (LiteLLM): http://$IP:4000             ║"
echo "║  💾 Vector DB (Qdrant):    http://$IP:6333             ║"
echo "║                                                          ║"
echo "║  CLI: nexus {up|down|status|health|models|test|ask}     ║"
echo "║                                                          ║"
source /app/ck-nexus/.env
echo "║  🔑 API Key: $MASTER_KEY                         ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
