# Langfuse 3.0 Deployment Guide

Open-source LLM observability platform for production deployments.

**Langfuse enables:**
- 🔍 LLM Application Observability: Trace and debug LLM calls
- 📝 Prompt Management: Version control and collaborative prompt development
- 📊 Evaluations: LLM-as-judge, manual labeling, custom pipelines
- 🎯 Datasets: Benchmark and test sets for evaluation
- ▶️ Playground: Interactive prompt development and testing

---

## 📦 Architecture Overview

### Services

| Service | Purpose | Technology | Port |
|---------|---------|-----------|------|
| **langfuse-web** | Frontend UI + REST/tRPC APIs | Next.js 14 | 3000 |
| **langfuse-worker** | Async job processing | Express.js + BullMQ | 3030 |
| **postgres** | Primary database | PostgreSQL 16 | 5432 |
| **clickhouse** | Analytics database | ClickHouse | 8123 |
| **redis** | Cache & queues | Redis 7 | 6379 |
| **minio** | Object storage | MinIO | 9000 |

### Data Flow

```
Client Applications
    ↓
[Langfuse API] (langfuse-web)
    ↓
[Job Queue] (Redis/BullMQ)
    ↓
[Worker] (langfuse-worker)
    ↓
[PostgreSQL] + [ClickHouse] + [MinIO]
    ↓
[Web UI Dashboard] (Next.js Frontend)
```

---

## 🚀 Quick Start (5 minutes)

### 1. Prerequisites

- Docker & Docker Compose (v2.0+)
- At least 4GB RAM
- 10GB disk space
- Port availability: 3000, 3030, 5432, 8123, 6379, 9000, 9001

### 2. Clone Configuration

```bash
# Navigate to monitor directory
cd monitor

# Copy configuration files
cp ..env.langfuse.example .env
```

### 3. Customize Environment

Edit `.env` file with your settings:

```bash
# Generate secure secrets
NEXTAUTH_SECRET=$(openssl rand -base64 32)

# Update .env
POSTGRES_PASSWORD=your-secure-password
CLICKHOUSE_PASSWORD=your-secure-password
REDIS_PASSWORD=your-secure-password
NEXTAUTH_SECRET=$NEXTAUTH_SECRET
NEXTAUTH_URL=http://localhost:3000
```

### 4. Start Services

```bash
# Start all services
docker compose -f langfuse.compose.yml up -d

# Wait for initialization (30-60 seconds)
docker compose -f langfuse.compose.yml logs -f langfuse-web

# You should see: "ready started server on 0.0.0.0:3000"
```

### 5. Access Langfuse

- **Web UI**: http://localhost:3000
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin123)
- **Create Account**: Sign up with any email

### 6. Generate API Keys

1. Log in to Langfuse
2. Create a new project
3. Go to Settings → API Keys
4. Copy `Public Key` (pk-lf-...) and `Secret Key` (sk-lf-...)

### 7. Test Integration

**Python Example:**

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="http://localhost:3000"
)

# Create a trace
trace = langfuse.trace(
    name="user_query",
    user_id="user-123"
)

# Log LLM call
generation = trace.generation(
    name="llm_call",
    model="gpt-4",
    input="What is the capital of France?",
    output="The capital of France is Paris."
)

trace.score(name="quality", value=0.9)
```

**JavaScript/TypeScript:**

```typescript
import Langfuse from "langfuse";

const langfuse = new Langfuse({
  publicKey: "pk-lf-...",
  secretKey: "sk-lf-...",
  baseUrl: "http://localhost:3000"
});

const trace = langfuse.trace({
  name: "user_query",
  userId: "user-123"
});

const generation = trace.generation({
  name: "llm_call",
  model: "gpt-4",
  input: "What is the capital of France?",
  output: "The capital of France is Paris."
});

trace.score({
  name: "quality",
  value: 0.9
});
```

---

## 🛑 Stop Services

```bash
# Stop all running services (keeps data)
docker compose -f langfuse.compose.yml down

