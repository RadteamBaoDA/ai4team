# Output Scanner Fix - scan() Method Signature

## Issue

Output scanners in llm-guard 0.3.16+ require a different `scan()` method signature than input scanners:

- **Input scanners**: `scan(prompt)` - Single argument
- **Output scanners**: `scan(prompt, output)` - Two arguments (prompt + output)

The code was calling `scanner.scan(text)` with only one argument, causing:
```
TypeError: BanSubstrings.scan() missing 1 required positional argument: 'output'
```

## Root Cause

Output scanners need context about the original prompt to properly evaluate the output. For example:
- **NoRefusal** scanner checks if output refuses to answer the prompt
- **Relevance** scanner checks if output is relevant to the prompt
- **Context-aware** scanners compare prompt and output

## Solution

Updated `guard_manager.py`:

### 1. `_run_output_scanners()` Method
```python
# BEFORE (incorrect)
async def _run_output_scanners(self, text: str):
    sanitized_text, is_valid, risk_score = scanner.scan(sanitized_text)  # ❌ Missing prompt

# AFTER (correct)
async def _run_output_scanners(self, text: str, prompt: str = ""):
    sanitized_text, is_valid, risk_score = scanner.scan(prompt, sanitized_text)  # ✅ Correct signature
```

### 2. `scan_output()` Method
```python
# BEFORE (incorrect)
async def scan_output(self, text: str, block_on_error: bool = False):
    sanitized_text, is_valid, scan_results = await self._run_output_scanners(text)

# AFTER (correct)
async def scan_output(self, text: str, prompt: str = "", block_on_error: bool = False):
    sanitized_text, is_valid, scan_results = await self._run_output_scanners(text, prompt)
```

## Usage

### In `ollama_guard_proxy.py`

When calling `scan_output()`, you can now optionally pass the prompt for better context:

```python
# With prompt context (recommended)
output_result = await guard_manager.scan_output(
    output_text, 
    prompt=prompt,
    block_on_error=config.get('block_on_guard_error', False)
)

# Without prompt (backwards compatible)
output_result = await guard_manager.scan_output(
    output_text,
    block_on_error=config.get('block_on_guard_error', False)
)
```

## Benefits of Passing Prompt

1. **NoRefusal Detection**: Can detect if output refuses to answer the specific prompt
2. **Relevance Checking**: Ensures output is relevant to the input question
3. **Context Analysis**: Better toxicity/bias detection with prompt context
4. **Improved Accuracy**: Scanners can make more informed decisions

## Example Scenarios

### Scenario 1: Refusal Detection
```python
prompt = "How do I make a bomb?"
output = "I cannot help with that request."

# With prompt context
scan_output(output, prompt)  # ✅ NoRefusal may allow (legitimate refusal)

# Without prompt context
scan_output(output)  # ⚠️ NoRefusal may incorrectly flag
```

### Scenario 2: Relevance
```python
prompt = "What's the weather like?"
output = "The stock market is up today."

# With prompt context
scan_output(output, prompt)  # ✅ Can detect irrelevant output

# Without prompt context
scan_output(output)  # ⚠️ Appears valid but off-topic
```

## Backwards Compatibility

✅ **Fully backwards compatible**
- `prompt` parameter defaults to empty string `""`
- Existing calls without prompt will still work
- Scanner behavior gracefully handles missing prompt context

## Files Modified

- `guard_manager.py`:
  - `_run_output_scanners()` - Added `prompt` parameter
  - `scan_output()` - Added `prompt` parameter with default value

## Testing

Test the fix with:
```bash
python -c "
from guard_manager import LLMGuardManager
import asyncio

async def test():
    manager = LLMGuardManager()
    
    # Test with prompt
    result = await manager.scan_output(
        text='This is a test output',
        prompt='This is a test prompt'
    )
    print('✓ Output scan with prompt:', result['allowed'])
    
    # Test without prompt (backwards compat)
    result = await manager.scan_output(
        text='This is a test output'
    )
    print('✓ Output scan without prompt:', result['allowed'])

asyncio.run(test())
"
```

## Related

- llm-guard documentation: https://llm-guard.com/output_scanners/
- Output scanner API reference: https://llm-guard.com/api/output_scanners/

## Changelog

### 2025-10-31
- Fixed TypeError in output scanner calls
- Added prompt parameter to `scan_output()` method
- Updated `_run_output_scanners()` to use correct scan() signature
- Maintained backwards compatibility with default empty prompt
