# Multi-Scanner Quick Reference

## Architecture Change

```
❌ OLD: Guard() wrapper class
  from llm_guard.guard import Guard
  guard = Guard(input_scanners=[...])
  result = guard.validate(text)

✅ NEW: Direct scanner calls
  manager = LLMGuardManager()
  result = manager.scan_input(text)
```

---

## Basic Usage

### Initialize Manager
```python
from guard_manager import LLMGuardManager

# All features enabled
manager = LLMGuardManager()

# Disable anonymization
manager = LLMGuardManager(enable_anonymize=False)

# Input only
manager = LLMGuardManager(enable_output=False)
```

### Scan Input
```python
result = manager.scan_input("user input")

if result['allowed']:
    print("✅ Input safe")
    print("Sanitized:", result['sanitized'])
else:
    print("❌ Input blocked")
```

### Scan Output
```python
result = manager.scan_output("llm response")

if result['allowed']:
    print("✅ Output safe")
else:
    print("❌ Output blocked")
```

---

## Response Format

```python
{
    'allowed': True,           # Overall pass/fail
    'sanitized': "text...",    # After all scanners
    'scanners': {              # Per-scanner results
        'BanSubstrings': {
            'passed': True,
            'risk_score': 0.0,
            'sanitized': False
        },
        'Toxicity': {
            'passed': False,
            'risk_score': 0.8,
            'sanitized': True
        },
        # ... more scanners
    },
    'scanner_count': 7
}
```

---

## Input Scanners (7 Total)

| # | Scanner | Purpose | Risk Score | Modifies Text |
|---|---------|---------|-----------|---------------|
| 1 | BanSubstrings | Block phrases | 0.0-1.0 | No |
| 2 | PromptInjection | Detect injection | 0.0-1.0 | No |
| 3 | Toxicity | Detect toxic language | 0.0-1.0 | No |
| 4 | Secrets | Detect API keys | 0.0-1.0 | No |
| 5 | Code | Detect code | 0.0-1.0 | No |
| 6 | TokenLimit | Enforce limits | 0.0-1.0 | Truncate |
| 7 | Anonymize | Redact PII | 0.0-1.0 | Yes |

---

## Output Scanners (5 Total)

| # | Scanner | Purpose | Risk Score | Modifies Text |
|---|---------|---------|-----------|---------------|
| 1 | BanSubstrings | Block phrases | 0.0-1.0 | No |
| 2 | Toxicity | Detect toxic | 0.0-1.0 | No |
| 3 | MaliciousURLs | Detect bad links | 0.0-1.0 | No |
| 4 | NoRefusal | Check refusal | 0.0-1.0 | No |
| 5 | Code | Block code (Python, C#, C++, C) | 0.0-1.0 | No |

---

## Common Patterns

### Check Overall Result
```python
result = manager.scan_input(text)
if result['allowed']:
    use_text(result['sanitized'])
else:
    block_user()
```

### Get Failed Scanners
```python
failed = [name for name, scan in result['scanners'].items() 
          if not scan['passed']]
print(f"Failed scanners: {failed}")
```

### Get Risk Scores
```python
for name, scan in result['scanners'].items():
    print(f"{name}: risk={scan['risk_score']:.2f}")
```

### Check If Text Modified
```python
modified_scanners = [name for name, scan in result['scanners'].items() 
                     if scan.get('sanitized')]
if modified_scanners:
    print(f"Modified by: {modified_scanners}")
```

### Check for Errors
```python
errors = {name: scan['error'] for name, scan in result['scanners'].items() 
          if 'error' in scan}
if errors:
    print(f"Scan errors: {errors}")
```

---

## Scanner Pipeline

```
Input → [Scanner1] → [Scanner2] → [Scanner3] → ... → Output
        (sanitize)   (sanitize)   (sanitize)
         risk: 0.3    risk: 0.0    risk: 0.8
```

**Key Point:** Each scanner receives the sanitized output from the previous scanner.

---

## Risk Score Interpretation

```
0.0-0.2: SAFE      ✅ Pass
0.3-0.5: LOW       ⚠️  Maybe modify
0.6-0.8: MEDIUM    ⚠️  Likely modify
0.9-1.0: HIGH      ❌ Fail
```

---

## Error Handling

### Graceful Degradation
```python
from guard_manager import HAS_LLM_GUARD

if not HAS_LLM_GUARD:
    print("Scanning disabled")
    # App continues without scanning
```

### Per-Scanner Errors
```python
result = manager.scan_input(text)

for name, scan in result['scanners'].items():
    if 'error' in scan:
        print(f"Error in {name}: {scan['error']}")
        # Other scanners still ran
```

### Block on Error
```python
result = manager.scan_input(text, block_on_error=True)

if 'error' in result:
    print("Blocked due to scan error")
```

---

## Configuration

### Disable Anonymization
```python
manager = LLMGuardManager(enable_anonymize=False)
```

### Disable Output Scanning
```python
manager = LLMGuardManager(enable_output=False)
```

### Disable a Scanner
```python
# Disable Toxicity scanner (index 2)
manager.input_scanners[2]['enabled'] = False
```

---

## Performance Tips

1. **Reuse Manager**
   ```python
   manager = LLMGuardManager()
   for text in texts:
       result = manager.scan_input(text)
   ```

2. **Disable Slow Scanners**
   ```python
   # Toxicity and Anonymize are slower
   manager = LLMGuardManager(enable_anonymize=False)
   ```

3. **Skip Output Scanning**
   ```python
   manager = LLMGuardManager(enable_output=False)
   ```

---

## Approximate Timing

| Operation | Time |
|-----------|------|
| BanSubstrings | 5ms |
| PromptInjection | 50ms |
| Toxicity | 100ms (ML model) |
| Secrets | 10ms |
| Code | 30ms |
| TokenLimit | 2ms |
| Anonymize | 80ms (optional) |
| **Total (without Anonymize)** | **~197ms** |
| **Total (with Anonymize)** | **~277ms** |

---

## Examples

### Block Toxic Input
```python
manager = LLMGuardManager()
result = manager.scan_input(user_input)

if not result['allowed']:
    if 'Toxicity' in result['scanners']:
        toxicity = result['scanners']['Toxicity']
        if not toxicity['passed']:
            return "Your message contains inappropriate language"
```

### Sanitize PII
```python
result = manager.scan_input("Email: john@example.com")

if result['sanitized'] != input:
    # Text was modified (PII redacted)
    safe_input = result['sanitized']
    send_to_llm(safe_input)
```

### Monitor Risk Scores
```python
result = manager.scan_input(text)

max_risk = max(scan['risk_score'] for scan in result['scanners'].values())
if max_risk > 0.7:
    log_warning(f"High risk detected: {max_risk}")
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ModuleNotFoundError: llm_guard | `pip install llm-guard` |
| Scanning very slow | Disable Toxicity/Anonymize |
| Scanner failed error | Check llm-guard version |
| Text not sanitized | Check 'sanitized' field in response |

---

## Key Differences from Guard() Approach

| Aspect | Guard() | Direct Scanners |
|--------|---------|-----------------|
| Per-scanner control | ❌ Limited | ✅ Full |
| Error handling | ❌ All or nothing | ✅ Per-scanner |
| Risk scores | ❌ Not exposed | ✅ Available |
| Text modification | ❌ Hidden | ✅ Visible |
| Flexibility | ❌ Low | ✅ High |
| Learning curve | ❌ API dependent | ✅ Explicit |

---

**Version**: 3.0
**Status**: ✅ Production Ready
**Guard() Class**: ❌ Removed
**Scanner Control**: ✅ Full