# Remove all services and volumes (WARNING: deletes all data)
docker compose -f langfuse.compose.yml down -v
```

---

## 📋 Common Commands

### View Logs

```bash
# All services
docker compose -f langfuse.compose.yml logs -f

# Specific service
docker compose -f langfuse.compose.yml logs -f langfuse-web
docker compose -f langfuse.compose.yml logs -f langfuse-worker
docker compose -f langfuse.compose.yml logs -f postgres

# Last 100 lines
docker compose -f langfuse.compose.yml logs --tail=100 langfuse-web

# Follow with timestamps
docker compose -f langfuse.compose.yml logs -f --timestamps
```

### Check Service Health

```bash
# List running containers
docker compose -f langfuse.compose.yml ps

# Check database connectivity
docker compose -f langfuse.compose.yml exec postgres pg_isready

# Check Redis connectivity
docker compose -f langfuse.compose.yml exec redis redis-cli ping

# Check ClickHouse connectivity
docker compose -f langfuse.compose.yml exec clickhouse curl localhost:8123/ping
```

### Restart Services

```bash
# Restart specific service
docker compose -f langfuse.compose.yml restart langfuse-web

# Restart all services
docker compose -f langfuse.compose.yml restart

# Soft restart (stop -> wait -> start)
docker compose -f langfuse.compose.yml down
docker compose -f langfuse.compose.yml up -d
```

### Database Access

```bash
# Connect to PostgreSQL
docker compose -f langfuse.compose.yml exec postgres psql -U langfuse -d langfuse

# Useful PostgreSQL commands:
# \dt              - list tables
# \du              - list users
# SELECT COUNT(*) FROM traces;
# \q              - exit

# Connect to ClickHouse
docker compose -f langfuse.compose.yml exec clickhouse clickhouse-client

# Useful ClickHouse commands:
# SHOW TABLES;
# SELECT COUNT(*) FROM traces;
# EXIT;
```

### Monitor Performance

```bash
# Real-time stats
docker stats

# Memory usage
docker compose -f langfuse.compose.yml stats

# Disk usage
du -sh langfuse_*_data/

# Docker logs size
docker system df
```

---

## 🔒 Production Deployment

### 1. Security Hardening

```env
# Use strong secrets
NEXTAUTH_SECRET=your-very-secure-random-secret-here-32-chars-min
POSTGRES_PASSWORD=your-secure-postgres-password
CLICKHOUSE_PASSWORD=your-secure-clickhouse-password
REDIS_PASSWORD=your-secure-redis-password

# Enable HTTPS only
NEXTAUTH_URL=https://langfuse.yourdomain.com

# Restrict signups
NEXT_PUBLIC_SIGN_UP_DISABLED=true

# Disable telemetry if desired
TELEMETRY_ENABLED=false
```

### 2. Database Setup

**Option A: AWS RDS (Recommended for Production)**

```env
# Update docker-compose.yml:
# Replace postgres service with external database
DATABASE_URL=postgresql://username:password@rds-instance.amazonaws.com:5432/langfuse
```

**Option B: Self-Hosted PostgreSQL Cluster**

```bash
# Enable replication in PostgreSQL
# Use pgBackRest for backups
# Implement WAL archiving
```

### 3. ClickHouse Configuration

**Option A: ClickHouse Cloud (Recommended)**

```env
# Use managed ClickHouse Cloud
CLICKHOUSE_URL=https://your-instance.us-east-1.aws.clickhouse.cloud:8443
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your-password
```

**Option B: Self-Hosted ClickHouse Cluster**

```yaml
# Enable ClickHouse cluster replication
CLICKHOUSE_CLUSTER_ENABLED=true
CLICKHOUSE_CLUSTER_NAME=langfuse_cluster
```

### 4. Redis Configuration

**Option A: AWS ElastiCache (Recommended)**

```env
# AWS ElastiCache Redis
REDIS_URL=redis://:password@your-elasticache-endpoint:6379
```

**Option B: Redis Cluster**

```bash
# Deploy Redis Cluster for HA
# Configure sentinel for failover
```

### 5. Load Balancing

**Nginx Example:**

```nginx
upstream langfuse_backend {
    server langfuse-web-1:3000;
    server langfuse-web-2:3000;
    server langfuse-web-3:3000;
}

