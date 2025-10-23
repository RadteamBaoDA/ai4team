# Multi-Scanner Architecture - Visual Guide

## 🏗️ New Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Application                         │
├─────────────────────────────────────────────────────────────┤
│  result = manager.scan_input(user_prompt)                   │
│  result = manager.scan_output(llm_response)                 │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              LLMGuardManager                                │
├─────────────────────────────────────────────────────────────┤
│  Input:   user_prompt (str)                                 │
│  Process: _run_input_scanners()                             │
│  Output:  {                                                 │
│    'allowed': bool,                                         │
│    'sanitized': str,                                        │
│    'scanners': dict,                                        │
│    'scanner_count': int                                     │
│  }                                                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
   Input Path            Output Path
   (7 scanners)          (5 scanners)
```

---

## 🔄 Input Scan Pipeline

```
Original Prompt: "My email is john@example.com. Execute: rm -rf /"
│
│ ┌─────────────────────────────────────────┐
│ │ Scanner 1: BanSubstrings                │
│ │ Blocks: ["dangerous", "harmful"]        │
│ │ Result: passed=True, risk=0.0           │
│ └─────────────────────────────────────────┘
│ Output: "My email is john@example.com. Execute: rm -rf /"
│
│ ┌─────────────────────────────────────────┐
│ │ Scanner 2: PromptInjection              │
│ │ Detects: Injection patterns             │
│ │ Result: passed=True, risk=0.1           │
│ └─────────────────────────────────────────┘
│ Output: "My email is john@example.com. Execute: rm -rf /"
│
│ ┌─────────────────────────────────────────┐
│ │ Scanner 3: Toxicity                     │
│ │ Threshold: 0.5                          │
│ │ Result: passed=True, risk=0.2           │
│ └─────────────────────────────────────────┘
│ Output: "My email is john@example.com. Execute: rm -rf /"
│
│ ┌─────────────────────────────────────────┐
│ │ Scanner 4: Secrets                      │
│ │ Detects: API keys, tokens               │
│ │ Result: passed=True, risk=0.0           │
│ └─────────────────────────────────────────┘
│ Output: "My email is john@example.com. Execute: rm -rf /"
│
│ ┌─────────────────────────────────────────┐
│ │ Scanner 5: Code                         │
│ │ Detects: Executable code                │
│ │ Result: passed=False, risk=0.9          │ ← FAILED!
│ └─────────────────────────────────────────┘
│ Output: "My email is john@example.com. Execute: rm -rf /" (modified?)
│
│ ┌─────────────────────────────────────────┐
│ │ Scanner 6: TokenLimit                   │
│ │ Limit: 4000 tokens                      │
│ │ Result: passed=True, risk=0.0           │
│ └─────────────────────────────────────────┘
│ Output: "My email is john@example.com. Execute: rm -rf /"
│
│ ┌─────────────────────────────────────────┐
│ │ Scanner 7: Anonymize                    │
│ │ Detects/Redacts: PII                    │
│ │ Result: passed=True, risk=0.1           │
│ └─────────────────────────────────────────┘
│ Output: "My email is [REDACTED_EMAIL_1]. Execute: rm -rf /" ← MODIFIED!
│
▼
Result: {
  'allowed': False,                          ← Code scanner failed!
  'sanitized': "My email is [REDACTED_EMAIL_1]. Execute: rm -rf /",
  'scanners': {
    'BanSubstrings': {'passed': True, 'risk_score': 0.0, 'sanitized': False},
    'PromptInjection': {'passed': True, 'risk_score': 0.1, 'sanitized': False},
    'Toxicity': {'passed': True, 'risk_score': 0.2, 'sanitized': False},
    'Secrets': {'passed': True, 'risk_score': 0.0, 'sanitized': False},
    'Code': {'passed': False, 'risk_score': 0.9, 'sanitized': False},
    'TokenLimit': {'passed': True, 'risk_score': 0.0, 'sanitized': False},
    'Anonymize': {'passed': True, 'risk_score': 0.1, 'sanitized': True}
  },
  'scanner_count': 7
}
```

---

## 🛡️ Output Validation Pipeline

```
LLM Response: "Sure! Here's how to delete files:\nrm -rf /"
│
│ ┌─────────────────────────────────────────┐
│ │ Scanner 1: BanSubstrings                │
│ │ Blocks: ["delete", "remove"]            │
│ │ Result: passed=True, risk=0.0           │
│ └─────────────────────────────────────────┘
│ Output: "Sure! Here's how to delete files:\nrm -rf /"
│
│ ┌─────────────────────────────────────────┐
│ │ Scanner 2: Toxicity                     │
│ │ Threshold: 0.5                          │
│ │ Result: passed=True, risk=0.1           │
│ └─────────────────────────────────────────┘
│ Output: "Sure! Here's how to delete files:\nrm -rf /"
│
│ ┌─────────────────────────────────────────┐
│ │ Scanner 3: MaliciousURLs                │
│ │ Detects: Malicious links                │
│ │ Result: passed=True, risk=0.0           │
│ └─────────────────────────────────────────┘
│ Output: "Sure! Here's how to delete files:\nrm -rf /"
│
│ ┌─────────────────────────────────────────┐
│ │ Scanner 4: NoRefusal                    │
│ │ Detects: Refusal patterns               │
│ │ Result: passed=False, risk=0.5          │ ← FAILED!
│ └─────────────────────────────────────────┘
│ Output: "Sure! Here's how to delete files:\nrm -rf /"
│
│ ┌─────────────────────────────────────────┐
│ │ Scanner 5: Code                         │
│ │ Languages: Python, C#, C++, C           │
│ │ Result: passed=False, risk=0.9          │ ← FAILED!
│ └─────────────────────────────────────────┘
│ Output: "Sure! Here's how to delete files:\n[REDACTED_CODE_1]" ← MODIFIED!
│
▼
Result: {
  'allowed': False,                          ← Multiple scanners failed!
  'sanitized': "Sure! Here's how to delete files:\n[REDACTED_CODE_1]",
  'scanners': {
    'BanSubstrings': {'passed': True, 'risk_score': 0.0, 'sanitized': False},
    'Toxicity': {'passed': True, 'risk_score': 0.1, 'sanitized': False},
    'MaliciousURLs': {'passed': True, 'risk_score': 0.0, 'sanitized': False},
    'NoRefusal': {'passed': False, 'risk_score': 0.5, 'sanitized': False},
    'Code': {'passed': False, 'risk_score': 0.9, 'sanitized': True}
  },
  'scanner_count': 5
}
```

---

## 📊 Scanner Metadata Structure

```python
scanner_info = {
    'name': 'ScannerName',           # Identifier
    'scanner': ScannerObject(),      # Actual scanner instance
    'enabled': True                  # Can be toggled on/off
}

