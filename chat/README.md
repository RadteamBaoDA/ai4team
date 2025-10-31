# 💬 Chat - Open-WebUI Distributed Deployment

This directory contains a complete distributed deployment of **Open-WebUI**, a feature-rich web interface for Large Language Models (LLMs) that provides ChatGPT-like functionality with advanced features including RAG (Retrieval Augmented Generation), multi-user support, and comprehensive AI integrations.

## 🎯 What is Open-WebUI?

Open-WebUI is an extensible, feature-rich, and user-friendly self-hosted WebUI designed to operate entirely offline. It supports various LLM runners, including Ollama and OpenAI-compatible APIs.

### Key Features

- **💬 ChatGPT-like Interface** - Intuitive conversational UI with modern design
- **🔍 RAG Integration** - Document upload, processing, and retrieval-augmented generation
- **👥 Multi-user Support** - User authentication, roles, and collaborative workspaces
- **🧠 Vector Database** - Qdrant integration for semantic search and embeddings
- **📊 Database Persistence** - PostgreSQL for reliable data storage
- **⚡ Real-time Features** - WebSocket support via Redis for live chat updates
- **☁️ Cloud Storage** - S3-compatible storage integration
- **🔐 OAuth Integration** - Microsoft OAuth and other identity providers
- **📱 Responsive Design** - Mobile-friendly interface
- **🎨 Customizable** - Themes, branding, and extensive configuration options

## 📁 Directory Structure

```
chat/
├── README.md                 # This file
├── master.compose.yaml       # Master node with full stack (WebUI + DB + Redis + Vector DB)
├── slave.compose.yaml        # Slave node (WebUI only, connects to master services)
├── .env.master              # Master node environment configuration
├── .env.slave               # Slave node environment configuration
└── chat.conf                # Nginx load balancer configuration
```

## 🏗️ Architecture Overview

The deployment consists of a distributed setup with master-slave architecture:

### **Master Node Components**
- **Open-WebUI**: Main web application and API server
- **PostgreSQL**: Primary database for users, conversations, and metadata
- **Redis**: Cache, session storage, and WebSocket message broker
- **Qdrant**: Vector database for RAG functionality and embeddings
- **S3 Storage**: MinIO integration for file and document storage

### **Slave Node Components**
- **Open-WebUI**: Load-balanced web application instances
- **Connection to Master**: Shared database, Redis, and vector store

```mermaid
graph TB
    Users[Users] --> LB[Nginx Load Balancer<br/>chat1.baoda.live]
    
    LB --> Master[Master Node<br/>192.168.1.14:3011]
    LB --> Slave[Slave Node<br/>192.168.1.21:3011]
    
    Master --> OpenWebUI1[Open-WebUI Container<br/>Master Instance]
    Slave --> OpenWebUI2[Open-WebUI Container<br/>Slave Instance]
    
    OpenWebUI1 --> PostgreSQL[(PostgreSQL Database<br/>Users & Conversations)]
    OpenWebUI1 --> Redis[(Redis Cache<br/>Sessions & WebSocket)]
    OpenWebUI1 --> Qdrant[(Qdrant Vector DB<br/>RAG & Embeddings)]
    OpenWebUI1 --> S3[(S3 Storage<br/>Documents & Files)]
    
    OpenWebUI2 -.->|Shared Services| PostgreSQL
    OpenWebUI2 -.->|Shared Services| Redis
    OpenWebUI2 -.->|Shared Services| Qdrant
    OpenWebUI2 -.->|Shared Services| S3
```

### **Port Configuration**

| Service | Master Port | Slave Port | Purpose |
|---------|-------------|------------|---------|
| Open-WebUI | 3011 | 3011 | Web interface |
| PostgreSQL | 5432 | - | Database access |
| Redis | 6379 | - | Cache & WebSocket |
| Qdrant API | 6333 | - | Vector database |
| Qdrant gRPC | 6334 | - | High-performance queries |
| Nginx LB | 80 | - | Load balanced access |

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Network connectivity between master and slave nodes
- At least 4GB RAM per node (8GB recommended for master)
- Sufficient disk space for data storage (20GB+ recommended)

