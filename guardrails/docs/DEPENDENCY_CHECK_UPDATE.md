# ✅ Dependency Check Enhancement - Summary

## What Was Updated

The `run_proxy.sh` script has been enhanced with **comprehensive dependency checking** from `requirements.txt`.

---

## 🎯 New Features

### 1. **Requirements.txt Parsing**
- Detects all required packages from `requirements.txt`
- Checks each package individually

### 2. **Comprehensive Package Checking**

The script now checks for:
- **fastapi** (0.104.1)
- **uvicorn** (0.24.0)
- **pydantic** (2.5.0)
- **requests** (2.31.0)
- **pyyaml** (6.0.1)
- **llm-guard** (0.3.16)

### 3. **Interactive Installation**

If packages are missing, the script:
1. Lists which packages are missing
2. Shows install command
3. **Asks permission to install** (y/n)
4. Automatically installs if approved
5. Continues setup or exits on failure

### 4. **Version Reporting**

Shows installed version for each package:
```
Step 3: Checking Dependencies
─────────────────────────────────────────────────────────────────
✓ requirements.txt found

  Checking required packages:
    ✓ uvicorn (version: 0.24.0)
    ✓ fastapi (version: 0.104.1)
    ✓ pydantic (version: 2.5.0)
    ✓ requests (version: 2.31.0)
    ✓ pyyaml (version: 6.0.1)
    ✓ llm-guard (version: 0.3.16)

✓ All required packages are installed
```

---

## 📋 How It Works

### Step 1: Check requirements.txt exists
```
✓ requirements.txt found
```

### Step 2: Check each package
```
Checking required packages:
  ✓ uvicorn (version: 0.24.0)
  ✗ fastapi NOT installed
  ✓ pydantic (version: 2.5.0)
  ...
```

### Step 3: If packages missing
```
✗ Missing packages: fastapi llm-guard

Install all dependencies with:
  pip install -r requirements.txt

Install missing packages now? (y/n) 
```

### Step 4: User chooses
- **y**: Automatically installs all missing packages
- **n**: Continues (some features may not work)

---

## 🔧 Error Handling

The script handles:
- ✅ Missing requirements.txt (warns but continues)
- ✅ Packages with hyphens (e.g., llm-guard → llm_guard)
- ✅ Packages with unknown versions
- ✅ Installation failures (exits with error message)
- ✅ Works with both venv and system Python

---

## 📝 Example Output - All Installed

```bash
./run_proxy.sh run
```

Output:
```
Step 3: Checking Dependencies
─────────────────────────────────────────────────────────────────
✓ requirements.txt found

  Checking required packages:
    ✓ uvicorn (version: 0.24.0)
    ✓ fastapi (version: 0.104.1)
    ✓ pydantic (version: 2.5.0)
    ✓ requests (version: 2.31.0)
    ✓ pyyaml (version: 6.0.1)
    ✓ llm-guard (version: 0.3.16)

✓ All required packages are installed

Step 4: Checking Configuration...
```

---

## 📝 Example Output - Missing Packages

```bash
./run_proxy.sh run
```

Output:
```
Step 3: Checking Dependencies
─────────────────────────────────────────────────────────────────
✓ requirements.txt found

  Checking required packages:
    ✓ uvicorn (version: 0.24.0)
    ✗ fastapi NOT installed
    ✗ pydantic NOT installed
    ✓ requests (version: 2.31.0)
    ✓ pyyaml (version: 6.0.1)
    ✓ llm-guard (version: 0.3.16)

✗ Missing packages: fastapi pydantic

Install all dependencies with:
  pip install -r requirements.txt

Install missing packages now? (y/n) y

Installing dependencies...
Collecting fastapi==0.104.1 from -r requirements.txt...
...
Successfully installed fastapi-0.104.1 pydantic-2.5.0

✓ Dependencies installed

Step 4: Checking Configuration...
```

---

## 🎯 Use Cases

### 1. **New Installation**
```bash
./run_proxy.sh run
# → Automatically detects missing packages
# → Prompts to install
# → Installs and continues
```

### 2. **After Python Upgrade**
```bash
./run_proxy.sh run
# → Detects all packages need reinstalling
# → Prompts to install
# → Installs all dependencies
```

### 3. **Partial Installation**
```bash
./run_proxy.sh run
# → Detects which packages are missing
# → Lists them specifically
# → User can install just those or all
```

### 4. **Background Start with Check**
```bash
./run_proxy.sh start
# → Still checks dependencies before starting
# → Fails early if packages missing
# → Shows debug info in logs
```

---

## 📊 Supported Packages

From `requirements.txt`:

| Package | Version | Status |
|---------|---------|--------|
| fastapi | 0.104.1 | ✅ Checked |
| uvicorn | 0.24.0 | ✅ Checked |
| pydantic | 2.5.0 | ✅ Checked |
| requests | 2.31.0 | ✅ Checked |
| pyyaml | 6.0.1 | ✅ Checked |
| llm-guard | 0.3.16 | ✅ Checked |