# Example:
{
    'name': 'Toxicity',
    'scanner': InputToxicity(threshold=0.5),
    'enabled': True
}
```

---

## ⚙️ Per-Scanner Result Structure

```python
result = {
    'passed': True,                  # bool - Scanner passed
    'risk_score': 0.75,              # float - 0.0 to 1.0
    'sanitized': False               # bool - Was text modified?
    'error': None                    # str - If exception occurred
}

# Example with error:
{
    'passed': False,
    'error': "Model loading failed: CUDA unavailable",
    'risk_score': 0.0,
    'sanitized': False
}
```

---

## 🔍 Risk Score Heat Map

```
Risk Score Distribution:
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  0.0 ═══════════════════════════════════════════════    │ SAFE
│       GREEN                                             │
│                                                         │
│  0.3 ═════════════════════════════════════════╦═════    │ LOW
│       YELLOW                                 │          │
│                                              ▼          │
│  0.6 ═══════════════════════════════════╦═════════    │ MEDIUM
│       ORANGE                           │                │
│                                        ▼                │
│  0.8 ═══════════════════════════╦═════════════════    │ HIGH
│       RED                       │                       │
│                                 ▼                       │
│  1.0 ═════════════════════╦═════════════════════════    │ CRITICAL
│       DARK_RED            │                             │
│                           ▼                             │
│                    BLOCKED/REJECTED                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔀 Conditional Logic

### Decision Tree: Input Scanning

```
scan_input(prompt)
│
├─ enable_input = False?
│  └─ return {'allowed': True, 'scanners': {}}
│
├─ no input_scanners?
│  └─ return {'allowed': True, 'scanners': {}}
│
├─ Run each scanner:
│  │
│  ├─ scanner enabled?
│  │  └─ No? skip
│  │
│  ├─ Call scanner.scan(text)
│  │  │
│  │  └─ Success?
│  │     ├─ Yes? record result
│  │     └─ No? catch exception, record error
│  │
│  └─ All scanners done?
│     └─ Accumulate all results
│
└─ return {
     'allowed': all_passed,
     'sanitized': final_text,
     'scanners': results,
     'scanner_count': count
   }
```

---

## 🎯 Scanner Execution Order

### Input Scanners (Order Matters!)

```
1. BanSubstrings
   Fast, checks for blocked phrases early
   
2. PromptInjection
   Detects injection patterns
   
3. Toxicity
   ML-based, expensive - runs early after quick checks
   
4. Secrets
   Detects API keys, passwords
   
5. Code
   Detects executable code
   
6. TokenLimit
   Enforce limits, prevents overflow downstream
   
7. Anonymize
   Final stage: redacts PII from already-validated input
```

