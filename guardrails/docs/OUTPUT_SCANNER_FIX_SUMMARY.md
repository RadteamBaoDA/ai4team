# Output Scanner Fix - Summary

## Issue Fixed

**Error**: `TypeError: BanSubstrings.scan() missing 1 required positional argument: 'output'`

**Root Cause**: Output scanners in llm-guard require two arguments `scan(prompt, output)`, but code was calling `scan(output)` with only one argument.

## Solution

Updated `guard_manager.py` to use the correct output scanner signature:

### Changes Made

1. **`_run_output_scanners()` method** (line ~409):
   - Added `prompt` parameter with default value `""`
   - Changed scanner call from `scanner.scan(sanitized_text)` to `scanner.scan(prompt, sanitized_text)`

2. **`scan_output()` method** (line ~447):
   - Added `prompt` parameter with default value `""`
   - Passes prompt to `_run_output_scanners(text, prompt)`

## Code Changes

### Before (Broken)
```python
async def _run_output_scanners(self, text: str):
    # ...
    sanitized_text, is_valid, risk_score = scanner.scan(sanitized_text)  # ❌ Wrong!
```

### After (Fixed)
```python
async def _run_output_scanners(self, text: str, prompt: str = ""):
    # ...
    sanitized_text, is_valid, risk_score = scanner.scan(prompt, sanitized_text)  # ✅ Correct!
```

## Why Output Scanners Need Prompt

Output scanners use the original prompt for context-aware analysis:

| Scanner | Why It Needs Prompt |
|---------|---------------------|
| **NoRefusal** | Checks if output refuses to answer the prompt |
| **Relevance** | Verifies output is relevant to the prompt |
| **BanSubstrings** | Can check prompt context for allowed exceptions |
| **Toxicity** | Better context for false positive reduction |
| **MaliciousURLs** | Can validate URLs mentioned in prompt |

## Backwards Compatibility

✅ **Fully backwards compatible**

The `prompt` parameter defaults to empty string, so existing code continues to work:

```python
# Both work correctly:
await manager.scan_output(output_text)                          # No prompt
await manager.scan_output(output_text, prompt=input_prompt)     # With prompt (better)
```

## Usage in ollama_guard_proxy.py

You can optionally update `ollama_guard_proxy.py` to pass prompts for better scanning:

```python
# Current (works but less accurate)
output_result = await guard_manager.scan_output(output_text)

# Recommended (better accuracy)
output_result = await guard_manager.scan_output(output_text, prompt=prompt)
```

## Testing

Test the fix:
```bash
python test_output_scanner_fix.py
```

Expected output:
```
✓ Output scan with prompt PASSED
✓ Output scan without prompt PASSED
✓ No scanner errors detected
✓ ALL TESTS PASSED
```

## Files Modified

1. `guard_manager.py`:
   - `_run_output_scanners()` - Added `prompt` parameter, fixed scan() call
   - `scan_output()` - Added `prompt` parameter

2. Documentation:
   - `docs/OUTPUT_SCANNER_FIX.md` - Detailed explanation
   
3. Tests:
   - `test_output_scanner_fix.py` - Verification test

## Impact

### Before (Broken)
- ❌ All output scanners threw TypeError
- ❌ Output scanning completely broken
- ❌ Security gap - no output validation

### After (Fixed)
- ✅ All output scanners work correctly
- ✅ Proper scan(prompt, output) signature
- ✅ Better accuracy with prompt context
- ✅ Backwards compatible

## Next Steps (Optional Enhancement)

Update `ollama_guard_proxy.py` to pass prompts to `scan_output()`:

```python
# In /api/generate endpoint
output_result = await guard_manager.scan_output(
    output_text,
    prompt=prompt,  # Add this
    block_on_error=config.get('block_on_guard_error', False)
)

# In /api/chat endpoint  
output_result = await guard_manager.scan_output(
    output_text,
    prompt=prompt,  # Add this
    block_on_error=config.get('block_on_guard_error', False)
)

# In /v1/chat/completions endpoint
output_result = await guard_manager.scan_output(
    output_text,
    prompt=prompt_text,  # Add this
    block_on_error=config.get('block_on_guard_error', False)
)
```

This will improve scanner accuracy but is not required for the fix to work.

## Conclusion

The output scanner signature issue is now fixed. All output scanners receive both prompt and output as required by the llm-guard API, enabling proper context-aware scanning while maintaining full backwards compatibility.