### Step 1: Configure Network and Environment

#### Update IP Addresses

**Master Node** (`master.compose.yaml`):
```yaml
extra_hosts:
  - "s3.ai4team.vn:192.168.1.14"   # Update with S3 server IP
```

**Slave Node** (`slave.compose.yaml`):
```yaml
extra_hosts:
  - "master-chat:192.168.1.14"     # Update with master IP
  - "s3.ai4team.vn:192.168.1.14"   # Update with S3 server IP
```

#### Configure Environment Files

**Master Node** (`.env.master`):
```bash
# Generate secure secret key
WEBUI_SECRET_KEY=$(openssl rand -hex 32)

# Update S3 credentials
S3_SECRET_ACCESS_KEY=your-s3-secret-key

# Configure OAuth (optional)
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
```

**Slave Node** (`.env.slave`):
```bash
# Use SAME secret key as master
WEBUI_SECRET_KEY=same-as-master-key

# Update S3 credentials
S3_SECRET_ACCESS_KEY=your-s3-secret-key
```

### Step 2: Deploy Master Node

```bash
# On master server (192.168.1.14)
cd d:\Project\ai4team\chat

# Create data directories
mkdir -p openwebui-data postgresql/data qdrant/storage qdrant/config qdrant/snapshots

# Start master services
docker-compose -f master.compose.yaml up -d

# Monitor startup
docker-compose -f master.compose.yaml logs -f
```

### Step 3: Deploy Slave Node

```bash
# On slave server (192.168.1.21)
cd /path/to/chat

# Create data directory
mkdir -p openwebui-data

# Start slave services
docker-compose -f slave.compose.yaml up -d

# Monitor startup
docker-compose -f slave.compose.yaml logs -f
```

### Step 4: Configure Load Balancer

```bash
# Install Nginx (on load balancer server)
sudo apt update && sudo apt install nginx

# Copy configuration
sudo cp chat.conf /etc/nginx/sites-available/chat.conf

# Update server IPs in chat.conf
sudo nano /etc/nginx/sites-available/chat.conf

# Enable site
sudo ln -s /etc/nginx/sites-available/chat.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 5: Access Open-WebUI

- **Load Balanced**: http://chat1.baoda.live
- **Master Direct**: http://192.168.1.14:3011  
- **Slave Direct**: http://192.168.1.21:3011

## 🔧 Configuration Options

### Environment Variables (.env files)

#### Core Application Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `CUSTOM_NAME` | Application branding name | PrivateGPT Radteam |
| `WEBUI_NAME` | Web interface title | PrivateGPT Radteam |
| `WEBUI_URL` | Public URL for the application | https://chat1.baoda.live |
| `WEBUI_SECRET_KEY` | JWT signing secret (must be same across nodes) | Generated |
| `JWT_EXPIRES_IN` | JWT token expiration | 7d |
| `ENV` | Environment mode | prod |

#### Database Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | postgresql://postgres:openwebui@openwebui-db:5432/openwebui_db |
| `REDIS_URL` | Redis connection string | redis://openwebui-redis:6379/0 |
| `WEBSOCKET_REDIS_URL` | Redis for WebSocket messaging | redis://openwebui-redis:6379/0 |

#### Vector Database (Qdrant)

| Variable | Description | Default |
|----------|-------------|---------|
| `VECTOR_DB` | Vector database type | qdrant |
| `QDRANT_URI` | Qdrant connection URL | http://openwebui-vectordb:6333 |
| `QDRANT_ON_DISK` | Enable disk persistence | True |
| `QDRANT_PREFER_GRPC` | Use gRPC for better performance | True |
| `QDRANT_TIMEOUT` | Query timeout in seconds | 30 |
| `ENABLE_QDRANT_MULTITENANCY_MODE` | Multi-user vector isolation | True |

#### S3 Storage Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `STORAGE_PROVIDER` | Storage backend | s3 |
| `S3_ENDPOINT_URL` | S3 API endpoint | http://s3.ai4team.vn |
| `S3_ACCESS_KEY_ID` | S3 access key | minioadmin |
| `S3_SECRET_ACCESS_KEY` | S3 secret key | (required) |
| `S3_BUCKET_NAME` | S3 bucket for files | openwebui |
| `S3_KEY_PREFIX` | File prefix in bucket | openwebui |
| `S3_ENABLE_TAGGING` | Enable S3 object tagging | True |

#### OAuth Integration

| Variable | Description | Required |
|----------|-------------|----------|
| `ENABLE_OAUTH_SIGNUP` | Allow OAuth registration | Optional |
| `OAUTH_MERGE_ACCOUNTS_BY_EMAIL` | Merge accounts by email | Optional |
| `MICROSOFT_CLIENT_ID` | Microsoft OAuth client ID | Optional |
| `MICROSOFT_CLIENT_SECRET` | Microsoft OAuth secret | Optional |
| `MICROSOFT_CLIENT_TENANT_ID` | Microsoft tenant ID | Optional |

#### AI & RAG Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `RAG_EMBEDDING_ENGINE` | Embedding model provider | ollama |
| `AUDIO_STT_ENGINE` | Speech-to-text engine | openai |
| `OFFLINE_MODE` | Run without internet | True |

### Volume Configuration

#### Master Node Volumes
```yaml
volumes:
  - ./openwebui-data:/app/backend/data           # Application data
  - ./postgresql/data:/var/lib/postgresql/data   # Database data
  - ./qdrant/storage:/qdrant/storage            # Vector embeddings
  - ./qdrant/config:/qdrant/config              # Qdrant configuration
  - ./qdrant/snapshots:/qdrant/snapshots        # Database backups
