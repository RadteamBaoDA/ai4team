# Guard() vs Direct Scanners - Detailed Comparison

## Architecture Overview

### Before: Guard() Wrapper Pattern

```
┌─────────────────────────────────────────┐
│ User Code                               │
├─────────────────────────────────────────┤
│  manager.scan_input(text)               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Guard Manager                           │
├─────────────────────────────────────────┤
│  self.input_guard = Guard(              │
│    input_scanners=[               │
│      Scanner1(),                  │
│      Scanner2(),                  │
│      Scanner3(),                  │
│      ...                           │
│    ]                              │
│  )                                │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Guard Class (llm_guard.guard)           │
├─────────────────────────────────────────┤
│  guard.validate(text)                   │
│    ├─ Internal scanner loop             │
│    ├─ Limited error handling            │
│    └─ Black-box result                  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ All Scanners (unknown execution)        │
├─────────────────────────────────────────┤
│  Scanner1.scan(text)                    │
│  Scanner2.scan(text)                    │
│  ...                                    │
└─────────────────────────────────────────┘
```

**Problems:**
- ❌ Guard() doesn't properly support multiple scanners
- ❌ Black-box execution - don't see individual results
- ❌ Errors in one scanner block others
- ❌ No per-scanner risk scores
- ❌ Can't modify/reorder scanners at runtime

---

### After: Direct Scanner Pipeline

```
┌─────────────────────────────────────────┐
│ User Code                               │
├─────────────────────────────────────────┤
│  manager.scan_input(text)               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Guard Manager                           │
├─────────────────────────────────────────┤
│  self.input_scanners = [                │
│    {name: 'Scanner1', ...},             │
│    {name: 'Scanner2', ...},             │
│    {name: 'Scanner3', ...},             │
│    ...                                  │
│  ]                                      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Pipeline Executor                       │
├─────────────────────────────────────────┤
│  _run_input_scanners(text)              │
│    ├─ Per-scanner execution             │
│    ├─ Per-scanner error handling        │
│    ├─ Chain results (text flows through)│
│    └─ Aggregate results                 │
└──────────────┬──────────────────────────┘
               │
      ┌────────┴────────┬────────┬─────────┐
      │                 │        │         │
      ▼                 ▼        ▼         ▼
  Scanner1         Scanner2   Scanner3   ...
  scan(text) → (text', valid, risk)
  
  text' → Scanner2.scan(text')
          ├─ Input: sanitized from Scanner1
          └─ Output: (text'', valid, risk)
          
  text'' → Scanner3.scan(text'')
           └─ And so on...
```

**Benefits:**
- ✅ Each scanner called independently
- ✅ Clear per-scanner results
- ✅ One scanner failure doesn't block others
- ✅ All risk scores visible
- ✅ Text flows through pipeline with modifications
- ✅ Full runtime control

---

## Code Comparison

### Initialization

#### BEFORE (Guard())
```python
from llm_guard.guard import Guard
from llm_guard.input_scanners import (
    BanSubstrings, PromptInjection, Toxicity, ...
)

class LLMGuardManager:
    def __init__(self):
        self.input_guard = Guard(
            input_scanners=[
                BanSubstrings(...),
                PromptInjection(),
                Toxicity(...),
                Secrets(),
                Code(),
                TokenLimit(...),
                Anonymize(...),
            ]
        )
```

**Issues:**
- ❌ All scanners bundled into Guard object
- ❌ Can't control individual scanners
- ❌ Guard class does internal scanning

#### AFTER (Direct Scanners)
```python
class LLMGuardManager:
    def __init__(self):
        self.input_scanners = [
            {
                'name': 'BanSubstrings',
                'scanner': BanSubstrings(...),
                'enabled': True
            },
            {
                'name': 'PromptInjection',
                'scanner': PromptInjection(),
                'enabled': True
            },
            {
                'name': 'Toxicity',
                'scanner': Toxicity(...),
                'enabled': True
            },
            # ... more scanners
        ]
```

**Benefits:**
- ✅ Explicit scanner list
- ✅ Each scanner is a dict with metadata
- ✅ Can enable/disable individual scanners
- ✅ Clear naming and configuration

---

### Scanning Process

