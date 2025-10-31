# Connection Cleanup - Quick Reference

## What This Optimization Does

**Closes connections immediately when LLM Guard blocks output**, stopping Ollama generation and freeing resources instantly.

## Quick Test

```bash
# Test streaming block (should complete in < 5s)
time curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"llama2","prompt":"write toxic content","stream":true}'

# Check logs for:
# "Connection closed after blocking streaming output"
```

## Key Logs to Monitor

### INFO Level (Production)
```
Connection closed after blocking streaming output
Connection closed after blocking non-streaming output
Connection closed after blocking OpenAI chat output
Connection closed after blocking completion output
```

### DEBUG Level (Development)
```
Connection closed after streaming completed
Connection closed after processing
Connection already closed: ...
```

## Modified Functions

| Function | Lines | Purpose |
|----------|-------|---------|
| `stream_response_with_guard()` | ~510-590 | Ollama streaming |
| `stream_openai_chat_response()` | ~595-795 | OpenAI chat streaming |
| `stream_openai_completion_response()` | ~800-980 | OpenAI completion streaming |
| `/api/generate` handler | ~440-480 | Ollama non-streaming |
| `/v1/chat/completions` handler | ~1290-1340 | OpenAI chat non-streaming |
| `/v1/completions` handler | ~1520-1560 | OpenAI completion non-streaming |

## Code Pattern

### Streaming
```python
blocked = False
try:
    async for line in response.aiter_lines():
        # Process...
        if blocked_by_guard:
            blocked = True
            await response.aclose()  # ⚡ Immediate
            return
finally:
    if not blocked:  # Prevent double-close
        await response.aclose()
```

### Non-Streaming
```python
if blocked_by_guard:
    await response.aclose()  # Close before exception
    raise HTTPException(...)

await response.aclose()  # Close on success
```

## Performance Expectations

| Scenario | Time | Resources |
|----------|------|-----------|
| Streaming block | < 5s | Freed immediately |
| Non-streaming block | < 1s | Freed immediately |
| Concurrent blocks | No pool exhaustion | All freed |

## Troubleshooting

### ⚠️ Connections not closing
- Check logs for "Connection closed" messages
- Verify scanners are detecting violations
- Ensure proper error flow (no early returns skipping cleanup)

### ⚠️ Double-close errors
- Should see DEBUG log: "Connection already closed"
- This is normal and handled gracefully
- Indicates proper flow through blocked path

### ⚠️ Pool exhaustion
- Should NOT occur after optimization
- If occurs, check for exceptions preventing cleanup
- Verify all exit paths close connections

## Monitoring Commands

```bash
# Watch Ollama CPU usage (should drop immediately after blocking)
watch -n 1 'ps aux | grep ollama'

# Monitor proxy logs in real-time
tail -f proxy.log | grep "Connection closed"

# Test concurrent blocking (should all succeed)
for i in {1..20}; do
  curl -X POST http://localhost:8080/api/generate \
    -d '{"model":"llama2","prompt":"toxic","stream":true}' &
done
```

## Files

- `ollama_guard_proxy.py` - Main implementation
- `docs/CONNECTION_CLEANUP_OPTIMIZATION.md` - Full documentation
- `docs/CONNECTION_CLEANUP_SUMMARY.md` - Executive summary
- `docs/CONNECTION_CLEANUP_VISUAL.md` - Visual guide
- `test_connection_cleanup.py` - Test suite

## Related

- [API_CHAT_STREAMING_FIX.md](API_CHAT_STREAMING_FIX.md) - Streaming scanning
- [IMPROVED_ERROR_RESPONSES.md](IMPROVED_ERROR_RESPONSES.md) - Error format
- [CONCURRENCY_IMPLEMENTATION_SUMMARY.md](../CONCURRENCY_IMPLEMENTATION_SUMMARY.md) - Connection pooling

## Common Questions

**Q: Does this change the API?**  
A: No, fully backwards compatible.

**Q: Will clients notice any difference?**  
A: Yes, blocked requests complete faster (< 5s vs 30-60s).

**Q: What about non-blocked requests?**  
A: No impact, same behavior as before.

**Q: Does this prevent all blocking?**  
A: No, it just cleans up faster AFTER blocking occurs.

**Q: Is configuration needed?**  
A: No, automatic for all endpoints.

## Emergency Rollback

If issues occur:
1. Revert `ollama_guard_proxy.py` to previous version
2. Restart proxy service
3. Connections will return to timeout-based cleanup

Note: This should not be needed as optimization is conservative and backwards compatible.
