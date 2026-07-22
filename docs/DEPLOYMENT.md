# CK-NEXUS AIOS — Deployment Guide

## Quick Start (One Command)

```bash
curl -sSL https://raw.githubusercontent.com/pnook301-code/Ai-ck/main/deploy/install_on_vps.sh | bash
```

## Manual Deployment

### Prerequisites
- Docker 24+
- Docker Compose v2
- 4GB+ RAM recommended
- Ports: 3000, 4000, 5678, 6333, 5432, 6379

### Steps

1. Clone repository
```bash
git clone https://github.com/pnook301-code/Ai-ck.git
cd Ai-ck/ck-nexus-aios/deploy
```

2. Configure environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Start services
```bash
docker compose up -d
```

4. Verify
```bash
nexus health
```

## Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| Open WebUI | http://YOUR-IP:3000 | Chat interface |
| LiteLLM | http://YOUR-IP:4000 | API gateway |
| n8n | http://YOUR-IP:5678 | Workflows |
| Qdrant | http://YOUR-IP:6333 | Vector DB |

## CLI Commands

```bash
nexus up            # Start all services
nexus down          # Stop all services
nexus restart       # Restart all services
nexus status        # Show service status
nexus health        # Health check all services
nexus models        # List available AI models
nexus test          # Quick test
nexus ask 'question' # Ask a question
nexus switch model  # Switch AI model
nexus update        # Pull latest and restart
nexus backup        # Backup all data
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| POSTGRES_PASSWORD | Yes | PostgreSQL password |
| LITELLM_MASTER_KEY | Auto | LiteLLM API key (auto-generated) |
| OPENAI_API_KEY | No | OpenAI API key |
| ANTHROPIC_API_KEY | No | Anthropic API key |
| GEMINI_API_KEY | No | Google Gemini key |
| GROQ_API_KEY | No | Groq API key (free) |
| DEEPSEEK_API_KEY | No | DeepSeek API key |

## Backup

```bash
nexus backup
# Creates timestamped backup in ~/ck-nexus-backup-*/
```

## Restore

```bash
docker compose down -v
cp -r ~/ck-nexus-backup-*/.env /app/ck-nexus/
cp -r ~/ck-nexus-backup-*/litellm /app/ck-nexus/
docker compose up -d
```