```

#### Slave Node Volumes
```yaml
volumes:
  - ./openwebui-data:/app/backend/data           # Local application data
```

## 🔒 Security Configuration

### Authentication Setup

#### Enable OAuth (Microsoft)

1. **Azure App Registration**:
   ```bash
   # Create app registration in Azure Portal
   # Set redirect URI: https://chat1.baoda.live/oauth/microsoft/callback
   ```

2. **Configure Environment**:
   ```bash
   # In .env.master and .env.slave
   MICROSOFT_CLIENT_ID=your-app-id
   MICROSOFT_CLIENT_SECRET=your-app-secret
   MICROSOFT_CLIENT_TENANT_ID=your-tenant-id
   MICROSOFT_REDIRECT_URI=https://chat1.baoda.live/oauth/microsoft/callback
   ```

#### Generate Secure Keys

```bash
# Generate secret key (use same on all nodes)
WEBUI_SECRET_KEY=$(openssl rand -hex 32)
echo "WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}"

# Generate database password
DB_PASSWORD=$(openssl rand -base64 32)
```

### Network Security

```bash
# Firewall configuration
sudo ufw allow 3011/tcp    # Open-WebUI
sudo ufw allow 80/tcp      # Nginx
sudo ufw allow 443/tcp     # HTTPS

# Restrict database ports to local network
sudo ufw allow from 192.168.1.0/24 to any port 5432
sudo ufw allow from 192.168.1.0/24 to any port 6379
sudo ufw allow from 192.168.1.0/24 to any port 6333
```

### SSL/HTTPS Setup

```bash
# Install Certbot (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx

# Generate SSL certificate
sudo certbot --nginx -d chat1.baoda.live

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 🛠️ Common Operations

### Service Management

```bash
# Start services
docker-compose -f master.compose.yaml up -d
docker-compose -f slave.compose.yaml up -d

# Stop services
docker-compose -f master.compose.yaml down
docker-compose -f slave.compose.yaml down

# Restart specific service
docker-compose -f master.compose.yaml restart web

# View logs
docker-compose -f master.compose.yaml logs -f web
```

### Database Operations

```bash
# Access PostgreSQL
docker exec -it openwebui-db psql -U postgres -d openwebui_db

# Database backup
docker exec openwebui-db pg_dump -U postgres openwebui_db | gzip > backup-$(date +%Y%m%d).sql.gz

# Database restore
gunzip -c backup-20241031.sql.gz | docker exec -i openwebui-db psql -U postgres -d openwebui_db
```