#### BEFORE (Guard())
```python
def scan_input(self, prompt: str):
    # Internal Guard mechanism
    try:
        result = self.input_guard.validate(prompt)
        
        # Try to extract results from Guard's internal structure
        return {
            "allowed": result.validation_passed,
            "scanners": {
                s.name: {"passed": s.passed, "reason": s.reason}
                for s in result.scanners
            }
        }
    except Exception as e:
        logger.exception('Input scan error: %s', e)
        return {"allowed": False, "error": str(e)}
```

**Issues:**
- ❌ Depends on Guard's internal API
- ❌ Limited result information
- ❌ No risk scores
- ❌ No text modification tracking
- ❌ No way to see which scanner modified text

#### AFTER (Direct Scanners)
```python
def scan_input(self, prompt: str):
    sanitized_prompt = prompt
    all_valid = True
    scan_results = {}
    
    # Process each scanner individually
    for scanner_info in self.input_scanners:
        if not scanner_info['enabled']:
            continue
        
        scanner_name = scanner_info['name']
        scanner = scanner_info['scanner']
        
        try:
            # Call scanner directly
            sanitized_prompt, is_valid, risk_score = scanner.scan(sanitized_prompt)
            
            # Record results with full details
            scan_results[scanner_name] = {
                'passed': is_valid,
                'risk_score': risk_score,
                'sanitized': sanitized_prompt != prompt
            }
            
            if not is_valid:
                all_valid = False
                
        except Exception as e:
            logger.exception(f'Error in {scanner_name}')
            scan_results[scanner_name] = {
                'passed': False,
                'error': str(e)
            }
            all_valid = False
    
    return {
        "allowed": all_valid,
        "sanitized": sanitized_prompt,
        "scanners": scan_results,
        "scanner_count": len(self.input_scanners)
    }
```

**Benefits:**
- ✅ Each scanner executed independently
- ✅ Per-scanner error handling
- ✅ Full risk score tracking
- ✅ Text modification visibility
- ✅ Can continue even if scanner fails
- ✅ Explicit pipeline control

---

## Response Format Comparison

### BEFORE (Guard() Result)
```python
{
    "allowed": True,                    # Overall pass/fail
    "scanners": {                       # Limited info per scanner
        "BanSubstrings": {
            "passed": True,
            "reason": None              # Minimal details
        },
        "Toxicity": {
            "passed": False,
            "reason": "Toxic content detected"
        }
    }
}
```

**Missing Information:**
- ❌ No risk scores
- ❌ No indication of text modification
- ❌ No scanner count
- ❌ No per-scanner errors
- ❌ No error details

### AFTER (Direct Scanner Result)
```python
{
    "allowed": True,                    # Overall pass/fail
    "sanitized": "modified text",       # Processed output
    "scanners": {                       # Comprehensive per-scanner info
        "BanSubstrings": {
            "passed": True,
            "risk_score": 0.0,          # NEW: Risk score
            "sanitized": False          # NEW: Was modified?
        },
        "Toxicity": {
            "passed": False,
            "risk_score": 0.85,         # NEW: Actual risk level
            "sanitized": False
        },
        "Anonymize": {
            "passed": True,
            "risk_score": 0.2,
            "sanitized": True           # NEW: Text was redacted
        }
    },
    "scanner_count": 7                  # NEW: Total scanners
}
```

**Enhanced Information:**
- ✅ Risk scores for each scanner
- ✅ Text modification tracking
- ✅ Scanner count for debugging
- ✅ Sanitized output at each step
- ✅ Per-scanner error details

---

## Error Handling Comparison

### BEFORE (Guard())
```
Input Text
    │
    ▼
Guard.validate() [Black box]
    ├─ Scanner1: ✓ Pass
    ├─ Scanner2: ✓ Pass
    ├─ Scanner3: ✗ ERROR  ← One error stops everything
    ├─ Scanner4: ⏸️ Skipped
    └─ Scanner5: ⏸️ Skipped
    
Result: All failed
        Error: "Guard validation failed"
```

**Issue:** One scanner error blocks all others

