# Concurrency Implementation - Complete Index

## 📚 Documentation Overview

This index provides quick access to all documentation related to the concurrent request handling implementation for the Ollama Guard Proxy.

## 🚀 Quick Start

**For new users:**
1. Read [CONCURRENCY_UPDATE.md](../CONCURRENCY_UPDATE.md) - Overview and quick start
2. Run setup script: `./setup_concurrency.sh` (Linux/Mac) or `setup_concurrency.bat` (Windows)
3. Review [CONCURRENCY_QUICKREF.md](CONCURRENCY_QUICKREF.md) - Essential commands

**For existing users:**
1. Review [CONCURRENCY_IMPLEMENTATION_SUMMARY.md](../CONCURRENCY_IMPLEMENTATION_SUMMARY.md) - What changed
2. Update config.yaml with concurrency settings
3. Restart proxy and monitor with `/health` and `/queue/stats`

## 📖 Core Documentation

### 1. User Guides

| Document | Description | Audience |
|----------|-------------|----------|
| [CONCURRENCY_UPDATE.md](../CONCURRENCY_UPDATE.md) | Feature announcement and overview | All users |
| [CONCURRENCY_GUIDE.md](CONCURRENCY_GUIDE.md) | Complete implementation guide | Developers, Operators |
| [CONCURRENCY_QUICKREF.md](CONCURRENCY_QUICKREF.md) | Quick reference commands | Daily users |
| [CONCURRENCY_TESTING.md](CONCURRENCY_TESTING.md) | Testing and validation guide | QA, DevOps |

### 2. Technical Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| [CONCURRENCY_IMPLEMENTATION_SUMMARY.md](../CONCURRENCY_IMPLEMENTATION_SUMMARY.md) | Technical implementation details | Developers |
| [concurrency.py](../concurrency.py) | Source code with inline documentation | Developers |
| [config.yaml](../config.yaml) | Configuration with concurrency settings | Operators |

## 🎯 Use Cases

### I want to... → Read this

- **Get started quickly** → [CONCURRENCY_UPDATE.md](../CONCURRENCY_UPDATE.md) Quick Start section
- **Understand the implementation** → [CONCURRENCY_GUIDE.md](CONCURRENCY_GUIDE.md) How It Works section
- **Configure my system** → [CONCURRENCY_GUIDE.md](CONCURRENCY_GUIDE.md) Configuration section
- **Monitor performance** → [CONCURRENCY_GUIDE.md](CONCURRENCY_GUIDE.md) Monitoring section
- **Run load tests** → [CONCURRENCY_TESTING.md](CONCURRENCY_TESTING.md) Load Testing section
- **Troubleshoot issues** → [CONCURRENCY_GUIDE.md](CONCURRENCY_GUIDE.md) Troubleshooting section
- **Integrate with my app** → [CONCURRENCY_GUIDE.md](CONCURRENCY_GUIDE.md) Examples section
- **Review what changed** → [CONCURRENCY_IMPLEMENTATION_SUMMARY.md](../CONCURRENCY_IMPLEMENTATION_SUMMARY.md)

## 📋 Setup Checklist

- [ ] Read [CONCURRENCY_UPDATE.md](../CONCURRENCY_UPDATE.md)
- [ ] Run setup script: `./setup_concurrency.sh` or `setup_concurrency.bat`
- [ ] Review and update `config.yaml`
- [ ] Restart proxy
- [ ] Test with `curl http://localhost:8080/health`
- [ ] Check queue stats with `curl http://localhost:8080/queue/stats`
- [ ] Run load tests from [CONCURRENCY_TESTING.md](CONCURRENCY_TESTING.md)
- [ ] Set up monitoring dashboard
- [ ] Configure alerts for queue metrics

## 🔧 Configuration Quick Reference

### Minimal Configuration
```yaml
ollama_num_parallel: "auto"
ollama_max_queue: 512
```

### Production Configuration
```yaml
ollama_num_parallel: 4          # or "auto"
ollama_max_queue: 1024          # Large queue for high load
request_timeout: 300            # 5 minutes
enable_queue_stats: true        # Enable metrics
```

### Memory-Constrained Configuration
```yaml
ollama_num_parallel: 2          # Reduce parallelism
ollama_max_queue: 256           # Smaller queue
request_timeout: 300
```

## 🔍 Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check with concurrency info |
| `/queue/stats` | GET | Queue statistics (all models) |
| `/queue/stats?model=X` | GET | Queue statistics (specific model) |
| `/queue/memory` | GET | Memory info and recommendations |
| `/admin/queue/reset` | POST | Reset statistics |
| `/admin/queue/update` | POST | Update model limits |

## 📊 Monitoring Dashboard

### Essential Metrics

```bash
# Real-time queue stats
watch -n 1 'curl -s http://localhost:8080/queue/stats | jq .models'

# Memory usage
watch -n 5 'curl -s http://localhost:8080/queue/memory | jq'

# Combined health view
curl http://localhost:8080/health | jq .concurrency
```

### Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Rejection rate | > 1% | > 5% | Increase queue/parallel limits |
| Avg wait time | > 5s | > 10s | Increase parallel limit |
| Queue depth | > 80% | > 95% | Increase queue limit |
| Memory usage | > 80% | > 90% | Reduce parallel limit |

## 🧪 Testing Commands

