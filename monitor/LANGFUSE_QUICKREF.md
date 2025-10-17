# 🚀 Langfuse 3.0 Quick Reference

## Start/Stop Services

```bash
# Start (create all services)
docker compose -f langfuse.compose.yml up -d

# Stop (keep data)
docker compose -f langfuse.compose.yml down

# Stop and delete all data
docker compose -f langfuse.compose.yml down -v

# Restart all services
docker compose -f langfuse.compose.yml restart

# Restart specific service
docker compose -f langfuse.compose.yml restart langfuse-web
```

## Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Langfuse UI | http://localhost:3000 | Sign up at first login |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin123 |
| PostgreSQL | localhost:5432 | langfuse / (from .env) |
| Redis | localhost:6379 | (from .env) |
| ClickHouse | localhost:8123 | langfuse / (from .env) |

## Logs & Debugging

```bash
# View all logs
docker compose -f langfuse.compose.yml logs -f

# View specific service logs
docker compose -f langfuse.compose.yml logs -f langfuse-web
docker compose -f langfuse.compose.yml logs -f langfuse-worker

# View last 50 lines with timestamps
docker compose -f langfuse.compose.yml logs --tail=50 --timestamps

# Search logs for errors
docker compose -f langfuse.compose.yml logs | grep -i error
```

## Database Operations

```bash
# Access PostgreSQL
docker compose exec postgres psql -U langfuse -d langfuse

# Backup PostgreSQL
docker compose exec postgres pg_dump -U langfuse langfuse > backup.sql

# Restore PostgreSQL
docker compose exec -T postgres psql -U langfuse langfuse < backup.sql

# Check database size
docker compose exec postgres psql -U langfuse langfuse \
  -c "SELECT pg_size_pretty(pg_database_size('langfuse'));"

# Access ClickHouse
docker compose exec clickhouse clickhouse-client

# Export ClickHouse table
docker compose exec clickhouse clickhouse-client \
  -q "SELECT * FROM traces FORMAT CSV" > traces.csv
```

## Monitoring

```bash
# Check service status
docker compose -f langfuse.compose.yml ps

# Check resource usage
docker compose -f langfuse.compose.yml stats

# Monitor in real-time
watch -n 1 'docker compose -f langfuse.compose.yml ps'

# Check disk usage
du -sh langfuse_*_data/

# Check database connections
docker compose exec postgres psql -U langfuse langfuse \
  -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"
```

## Configuration

```bash
# Set environment variables
export LANGFUSE_PORT=3001
export POSTGRES_PASSWORD=mysecurepassword

# Start with custom port
LANGFUSE_PORT=3001 docker compose -f langfuse.compose.yml up -d

# Generate secure secret
openssl rand -base64 32
```

## Integration Examples

### Python - Langfuse SDK

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="http://localhost:3000"
)

# Create trace
trace = langfuse.trace(name="my_trace", user_id="user-123")

# Log generation
trace.generation(
    name="llm_call",
    model="gpt-4",
    input="Hello",
    output="Hi there!"
)

# Score trace
trace.score(name="quality", value=0.9)
```

### Python - With OpenAI

```python
from langfuse.openai import openai

response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### JavaScript/TypeScript

```typescript
import Langfuse from "langfuse";

const langfuse = new Langfuse({
  publicKey: "pk-lf-...",
  secretKey: "sk-lf-...",
  baseUrl: "http://localhost:3000"
});

const trace = langfuse.trace({
  name: "my_trace",
  userId: "user-123"
});

const generation = trace.generation({
  name: "llm_call",
  model: "gpt-4",
  input: "Hello",
  output: "Hi there!"
});

trace.score({
  name: "quality",
  value: 0.9
});
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | Change port: `LANGFUSE_PORT=3001 docker compose up` |
| Can't connect to database | Check PostgreSQL health: `docker compose logs postgres` |
| Web page won't load | Check web service logs: `docker compose logs langfuse-web` |
| Worker jobs backing up | Scale workers: `docker compose up -d --scale langfuse-worker=5` |
| High memory usage | Check container stats: `docker stats` |
| API returning 500 errors | Check database: `docker compose exec postgres pg_isready` |

## Performance Tuning

```yaml
# Scale workers for high throughput
services:
  langfuse-worker:
    deploy:
      replicas: 5

# Increase resources
langfuse-web:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 8G

# Optimize Redis
redis:
  command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

## Common Ports

```
3000   - Langfuse Web UI
3030   - Langfuse Worker (async jobs)
5432   - PostgreSQL
8123   - ClickHouse HTTP API
9000   - ClickHouse Native Protocol
6379   - Redis
9000   - MinIO API
9001   - MinIO Web Console
```

## Backup & Restore

```bash
# Backup everything
docker compose exec postgres pg_dump -U langfuse langfuse | gzip > backup-$(date +%Y%m%d).sql.gz

# Restore
gunzip < backup-20240101.sql.gz | docker compose exec -T postgres psql -U langfuse langfuse

# Backup volumes
tar czf langfuse-backup-$(date +%Y%m%d).tar.gz langfuse_*_data/

# Restore volumes
tar xzf langfuse-backup-20240101.tar.gz
```

## Cleanup

```bash
# Remove stopped containers
docker compose -f langfuse.compose.yml rm

# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune

# Remove everything (WARNING: deletes all data)
docker compose -f langfuse.compose.yml down -v
```

## Security Checklist

- [ ] Change all default passwords in `.env`
- [ ] Generate new `NEXTAUTH_SECRET`: `openssl rand -base64 32`
- [ ] Set `NEXTAUTH_URL` to your domain
- [ ] Disable public signups if needed: `NEXT_PUBLIC_SIGN_UP_DISABLED=true`
- [ ] Use HTTPS for production
- [ ] Backup database regularly
- [ ] Monitor for security updates
- [ ] Restrict database access to internal networks
- [ ] Use strong passwords for all services
- [ ] Keep Docker images updated

## Documentation Links

- Docs: https://langfuse.com/docs
- Self-Hosting: https://langfuse.com/docs/deployment/self-host
- API Reference: https://langfuse.com/docs/api
- GitHub: https://github.com/langfuse/langfuse
- Discord: https://discord.com/invite/7NXusRtqYU

---

**Langfuse 3.0** - Open source LLM observability platform  
Last updated: October 17, 2025