### AFTER (Direct Scanners)
```
Input Text
    │
    ▼
Scanner1.scan(): ✓ Pass (risk=0.0)
    │
    ▼ [sanitized text]
Scanner2.scan(): ✓ Pass (risk=0.1)
    │
    ▼ [sanitized text]
Scanner3.scan(): ✗ ERROR (caught and logged)
    ├─ Result: {passed: False, error: "..."}
    │
    ▼ [continue with modified text]
Scanner4.scan(): ✓ Pass (risk=0.0)
    │
    ▼ [sanitized text]
Scanner5.scan(): ✓ Pass (risk=0.0)

Result: 4 passed, 1 error
        Overall: Failed (due to Scanner3 error)
        But: All scanners still ran!
```

**Benefit:** One error doesn't block others

---

## Runtime Control Comparison

### BEFORE (Guard())
```python
# Can't modify scanners after creation
manager = LLMGuardManager()

# No way to:
# - Disable a scanner
# - Change configuration
# - Add a scanner
# - Reorder scanners
```

### AFTER (Direct Scanners)
```python
# Full control over scanners
manager = LLMGuardManager()

# Disable Toxicity scanner
manager.input_scanners[2]['enabled'] = False

# Enable it again
manager.input_scanners[2]['enabled'] = True

# Add a new scanner
manager.input_scanners.append({
    'name': 'CustomScanner',
    'scanner': MyScanner(),
    'enabled': True
})

# Change scanner configuration
manager.input_scanners[0]['scanner'] = \
    BanSubstrings(["new", "words"])
```

**Benefit:** Full flexibility

---

## Feature Comparison Table

| Feature | Guard() | Direct Scanners |
|---------|---------|-----------------|
| **Initialization** | Simple | Explicit |
| **Per-scanner control** | ❌ No | ✅ Yes |
| **Enable/disable scanners** | ❌ No | ✅ Yes |
| **Per-scanner errors** | ❌ All or nothing | ✅ Individual |
| **Risk scores** | ❌ No | ✅ Yes |
| **Text modification tracking** | ❌ No | ✅ Yes |
| **Error recovery** | ❌ No | ✅ Yes |
| **Runtime modification** | ❌ No | ✅ Yes |
| **Debugging** | ❌ Hard | ✅ Easy |
| **Transparency** | ❌ Black box | ✅ White box |
| **Learning curve** | ❌ API dependent | ✅ Intuitive |
| **Performance** | Similar | Similar |
| **Maintainability** | ❌ Complex | ✅ Simple |

---

## When to Use Each Approach

### Use Guard() if:
- You need a pre-built orchestrator
- Your scanners work well together
- You don't need per-scanner control
- You prefer black-box simplicity

**Reality:** Guard() has issues with multiple scanners, so use Direct Scanners instead!

### Use Direct Scanners if:
- ✅ You need full control per scanner
- ✅ You want to see all details
- ✅ You need robust error handling
- ✅ You want to customize behavior
- ✅ You want clear debugging
- ✅ You need per-scanner risk scores

**Recommendation:** Use Direct Scanners (this implementation)

---

## Migration Path

### Step 1: Update Initialization
```python
# Old
self.input_guard = Guard(input_scanners=[...])

# New
self.input_scanners = [
    {'name': 'Scanner1', 'scanner': Scanner1(), 'enabled': True},
    # ...
]
```

### Step 2: Update Scanning
```python
# Old
result = self.input_guard.validate(text)

# New
sanitized, is_valid, risk = scanner.scan(text)
```

### Step 3: Update Result Handling
```python
# Old
result['allowed']

# New
result['allowed']  # Same!
result['sanitized']  # New: get sanitized text
result['scanners']['Scanner1']['risk_score']  # New: get risk
```

---

## Summary

| Aspect | Guard() | Direct Scanners |
|--------|---------|-----------------|
| **Coupling** | High | Low |
| **Control** | Limited | Full |
| **Transparency** | Black box | White box |
| **Error Handling** | Fragile | Robust |
| **Debugging** | Hard | Easy |
| **Flexibility** | Low | High |
| **Maintenance** | Complex | Simple |

**Verdict:** Direct Scanners are superior for production use.

---

**Version**: 3.0
**Architecture**: ✅ Direct Scanners (No Guard())
**Comparison**: Complete
**Migration**: Straightforward