### Quick Test
```bash
# Send single request
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"llama2","prompt":"Test","stream":false}'

# Check stats
curl http://localhost:8080/queue/stats?model=llama2 | jq
```

### Load Test
```bash
# Apache Bench
ab -n 100 -c 10 -p prompt.json -T application/json \
  http://localhost:8080/api/generate
```

### Automated Test Suite
```bash
# Run all tests
python docs/test_concurrency.py
```

## 🐛 Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| 503 errors | Queue full | Increase `ollama_max_queue` or `ollama_num_parallel` |
| High wait times | Insufficient parallelism | Increase `ollama_num_parallel` |
| Memory warnings | Too much parallelism | Reduce `ollama_num_parallel` |
| Import errors | Missing dependencies | Run `pip install -r requirements.txt` |

### Debug Commands

```bash
# Check if proxy is running
curl http://localhost:8080/health

# Check configuration
curl http://localhost:8080/config | jq

# View logs
tail -f logs/ollama_guard_proxy.log

# Check memory
curl http://localhost:8080/queue/memory | jq
```

## 📦 Files Added/Modified

### New Files
- `concurrency.py` - Core implementation
- `setup_concurrency.sh` - Linux/Mac setup script
- `setup_concurrency.bat` - Windows setup script
- `docs/CONCURRENCY_GUIDE.md` - Complete guide
- `docs/CONCURRENCY_QUICKREF.md` - Quick reference
- `docs/CONCURRENCY_TESTING.md` - Testing guide
- `docs/CONCURRENCY_INDEX.md` - This file
- `CONCURRENCY_UPDATE.md` - Update announcement
- `CONCURRENCY_IMPLEMENTATION_SUMMARY.md` - Technical summary

### Modified Files
- `ollama_guard_proxy.py` - Added concurrency control
- `config.yaml` - Added concurrency settings
- `language.py` - Added error messages

### Unchanged Files
- `requirements.txt` - psutil already included

## 🔗 Related Documentation

### General Proxy Documentation
- `README.md` - Main README
- `README_OPTIMIZED.md` - Performance optimization guide
- `docs/QUICK_START.md` - Getting started guide
- `docs/DEPLOYMENT.md` - Deployment guide

### Performance Documentation
- `docs/OPTIMIZATION_SUMMARY.md` - Other optimizations
- `docs/REDIS_QUICKREF.md` - Redis caching
- `docs/MACOS_OPTIMIZATION.md` - Apple Silicon optimization

### API Documentation
- `docs/API_UPDATES.md` - API changes
- `docs/USAGE.md` - API usage guide
- `docs/NGINX_QUICKREF.md` - Nginx configuration

## 💡 Best Practices

1. **Start with auto-detection**: Use `ollama_num_parallel: "auto"`
2. **Monitor before tuning**: Collect metrics for at least 24 hours
3. **Load test in staging**: Test configuration changes before production
4. **Set up alerts**: Monitor rejection rate and wait times
5. **Document changes**: Keep track of configuration changes
6. **Regular review**: Review queue stats weekly

## 🤝 Contributing

Found an issue or have an improvement?
1. Check existing documentation
2. Review [CONCURRENCY_IMPLEMENTATION_SUMMARY.md](../CONCURRENCY_IMPLEMENTATION_SUMMARY.md)
3. Test your changes with the testing guide
4. Update documentation as needed

## 📞 Support

### Documentation Issues
- Check this index for the right document
- Search within documents (all are searchable)
- Review examples in [CONCURRENCY_GUIDE.md](CONCURRENCY_GUIDE.md)

### Configuration Help
- [CONCURRENCY_QUICKREF.md](CONCURRENCY_QUICKREF.md) - Quick settings
- [CONCURRENCY_GUIDE.md](CONCURRENCY_GUIDE.md) - Detailed configuration

### Testing Help
- [CONCURRENCY_TESTING.md](CONCURRENCY_TESTING.md) - Complete testing guide

### Implementation Details
- [CONCURRENCY_IMPLEMENTATION_SUMMARY.md](../CONCURRENCY_IMPLEMENTATION_SUMMARY.md) - Technical details
- [concurrency.py](../concurrency.py) - Source code

## 🎓 Learning Path

### Beginner
1. Read [CONCURRENCY_UPDATE.md](../CONCURRENCY_UPDATE.md)
2. Run setup script
3. Use [CONCURRENCY_QUICKREF.md](CONCURRENCY_QUICKREF.md) for daily tasks

### Intermediate
1. Study [CONCURRENCY_GUIDE.md](CONCURRENCY_GUIDE.md)
2. Run load tests from [CONCURRENCY_TESTING.md](CONCURRENCY_TESTING.md)
3. Set up monitoring dashboard

### Advanced
1. Review [CONCURRENCY_IMPLEMENTATION_SUMMARY.md](../CONCURRENCY_IMPLEMENTATION_SUMMARY.md)
2. Study [concurrency.py](../concurrency.py) source code
3. Contribute improvements

## 🏁 Next Steps

After completing setup:
1. ✅ Monitor system with `/health` and `/queue/stats`
2. ✅ Run load tests to validate configuration
3. ✅ Set up automated monitoring and alerts
4. ✅ Document your configuration choices
5. ✅ Review metrics weekly and adjust as needed

---

**Last Updated**: October 31, 2025  
**Version**: 1.0.0  
**Maintainer**: AI4Team Guardrails Project