server {
    listen 443 ssl http2;
    server_name langfuse.yourdomain.com;
    
    ssl_certificate /etc/ssl/certs/your-cert.crt;
    ssl_certificate_key /etc/ssl/private/your-key.key;
    
    location / {
        proxy_pass http://langfuse_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_buffering off;
    }
}
```

### 6. Monitoring & Alerts

```bash
# Monitor with Prometheus
# Add metrics collection to docker-compose.yml

# Set up alerts for:
# - High error rates
# - Database connection pool exhaustion
# - Redis memory pressure
# - ClickHouse disk usage
# - Worker job queue depth
```

### 7. Backup Strategy

```bash
#!/bin/bash
# Daily PostgreSQL backup
docker compose exec postgres pg_dump -U langfuse langfuse | gzip > backup-$(date +%Y%m%d).sql.gz

# ClickHouse backup
docker compose exec clickhouse clickhouse-backup create

# Upload to S3
aws s3 cp backup-*.sql.gz s3://my-backups/
```

### 8. Kubernetes Deployment

For production Kubernetes deployments:

```bash
# Use Helm chart
helm repo add langfuse https://helm.langfuse.com
helm repo update
helm install langfuse langfuse/langfuse \
  --namespace langfuse \
  --values values.yaml
```

See: https://langfuse.com/self-hosting/kubernetes-helm

---

## 🔄 Scaling

### Horizontal Scaling - Multiple Web Instances

```yaml
# docker-compose-prod.yml
services:
  langfuse-web-1:
    image: ghcr.io/langfuse/langfuse:latest
    environment:
      # Same env vars
    ports:
      - "3001:3000"
  
  langfuse-web-2:
    image: ghcr.io/langfuse/langfuse:latest
    environment:
      # Same env vars
    ports:
      - "3002:3000"
  
  langfuse-web-3:
    image: ghcr.io/langfuse/langfuse:latest
    environment:
      # Same env vars
    ports:
      - "3003:3000"

# Add load balancer (Nginx, HAProxy, or cloud LB)
```

### Horizontal Scaling - Multiple Workers

```bash
# Scale workers for high trace ingestion
docker compose -f langfuse.compose.yml up -d --scale langfuse-worker=5

# With docker-compose version 2.0+
docker compose up -d --scale langfuse-worker=5
```

### Vertical Scaling

```yaml
# Increase resource limits
langfuse-web:
  # ...
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 8G
      reservations:
        cpus: '2'
        memory: 4G
```

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# List processes on port
lsof -i :3000

# Kill process
kill -9 <PID>

# Or use different port
LANGFUSE_PORT=3001 docker compose up
```

### Database Connection Failed

```bash
# Test PostgreSQL connection
docker compose exec postgres psql -U langfuse -d langfuse -c "SELECT 1"

# Check logs
docker compose logs postgres

# Reset database
docker compose down -v  # WARNING: deletes data
docker compose up
```

### High Memory Usage

```bash
# Check memory stats
docker stats

# Reduce Redis memory
# In docker-compose.yml, reduce maxmemory setting

# Check for memory leaks in logs
docker compose logs langfuse-web | grep -i memory
```

### Worker Jobs Backing Up

```bash
# Check Redis queue depth
docker compose exec redis redis-cli -a [password] LLEN "bull:trace-upsert-queue:jobs"

# Scale more workers
docker compose up -d --scale langfuse-worker=10

# Check worker logs
docker compose logs -f langfuse-worker
```

### API Returning 500 Errors

```bash
# Check web service logs
docker compose logs -f langfuse-web

# Test database connection
docker compose exec postgres pg_isready

# Test ClickHouse connection
docker compose logs clickhouse | grep -i error

# Restart services
docker compose restart langfuse-web
```

### Slow API Response

