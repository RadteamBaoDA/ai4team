# 📦 Dependency Check Feature - Quick Reference

## What's New

The `run_proxy.sh` script now **automatically checks if all packages from requirements.txt are installed** and optionally installs them.

---

## Quick Start

### Run the script normally
```bash
./run_proxy.sh run
```

**If all packages are installed:**
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

**If packages are missing:**
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

Install missing packages now? (y/n) _
```

---

## Features

| Feature | Details |
|---------|---------|
| **Auto-Detection** | Automatically detects missing packages |
| **Version Reporting** | Shows installed version for each package |
| **Interactive** | Asks before installing (y/n prompt) |
| **Automatic Install** | Can install all missing packages with one command |
| **Package Support** | Checks all 6 packages from requirements.txt |
| **Smart Naming** | Handles package names with hyphens (llm-guard → llm_guard) |
| **Fallback** | Continues setup even if installation skipped |

---

## Packages Checked

From `requirements.txt`:

1. **fastapi** (0.104.1) - Web framework
2. **uvicorn** (0.24.0) - ASGI server
3. **pydantic** (2.5.0) - Data validation
4. **requests** (2.31.0) - HTTP library
5. **pyyaml** (6.0.1) - YAML parsing
6. **llm-guard** (0.3.16) - LLM guardrails

---

## Usage Examples

### Example 1: All packages installed ✓
```bash
./run_proxy.sh run --debug
```
Output shows all ✓, proceeds to start server.

### Example 2: Missing packages ✗
```bash
./run_proxy.sh run
```
Detects missing packages, prompts to install.

### Example 3: Skip installation
```bash
./run_proxy.sh run
# When asked: Install missing packages now? (y/n)
# Type: n
# Server continues with warnings
```

### Example 4: Auto install
```bash
./run_proxy.sh run
# When asked: Install missing packages now? (y/n)
# Type: y
# Packages install automatically
# Server starts
```

---

## Troubleshooting

### Issue: "uvicorn NOT installed"

**Solution 1 (Interactive - Recommended):**
```bash
./run_proxy.sh run
# Type 'y' when prompted to install packages
```

**Solution 2 (Manual):**
```bash
source ./venv/bin/activate
pip install -r requirements.txt
./run_proxy.sh start
```

### Issue: "pip install fails"

Check permissions:
```bash
# If using venv (recommended)
source ./venv/bin/activate
pip install -r requirements.txt

# If using system Python
sudo pip install -r requirements.txt
```

### Issue: "requirements.txt not found"

The script warns but continues:
```bash
⚠ Warning: requirements.txt not found
  Skipping dependency check
```

Create requirements.txt in the same directory as `run_proxy.sh`.

---

## Command Reference

| Command | Does |
|---------|------|
| `./run_proxy.sh run` | Interactive mode - checks deps, asks to install |
| `./run_proxy.sh run --debug` | Adds debug logging to dependency checks |
| `./run_proxy.sh start` | Background mode - checks deps before starting |
| `pip install -r requirements.txt` | Manually install all packages |
| `pip list` | See what's installed |

---

## How It Works

```
1. Check if requirements.txt exists
   ├─ If YES: Parse package list
   └─ If NO: Warn and skip

2. For each package in requirements.txt
   ├─ Try to import it
   ├─ If found: Show version ✓
   └─ If NOT found: Add to missing list ✗

3. If packages missing
   ├─ Show which ones are missing
   ├─ Show install command
   └─ Ask user: "Install now? (y/n)"

4. If user says YES
   ├─ Run: pip install -r requirements.txt
   └─ Show progress

5. If all OK (or user skips)
   └─ Continue to Step 4 (Configuration check)
```

---

## Key Improvements

✅ **Before**: Had to manually check and install packages  
✅ **Now**: Script detects and offers to install automatically

✅ **Before**: Vague errors like "module not found"  
✅ **Now**: Clear message showing exactly which packages are missing

✅ **Before**: No version information  
✅ **Now**: Shows installed version of each package

✅ **Before**: Had to look at requirements.txt file  
✅ **Now**: Script reads and checks requirements automatically

---

## Testing

### Test 1: Verify all packages installed
```bash
./run_proxy.sh run
# Should show all packages as ✓
```

### Test 2: Simulate missing package
```bash
# Uninstall a package
pip uninstall -y fastapi

# Run script
./run_proxy.sh run
# Should show fastapi as ✗ and offer to install
```

### Test 3: Test installation
```bash
./run_proxy.sh run
# When prompted: y
# Packages should install
# Server should start
```

---

## File Changes

**Modified**: `run_proxy.sh`
- Location: Step 3 of `run_interactive()` function  
- Lines: ~585-630
- Changes: Enhanced dependency checking logic

**Updated**: Dependencies now checked against all packages in `requirements.txt`

---

## Backward Compatibility

✅ All existing commands work unchanged:
- `./run_proxy.sh start` - Works (with enhanced check)
- `./run_proxy.sh stop` - Works
- `./run_proxy.sh restart` - Works
- `./run_proxy.sh status` - Works
- `./run_proxy.sh logs` - Works
- `./run_proxy.sh run` - Works (with new feature)

✅ Environment variables still supported:
- `VENV_DIR`
- `USE_VENV`
- `OLLAMA_URL`
- All others

✅ Configuration files unchanged:
- `requirements.txt` - Used for package list
- `config.yaml` - Used for proxy config
- All others

---

## Performance Impact

- **Startup time**: +1-2 seconds (pip check)
- **Memory**: No additional overhead
- **Network**: Only when installing packages
- **Runtime**: No impact once started

---

## Related Documentation

- **DEPENDENCY_CHECK_UPDATE.md** - Detailed feature documentation
- **run_proxy.sh** - Script with implementation
- **requirements.txt** - Package list

---

## Next Steps

1. **Run the script**:
   ```bash
   ./run_proxy.sh run --debug
   ```

2. **Watch dependency check**:
   - See Step 3 output
   - Note version information

3. **If packages missing**:
   - Type 'y' to install
   - Or type 'n' to skip

4. **Server starts**:
   - Proxy is ready
   - Test with: `curl http://localhost:9999/health`

---

## Summary

| Before | After |
|--------|-------|
| Manual package install | Automatic detection + install |
| Vague errors | Clear missing package list |
| No version info | Version reporting |
| Manual requirement check | Automatic from requirements.txt |
| Optional dependencies ignored | All requirements verified |

---

**Status**: ✅ Ready to use  
**Last Updated**: October 23, 2025  
**Version**: 2.1
