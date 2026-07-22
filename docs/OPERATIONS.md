# CK-NEXUS AIOS — Operations Guide

## Monitoring

### Health Checks
```bash
nexus health
```

### Logs
```bash
nexus logs              # All services
nexus logs litellm      # Specific service
docker logs nexus-n8n   # Direct Docker
```

### Metrics
- LiteLLM: http://localhost:4000/metrics
- Qdrant: http://localhost:6333/dashboard
- n8n: Built-in workflow analytics

## Backup & Recovery

### Automated Backup
```bash
nexus backup
# Creates: ~/ck-nexus-backup-YYYYMMDD-HHMMSS/
```

### Manual Backup
```bash
docker exec nexus-postgres pg_dump -U nexus nexus_aios > backup.sql
cp -r /app/ck-nexus/qdrant_data backup/
cp -r /app/ck-nexus/n8n_data backup/
```

### Restore
```bash
docker compose down -v
cat backup.sql | docker exec -i nexus-postgres psql -U nexus
docker compose up -d
```

## Troubleshooting

### Service Won't Start
```bash
docker compose ps              # Check status
docker compose logs <service>  # Check logs
docker compose restart <service>
```

### Port Already in Use
```bash
lsof -i :3000
kill -9 <PID>
```

### Database Connection Issues
```bash
docker exec nexus-postgres pg_isready -U nexus
docker compose restart postgres
```

### Out of Memory
```bash
docker stats                   # Check usage
docker compose down
docker system prune -f
docker compose up -d
```

## Scaling

### Horizontal Scaling
```yaml
# docker-compose.yml
services:
  litellm:
    deploy:
      replicas: 3
```

### Vertical Scaling
Edit resource limits in docker-compose.yml:
```yaml
services:
  litellm:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

## Disaster Recovery

1. Regular backups: `nexus backup` (daily recommended)
2. Test restore procedure quarterly
3. Keep backup offsite (S3, GCS, etc.)
4. Monitor disk usage