### Redis Operations

```bash
# Access Redis CLI
docker exec -it openwebui-redis redis-cli

# Monitor Redis activity
docker exec -it openwebui-redis redis-cli monitor

# Clear Redis cache
docker exec -it openwebui-redis redis-cli flushdb
```

### Qdrant Vector Database

```bash
# Check Qdrant health
curl http://192.168.1.14:6333/health

# View collections
curl http://192.168.1.14:6333/collections

# Backup Qdrant data
docker exec openwebui-vectordb qdrant-backup create backup-$(date +%Y%m%d)
```

### File Storage Management

```bash
# Check S3 storage usage
docker exec minio-client mc du s3/openwebui

# List uploaded files
docker exec minio-client mc ls s3/openwebui/files/

# Cleanup old files (optional)
docker exec minio-client mc rm --recursive --force --older-than 30d s3/openwebui/temp/
```

## 📊 Monitoring & Health Checks

### Application Health

```bash
# Check all container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Health check endpoints
curl http://192.168.1.14:3011/health        # Open-WebUI master
curl http://192.168.1.21:3011/health        # Open-WebUI slave
curl http://192.168.1.14:6333/health        # Qdrant
```

### Performance Monitoring

```bash
# Container resource usage
docker stats --no-stream

# Database performance
docker exec openwebui-db psql -U postgres -d openwebui_db -c "
SELECT schemaname,tablename,attname,n_distinct,correlation 
FROM pg_stats WHERE tablename='conversations' 
ORDER BY n_distinct DESC;"

# Redis memory usage
docker exec openwebui-redis redis-cli info memory
```

### Log Monitoring

```bash
# Real-time logs from all services
docker-compose -f master.compose.yaml logs -f

# Search for errors
docker-compose -f master.compose.yaml logs | grep -i error

# Application-specific logs
docker logs openwebui --tail=100 -f
```

## 🔌 Integration with AI4Team Platform

### LLM Service Integration

```bash
# Configure Ollama endpoint
OLLAMA_BASE_URL=http://192.168.1.14:11434

# Configure OpenAI-compatible API
OPENAI_API_BASE=http://192.168.1.14:8000/v1
OPENAI_API_KEY=your-api-key
```

### Knowledge Base Integration

```bash
# RAG document processing
RAG_EMBEDDING_ENGINE=ollama
RAG_RERANKING_MODEL=ms-marco-MiniLM-L-12-v2
RAG_TOP_K=5
```

### Guardrails Integration

```bash
# Content filtering
CONTENT_FILTER_ENDPOINT=http://192.168.1.14:8001/filter
ENABLE_CONTENT_FILTERING=True
```

### Monitoring Integration (Langfuse)

```bash
# Observability tracking
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://192.168.1.14:3000
ENABLE_LANGFUSE_TRACING=True
```

## 🚨 Troubleshooting

### Common Issues

| Problem | Symptoms | Solution |
|---------|----------|----------|
| Authentication fails | Login errors, JWT issues | Check `WEBUI_SECRET_KEY` consistency |
| RAG not working | Document upload fails | Verify Qdrant connection and S3 storage |
| Slow performance | High response times | Check database indexes, Redis memory |
| WebSocket errors | Real-time features broken | Verify Redis WebSocket configuration |
| File uploads fail | S3 errors | Check MinIO connectivity and credentials |

### Debug Commands

```bash
# Check service connectivity
docker exec openwebui ping openwebui-db
docker exec openwebui ping openwebui-redis
docker exec openwebui ping openwebui-vectordb

# Check environment variables
docker exec openwebui printenv | grep -E "(DATABASE|REDIS|QDRANT|S3)"

# Test database connection
docker exec openwebui python -c "
import os
import psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
print('Database connection successful')
"

# Test Redis connection
docker exec openwebui python -c "
import os
import redis
r = redis.from_url(os.environ['REDIS_URL'])
print('Redis ping:', r.ping())
"
```

### Performance Tuning

