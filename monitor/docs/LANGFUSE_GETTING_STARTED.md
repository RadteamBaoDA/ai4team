# 🎯 Langfuse 3.0 - Getting Started Guide

## 📦 What You Have

Complete production-ready Docker Compose deployment for **Langfuse 3.0** - the open-source LLM observability platform.

### 5 Files Created in `monitor/` directory:

```
monitor/
│
├── 🐳 langfuse.compose.yml
│   └─ Main Docker Compose file with all 6 services
│     - Langfuse Web (UI + API)
│     - Langfuse Worker (async jobs)
│     - PostgreSQL (database)
│     - ClickHouse (analytics)
│     - Redis (cache/queue)
│     - MinIO (storage)
│
├── ⚙️ .env.langfuse.example
│   └─ Environment configuration template
│     - Database credentials
│     - Storage settings
│     - API secrets
│     - Optional integrations
│
├── 📖 LANGFUSE_DEPLOYMENT.md
│   └─ Comprehensive deployment guide (800+ lines)
│     - Architecture overview
│     - Quick start
│     - Production setup
│     - Security hardening
│     - Scaling strategies
│     - Troubleshooting
│
├── ⚡ LANGFUSE_QUICKREF.md
│   └─ Quick reference card (300+ lines)
│     - Common commands
│     - Quick lookup
│     - Code examples
│     - Troubleshooting table
│
└── 📋 LANGFUSE_PACKAGE_SUMMARY.md
    └─ This package overview
```

---

## 🚀 Quick Start (5 Minutes)

### 1. Copy Configuration

```bash
cd d:\Project\ai4team\monitor
cp .env.langfuse.example .env
```

### 2. Customize Environment (Optional)

Edit `.env` file:
```env
POSTGRES_PASSWORD=your-secure-password
CLICKHOUSE_PASSWORD=your-secure-password
REDIS_PASSWORD=your-secure-password
NEXTAUTH_SECRET=your-secret-min-32-chars
NEXTAUTH_URL=http://localhost:3000
```

**To generate a secure secret:**
```bash
openssl rand -base64 32
```

### 3. Start All Services

```bash
docker compose -f langfuse.compose.yml up -d
```

### 4. Wait for Startup

```bash
docker compose -f langfuse.compose.yml logs -f langfuse-web
```

Look for: `"ready started server on 0.0.0.0:3000"`

### 5. Access Langfuse

- **Web UI**: http://localhost:3000
- **MinIO Console**: http://localhost:9001
- **Sign up**: Create your first account

### 6. Generate API Keys

1. Log in to Langfuse
2. Create a new project
3. Go to Settings → API Keys
4. Copy `pk-lf-...` (public) and `sk-lf-...` (secret)

---

## 📚 Documentation Guide

### 📖 LANGFUSE_DEPLOYMENT.md
**When to use:** Full reference for all deployment scenarios

**Read for:**
- Architecture & data flow
- Production deployment
- Security hardening
- Database setup (RDS, ClickHouse Cloud)
- Load balancing
- Kubernetes deployment
- Scaling strategies
- Troubleshooting
- Integration examples

**Length:** 800+ lines  
**Time to read:** 30-45 minutes

### ⚡ LANGFUSE_QUICKREF.md
**When to use:** Quick lookup for common tasks

**Read for:**
- How do I start services?
- How do I view logs?
- How do I access the database?
- Code examples
- Quick troubleshooting table

**Length:** 300+ lines  
**Time to read:** 5-10 minutes

---

## 🎯 What Can You Do With Langfuse?

### 🔍 Tracing & Observability
```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="http://localhost:3000"
)

# Trace your LLM calls
trace = langfuse.trace(name="user_query", user_id="user-123")
trace.generation(
    name="llm_call",
    model="gpt-4",
    input="What is AI?",
    output="AI is..."
)
```

### 📝 Prompt Management
- Version control prompts
- Collaborate with team
- Track prompt changes
- Test variations

