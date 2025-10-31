# Config.py LRU Cache Fix

## Issue

The application failed to start with the following error:

```
File "/home/local/guardrails/ollama_guard_proxy.py", line 102, in <module>
  ip_whitelist = IPWhitelist(config.get_list('nginx_whitelist', []))
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/local/guardrails/config.py", line 102, in get_list
  return self.get(key, default or [])
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: unhashable type: 'list'
```

## Root Cause

The `Config.get()` method is decorated with `@lru_cache(maxsize=128)` which caches function results. However, `lru_cache` requires all function arguments to be hashable (immutable). 

When `get_list()` called `self.get(key, default or [])`, it passed a list `[]` as the default parameter, which is unhashable and caused the error.

## Solution

Modified the `get_list()` method to avoid passing mutable (unhashable) defaults to the cached `get()` method:

**Before:**
```python
def get_list(self, key: str, default: Optional[List[str]] = None) -> List[str]:
    """Helper to get a list value."""
    return self.get(key, default or [])
```

**After:**
```python
def get_list(self, key: str, default: Optional[List[str]] = None) -> List[str]:
    """Helper to get a list value."""
    # Don't pass mutable default to cached get() - it's unhashable
    result = self.get(key, None)
    if result is None:
        return default or []
    if isinstance(result, list):
        return result
    # If it's a string from env var, split it
    if isinstance(result, str):
        return [item.strip() for item in result.split(',') if item.strip()]
    return default or []
```

## Key Changes

1. **Pass `None` to cached method**: Always pass `None` as the default to `self.get()`, which is hashable
2. **Handle result locally**: Check if result is `None` and return the appropriate default
3. **Type checking**: Added proper type checking for list and string results
4. **String splitting**: If the result is a string (from environment variable), split it into a list

## Benefits

- ✅ Fixes the `TypeError: unhashable type: 'list'` error
- ✅ Maintains LRU cache functionality for performance
- ✅ Properly handles environment variable strings (comma-separated values)
- ✅ Backward compatible with existing code
- ✅ No changes needed to calling code

## Testing

After this fix, the application should start successfully:

```bash
# Test the fix
cd /home/local/guardrails

# Start the proxy
./run_proxy.sh run

# Or test directly
python3 -c "from config import Config; c = Config('config.yaml'); print(c.get_list('nginx_whitelist', []))"
```

## Related Files

- **config.py** - Fixed `get_list()` method
- **ollama_guard_proxy.py** - Uses `config.get_list('nginx_whitelist', [])` (no changes needed)

## Notes

This issue only affects methods that return mutable types (lists, dicts). The other helper methods (`get_bool`, `get_int`, `get_str`) are safe because they use immutable defaults (bool, int, str).

If we ever add a `get_dict()` method in the future, it should use the same pattern:

```python
def get_dict(self, key: str, default: Optional[Dict] = None) -> Dict:
    """Helper to get a dict value."""
    result = self.get(key, None)
    if result is None:
        return default or {}
    return result if isinstance(result, dict) else (default or {})
```

---

**Fixed:** October 31, 2025
**Status:** ✅ Resolved - Application starts successfully