#### Database Optimization
```bash
# Optimize PostgreSQL configuration
docker exec openwebui-db psql -U postgres -d openwebui_db -c "
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
"
```

#### Redis Optimization
```bash
# Configure Redis memory policy
docker exec openwebui-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
docker exec openwebui-redis redis-cli CONFIG SET maxmemory 512mb
```

#### Container Resource Limits
```yaml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

## 📚 User Features & Usage

### Core Functionality

#### Chat Interface
- **Multi-model Support**: Switch between different LLM models
- **Conversation History**: Persistent chat sessions
- **Message Threading**: Organized conversation flow
- **Export/Import**: Backup and restore conversations

#### Document RAG
- **File Upload**: PDF, TXT, DOCX, and more
- **Document Processing**: Automatic chunking and embedding
- **Semantic Search**: Vector-based document retrieval
- **Citation Tracking**: Source attribution in responses

#### User Management
- **Multi-user Support**: Individual user accounts and data isolation
- **Role-based Access**: Admin and user roles
- **OAuth Integration**: Microsoft, Google, and other providers
- **User Preferences**: Customizable interface and settings

#### Advanced Features
- **Model Management**: Download and manage local models
- **Plugin System**: Extend functionality with custom plugins
- **API Access**: REST API for programmatic access
- **Webhook Support**: Integration with external services

### Administrative Features

#### System Configuration
- **Model Settings**: Configure available LLM models
- **User Management**: Create, modify, and delete user accounts
- **System Monitoring**: View usage statistics and performance metrics
- **Backup Management**: Automated backup and restore procedures

## 📋 Production Deployment Checklist

### Security
- [ ] Change default passwords
- [ ] Configure OAuth providers
- [ ] Enable HTTPS/SSL
- [ ] Set up firewall rules
- [ ] Generate secure secret keys
- [ ] Configure content filtering

### High Availability
- [ ] Deploy multiple slave nodes
- [ ] Configure load balancer
- [ ] Set up health checks
- [ ] Plan disaster recovery
- [ ] Test failover scenarios

### Performance
- [ ] Optimize database configuration
- [ ] Configure Redis memory limits
- [ ] Set up monitoring
- [ ] Plan capacity scaling
- [ ] Optimize vector database

### Backup & Recovery
- [ ] Automated database backups
- [ ] Vector database snapshots
- [ ] S3 storage redundancy
- [ ] Test restore procedures
- [ ] Document recovery process

## 📈 Scaling Strategies

### Horizontal Scaling

```bash
# Add additional slave nodes
# Copy slave.compose.yaml to new servers
# Update load balancer configuration
# Add new upstream servers to chat.conf

upstream chat {
    least_conn;
    server 192.168.1.14:3011 max_fails=3 fail_timeout=5s;  # Master
    server 192.168.1.21:3011 max_fails=3 fail_timeout=5s;  # Slave 1
    server 192.168.1.22:3011 max_fails=3 fail_timeout=5s;  # Slave 2
    server 192.168.1.23:3011 max_fails=3 fail_timeout=5s;  # Slave 3
}
```

### Vertical Scaling

```yaml
# Increase container resources
services:
  web:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
  
  db:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

### Database Scaling

```bash
# PostgreSQL read replicas
# Redis Cluster for high availability
# Qdrant cluster deployment
```

---

## 🚀 Get Started

Ready to deploy Open-WebUI for your AI chat platform?

1. **Configure network**: Update IP addresses in compose files
2. **Set environment**: Create and configure `.env` files
3. **Deploy master**: `docker-compose -f master.compose.yaml up -d`
4. **Deploy slaves**: `docker-compose -f slave.compose.yaml up -d`
5. **Setup load balancer**: Configure Nginx with `chat.conf`
6. **Access interface**: https://chat1.baoda.live
7. **Create admin account**: First user becomes admin
8. **Configure models**: Add LLM endpoints and download models
9. **Enable features**: Set up RAG, OAuth, and integrations

For production deployment, follow the security and scaling checklists above.

---

**Open-WebUI Distributed Chat Platform**  
Part of AI4Team Platform  
October 2025