### 📊 Evaluations
- Create test datasets
- Run evaluations
- Score outputs
- Track metrics

### 🎮 Interactive Playground
- Test prompts live
- Adjust parameters
- See results instantly
- Iterate fast

---

## 🔄 Integration Examples

### With LangChain
```python
from langfuse.callback import CallbackHandler

handler = CallbackHandler(
    public_key="pk-lf-...",
    secret_key="sk-lf-..."
)

chain.invoke(..., config={"callbacks": [handler]})
```

### With LiteLLM
```yaml
guardrails:
  - id: "langfuse"
    type: "custom_guardrail"
    host: "http://langfuse:3000"
```

### With LlamaIndex
```python
from llama_index.callbacks import CallbackManager
from langfuse.llama_index import LangfuseCallbackHandler

handler = LangfuseCallbackHandler(
    public_key="pk-lf-...",
    secret_key="sk-lf-..."
)
Settings.callback_manager = CallbackManager([handler])
```

---

## 💻 Common Commands

### Start/Stop

```bash
# Start all services
docker compose -f langfuse.compose.yml up -d

# Stop services (keep data)
docker compose -f langfuse.compose.yml down

# Stop and delete everything
docker compose -f langfuse.compose.yml down -v
```

### View Logs

```bash
# All services
docker compose -f langfuse.compose.yml logs -f

# Specific service
docker compose -f langfuse.compose.yml logs -f langfuse-web
docker compose -f langfuse.compose.yml logs -f langfuse-worker
```

### Database Operations

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U langfuse -d langfuse

# Backup database
docker compose exec postgres pg_dump -U langfuse langfuse | gzip > backup.sql.gz

# Check database size
docker compose exec postgres psql -U langfuse langfuse \
  -c "SELECT pg_size_pretty(pg_database_size('langfuse'));"
```

### Monitoring

```bash
# Check service status
docker compose -f langfuse.compose.yml ps

# Resource usage
docker compose stats

# Disk usage
du -sh langfuse_*_data/
```

---

## 🔒 Security Quick Checklist

For **development/testing:**
- ✓ Use default .env values
- ✓ Access only via localhost
- ✓ No external exposure

For **production:**
- ✓ Change all passwords
- ✓ Generate new `NEXTAUTH_SECRET`
- ✓ Use HTTPS with valid SSL cert
- ✓ Set `NEXTAUTH_URL` to your domain
- ✓ Disable public signups
- ✓ Use managed databases (RDS, ClickHouse Cloud)
- ✓ Enable backups
- ✓ Monitor logs
- ✓ Restrict network access
- ✓ Regular security updates

---

## 📊 Architecture at a Glance

```
Your Applications
      ↓
[Langfuse Web] → HTTP API (port 3000)
      ↓
   [Worker] → Async Jobs
      ↓
[PostgreSQL] + [ClickHouse] + [MinIO]
      ↓