---

## 🔄 Workflow

```
┌─────────────────────────────────────┐
│ ./run_proxy.sh run                   │
└─────────────────────────────────────┘
              │
              v
┌─────────────────────────────────────┐
│ Step 1: Check Python ✓              │
└─────────────────────────────────────┘
              │
              v
┌─────────────────────────────────────┐
│ Step 2: Check Virtual Env ✓         │
└─────────────────────────────────────┘
              │
              v
┌─────────────────────────────────────┐
│ Step 3: Check Dependencies          │
│   - Read requirements.txt           │
│   - Check each package              │
│   - Show versions                   │
│   - Prompt to install if missing    │
└─────────────────────────────────────┘
              │
         ┌────┴────┐
         │         │
       All OK   Missing
         │         │
         v         v
       Skip    Prompt User
       to          │
      Install   ┌──┴──┐
         │      │     │
         │      Y     N
         │      │     │
         │      v     v
         │    Install Skip
         │      │      │
         v      v      v
    ┌─────────────────────────┐
    │ Step 4: Check Config    │
    └─────────────────────────┘
         │
         v
    ┌─────────────────────────┐
    │ Step 5: Start Server    │
    └─────────────────────────┘
```

---

## ✨ Benefits

1. **Automatic Detection** - No manual checking needed
2. **Clear Feedback** - Know exactly what's missing
3. **Interactive** - Ask before installing
4. **Version Info** - See what versions are installed
5. **Intelligent Naming** - Handles package name conversions
6. **Fallback** - Continue even if some packages missing
7. **Works Everywhere** - Works with venv and system Python

---

## 🚀 Testing

### Test 1: With all packages installed
```bash
./run_proxy.sh run --debug
# Expected: All packages shown as ✓
```

### Test 2: With missing packages
```bash
# Temporarily remove a package
pip uninstall -y fastapi

# Then run
./run_proxy.sh run

# Expected: fastapi shown as ✗ with install prompt
```

### Test 3: No requirements.txt
```bash
# Temporarily rename it
mv requirements.txt requirements.txt.bak

# Run script
./run_proxy.sh run

# Expected: Warning but continues

# Restore it
mv requirements.txt.bak requirements.txt
```

---

## 🔧 Implementation Details

### Code Changes

**Location**: `run_proxy.sh` - Step 3 of `run_interactive()` function

**What's New**:
- Reads requirements.txt
- Parses package names
- Checks each package import
- Gets installed versions
- Prompts for installation
- Runs pip install if approved

### Package Name Mapping

```bash
fastapi        → import fastapi ✓
uvicorn        → import uvicorn ✓
pydantic       → import pydantic ✓
requests       → import requests ✓
pyyaml         → import yaml ✓
llm-guard      → import llm_guard ✓
```

---

## 📚 Related Files

- **run_proxy.sh** - Updated (enhanced dependency checking)
- **requirements.txt** - Used for package list
- **DEBUG_GUIDE.md** - References this feature (if exists)
- **QUICK_REFERENCE.md** - Command reference (if exists)

---

## 🎓 Usage Examples

### Example 1: First Time Setup
```bash
cd /home/local/ai4team/guardrails
./run_proxy.sh run

# Output:
# Step 3: Checking Dependencies...
# ✓ requirements.txt found
# Checking required packages:
#   ✓ uvicorn (version: 0.24.0)
#   ✓ fastapi (version: 0.104.1)
#   ...
# ✓ All required packages are installed
```

### Example 2: Missing Package
```bash
pip uninstall -y llm-guard
./run_proxy.sh run

# Output:
# Step 3: Checking Dependencies...
# ✗ Missing packages: llm-guard
# 
# Install all dependencies with:
#   pip install -r requirements.txt
#
# Install missing packages now? (y/n) y
#
# Installing dependencies...
# ✓ Dependencies installed
```

### Example 3: Background Start
```bash
./run_proxy.sh start

# Logs (proxy.log):
# Step 3: Checking Dependencies...
# ✓ requirements.txt found
# Checking required packages:
#   ✓ uvicorn (version: 0.24.0)
#   ...
# ✓ All required packages are installed
```

---

## ✅ Verification

- ✅ Script syntax valid
- ✅ All packages from requirements.txt checked
- ✅ Version detection working
- ✅ Interactive installation prompt
- ✅ Error handling complete
- ✅ Backward compatible
- ✅ Works with venv and system Python

---

## 🎯 Summary

The `run_proxy.sh` script now:
1. ✅ Reads requirements.txt
2. ✅ Checks each required package
3. ✅ Reports installation status
4. ✅ Shows installed versions
5. ✅ Prompts to install missing packages
6. ✅ Automatically installs if approved
7. ✅ Continues or fails gracefully

**Status**: Ready to use! 🚀

---

**Last Updated:** October 23, 2025  
**Version:** 2.1 - Dependency Check Enhanced  
**Status:** ✅ Production Ready