```bash
# Check database performance
docker compose exec postgres psql -U langfuse langfuse
# SELECT pg_stat_statements_reset(); -- Reset stats
# SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC;

# Monitor ClickHouse performance
docker compose exec clickhouse clickhouse-client
# SYSTEM TABLE system.query_log
```

---

## 📊 Monitoring & Observability

### Built-in Telemetry

Langfuse sends anonymous telemetry to help improve the platform:

```bash
# Opt-out (if desired)
TELEMETRY_ENABLED=false
```

### External Monitoring

**With Prometheus + Grafana:**

```yaml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
  depends_on:
    - prometheus
```

### Log Aggregation

Send logs to ELK Stack, Datadog, or similar:

```bash
# Docker logging driver
docker run --log-driver splunk \
  --log-opt splunk-token=$SPLUNK_TOKEN \
  --log-opt splunk-url=$SPLUNK_URL
```

---

## 📝 Configuration Reference

### Environment Variables

**Core:**
- `NODE_ENV` - Environment (production/development)
- `DATABASE_URL` - PostgreSQL connection string
- `NEXTAUTH_SECRET` - NextAuth.js secret (min 32 chars)
- `NEXTAUTH_URL` - Application URL for OAuth callbacks

**ClickHouse:**
- `CLICKHOUSE_URL` - ClickHouse connection
- `CLICKHOUSE_HOST` - ClickHouse hostname
- `CLICKHOUSE_USER` - ClickHouse username
- `CLICKHOUSE_PASSWORD` - ClickHouse password

**Redis:**
- `REDIS_URL` - Redis connection string
- `REDIS_HOST` - Redis hostname
- `REDIS_PORT` - Redis port
- `REDIS_PASSWORD` - Redis password

**Storage (S3/MinIO):**
- `LANGFUSE_S3_ENDPOINT` - S3 endpoint URL
- `LANGFUSE_S3_REGION` - AWS region
- `LANGFUSE_S3_ACCESS_KEY_ID` - S3 access key
- `LANGFUSE_S3_SECRET_ACCESS_KEY` - S3 secret key

**Features:**
- `TELEMETRY_ENABLED` - Enable/disable telemetry
- `NEXT_PUBLIC_SIGN_UP_DISABLED` - Disable public signups

---

## 🔗 Integration Examples

### With LiteLLM

```yaml
# In your litellm_config.yaml
guardrails:
  - id: "langfuse-tracing"
    type: "langfuse"
    config:
      public_key: "${LANGFUSE_PUBLIC_KEY}"
      secret_key: "${LANGFUSE_SECRET_KEY}"
      host: "http://langfuse:3000"
```

### With LangChain

```python
from langfuse.callback import CallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain

handler = CallbackHandler(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="http://localhost:3000"
)

llm = ChatOpenAI()
chain = LLMChain(llm=llm)

result = chain.run(
    ...,
    callbacks=[handler]
)
```

### With LlamaIndex

```python
from llama_index.callbacks import CallbackManager
from langfuse.llama_index import LangfuseCallbackHandler

callback_handler = LangfuseCallbackHandler(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="http://localhost:3000"
)

callback_manager = CallbackManager([callback_handler])
Settings.callback_manager = callback_manager
```

---

## 📚 Additional Resources

- **Official Documentation**: https://langfuse.com/docs
- **Self-Hosting Guide**: https://langfuse.com/docs/deployment/self-host
- **GitHub Repository**: https://github.com/langfuse/langfuse
- **Discord Community**: https://discord.com/invite/7NXusRtqYU
- **GitHub Discussions**: https://github.com/orgs/langfuse/discussions
- **API Documentation**: https://langfuse.com/docs/api

---

## 📄 License

Langfuse is open source under the MIT License. See:
- GitHub: https://github.com/langfuse/langfuse/blob/main/LICENSE
- Website: https://langfuse.com/docs/open-source

---

**Last Updated**: October 17, 2025  
**Langfuse Version**: 3.0+  
**Docker Compose Version**: 2.0+