[Dashboard] → View Traces & Analyze
```

---

## ❓ FAQ

**Q: How long to set up?**  
A: 5 minutes for basic setup, includes all services running.

**Q: Do I need all 6 services?**  
A: Yes, all are required for full functionality. PostgreSQL + ClickHouse + Redis are non-negotiable.

**Q: Can I use AWS services?**  
A: Yes! Use AWS RDS for PostgreSQL, ClickHouse Cloud, ElastiCache for Redis, S3 for storage.

**Q: How much storage do I need?**  
A: Start with 20-30GB. PostgreSQL (1-5GB), ClickHouse (5-50GB), MinIO (10-100GB).

**Q: Can I scale it?**  
A: Yes! Scale workers, use managed databases, add load balancer.

**Q: What about backups?**  
A: Included in guide. Daily PostgreSQL backups recommended.

**Q: Is it production-ready?**  
A: Yes! With proper configuration, security hardening, and monitoring.

---

## 🎓 Learning Path

### Phase 1: Get Started (30 min)
1. ✅ Run `docker compose up -d`
2. ✅ Access http://localhost:3000
3. ✅ Create account & project
4. ✅ Generate API keys

### Phase 2: Integrate (1-2 hours)
1. ✅ Install Langfuse SDK
2. ✅ Add tracing to your app
3. ✅ View traces in dashboard
4. ✅ Create evaluations

### Phase 3: Advanced (1-2 days)
1. ✅ Set up prompt management
2. ✅ Create datasets
3. ✅ Configure evaluations
4. ✅ Build dashboards

### Phase 4: Production (1-2 weeks)
1. ✅ Security hardening
2. ✅ Database backups
3. ✅ Monitoring setup
4. ✅ Performance tuning
5. ✅ High availability

---

## 📞 Getting Help

| Issue | Solution |
|-------|----------|
| Port in use | `LANGFUSE_PORT=3001 docker compose up` |
| Won't start | Check logs: `docker compose logs langfuse-web` |
| Can't connect | Verify database: `docker compose logs postgres` |
| Slow performance | Read scaling section in deployment guide |
| Data lost | Set up backups (see guide) |

---

## 📂 File Organization

Your `monitor/` directory now contains:

```
monitor/
├── langfuse.compose.yml          ← START HERE (run: docker compose up -d)
├── .env.langfuse.example         ← Copy to .env and customize
├── LANGFUSE_DEPLOYMENT.md        ← Read for complete guide
├── LANGFUSE_QUICKREF.md          ← Use for quick lookup
└── LANGFUSE_PACKAGE_SUMMARY.md   ← Overview (you are here!)
```

---

## ✨ Next Steps

### Immediate (Now)
1. Run `docker compose -f langfuse.compose.yml up -d`
2. Access http://localhost:3000
3. Create account and project

### Short-term (Today)
1. Generate API keys
2. Install Langfuse SDK
3. Add tracing to one app
4. View traces in dashboard

### Medium-term (This Week)
1. Integrate multiple services
2. Set up evaluations
3. Create dashboards
4. Explore all features

### Long-term (This Month)
1. Plan production deployment
2. Security hardening
3. Backup strategy
4. Monitoring setup
5. Team training

---

## 📖 Recommended Reading Order

```
1. THIS FILE (Langfuse_Getting_Started.md)
   ↓
2. LANGFUSE_QUICKREF.md (for command reference)
   ↓
3. LANGFUSE_DEPLOYMENT.md (when deploying to production)
   ↓
4. Official Docs (https://langfuse.com/docs)
```

---

## 🎉 You're All Set!

Everything you need is configured and ready to go:

✅ **Docker Compose Configuration**
- All services configured
- Production-ready defaults
- Health checks included
- Persistence enabled

✅ **Documentation**
- 1,900+ lines of guides
- Code examples included
- Troubleshooting included
- Security best practices

✅ **Ready to Deploy**
- Development: 5 minutes
- Production: Follow guide (1-2 weeks)
- Scaling: Documented
- Support: Links included

---

## 🚀 Start Now

```bash
# Navigate to monitor directory
cd d:\Project\ai4team\monitor

# Copy configuration
cp .env.langfuse.example .env

# Start all services
docker compose -f langfuse.compose.yml up -d

# Wait 30 seconds for startup...

# Access Langfuse
open http://localhost:3000

# Sign up and enjoy! 🎉
```

---

## 📞 Support Resources

- **Documentation**: https://langfuse.com/docs
- **GitHub**: https://github.com/langfuse/langfuse
- **Discord**: https://discord.com/invite/7NXusRtqYU
- **Discussions**: https://github.com/orgs/langfuse/discussions
- **This Deployment**: See `LANGFUSE_DEPLOYMENT.md`

---

**Langfuse 3.0 - Complete Deployment Package**  
Ready to deploy, documented, production-ready  
October 17, 2025

*Happy tracing! 🚀*