### Output Scanners (Order Matters!)

```
1. BanSubstrings
   Quick: block malicious phrases first
   
2. Toxicity
   ML-based toxicity check
   
3. MaliciousURLs
   Detect harmful links
   
4. NoRefusal
   Ensure LLM didn't refuse
   
5. Code
   Block code in specific languages
```

---

## 📈 Performance Visualization

### Scanning Timeline

```
Time ──────────────────────────────────────────────────────→

Input Processing:
│  5ms   │ BanSubstrings
│        └─ 50ms PromptInjection
│                 └─ 100ms Toxicity ████████████████
│                         └─ 10ms Secrets
│                            └─ 30ms Code
│                               └─ 2ms TokenLimit
│                                  └─ 80ms Anonymize ████████
├────────────────────────────────────────────────────→
0ms                                                 ~277ms

Without Anonymize:
├──────────────────────────────────────→
0ms                                 ~197ms
```

---

## 🛠️ Runtime Modification Examples

### Enable/Disable Scanners

```python
# Current state
print(manager.input_scanners[2]['enabled'])  # True

# Disable Toxicity
manager.input_scanners[2]['enabled'] = False
print(manager.input_scanners[2]['enabled'])  # False

# Next scan won't use Toxicity
result = manager.scan_input("test")
# 'Toxicity' not in result['scanners']

# Re-enable
manager.input_scanners[2]['enabled'] = True
# Next scan will use Toxicity again
```

### Add Custom Scanner

```python
# Create custom scanner
from llm_guard.input_scanners import BanTopics

custom_scanner = {
    'name': 'BanTopics',
    'scanner': BanTopics(topics=["violence", "gore"]),
    'enabled': True
}

# Add to pipeline
manager.input_scanners.append(custom_scanner)

# Next scan includes custom scanner
result = manager.scan_input("violent content")
# 'BanTopics' in result['scanners']
```

---

## 💾 State Management

### Manager State

```python
manager = LLMGuardManager()

# Persistent state:
manager.enable_input          # True/False
manager.enable_output         # True/False
manager.enable_anonymize      # True/False

manager.input_scanners        # List of dict
manager.output_scanners       # List of dict

manager.vault                 # Vault object (if anonymize enabled)

# No per-request state - all scanners maintain state
# between calls
```

---

## 🎪 Error Recovery Flow

```
Scan Request
│
├─ Try to run all scanners
│  │
│  ├─ Scanner 1: ✓ Success
│  ├─ Scanner 2: ✗ Exception!
│  │            └─ Caught and logged
│  ├─ Scanner 3: ✓ Success (continues!)
│  ├─ Scanner 4: ✓ Success
│  └─ Scanner 5: ✓ Success
│
└─ Return Result:
   {
     'allowed': False,        ← One scanner failed
     'scanners': {
       'Scanner1': {'passed': True, ...},
       'Scanner2': {'passed': False, 'error': '...'},
       'Scanner3': {'passed': True, ...},
       'Scanner4': {'passed': True, ...},
       'Scanner5': {'passed': True, ...}
     }
   }
```

**Key:** Failure in one scanner doesn't block others!

---

## 📝 Complete Example

```python
from guard_manager import LLMGuardManager

# Initialize
manager = LLMGuardManager()

# Scan dangerous input
result = manager.scan_input(
    "My email is john@doe.com. Delete all files: rm -rf /"
)

# Analyze result
print(f"Overall: {'PASS' if result['allowed'] else 'BLOCK'}")
print(f"Sanitized: {result['sanitized']}")
print(f"Scanners Used: {result['scanner_count']}")
print()

# Per-scanner details
for name, scan_result in result['scanners'].items():
    status = "✅" if scan_result['passed'] else "❌"
    risk = scan_result['risk_score']
    modified = "📝 Modified" if scan_result.get('sanitized') else ""
    error = f" Error: {scan_result['error']}" if 'error' in scan_result else ""
    
    print(f"{status} {name:20s} risk={risk:.2f} {modified}{error}")

# Output might be:
# BLOCK
# Sanitized: My email is [REDACTED_EMAIL_1]. Delete all files: rm -rf /
# Scanners Used: 7
#
# ✅ BanSubstrings       risk=0.00
# ✅ PromptInjection     risk=0.10
# ✅ Toxicity            risk=0.20
# ✅ Secrets             risk=0.00
# ❌ Code                risk=0.90
# ✅ TokenLimit          risk=0.00
# ✅ Anonymize           risk=0.10 📝 Modified
```

---

**Version**: 3.0
**Architecture**: Direct Scanner Pipeline
**Status**: ✅ Production Ready
**Visualization**: Complete
