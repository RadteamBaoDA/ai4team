# Quick Reference: v2.5 Features

Quick guide to using the new v2.5 intelligent workload management features.

---

## 🚀 Quick Start

### Installation
```bash
# Install dependencies with uv (includes tqdm for progress bars)
uv venv ../.venv
uv pip install --python ../.venv/bin/python -r requirements.txt

# Verify installation
python tests/test_v2.5_features.py
```

### Basic Usage (All v2.5 Features Enabled)
```python
from src.document_converter import DocumentConverter

# All v2.5 features enabled by default
converter = DocumentConverter(
    input_dir="./input",
    output_dir="./output"
)

# Watch the progress bar in action!
stats = converter.convert_all()
```

**Output:**
```
Processing files: 100%|████████████████████| 15/15 [00:25<00:00]
✓ giao trinh (1).docx
✓ Performance_Testing_Presentation.pptx
```

---

## 💾 Persistent Hash Cache

### What it does
Stores file hashes in SQLite database across sessions. Files are only reconverted when they actually change.

### Configuration
```python
# Enabled by default, cache stored at logs/hash_cache.db
converter = DocumentConverter()

# Cache is automatic - no configuration needed!
```

### Benefits
- **13.1% faster** on subsequent runs
- Survives application restarts
- Automatic cleanup of old entries (>30 days)

### Check Cache Stats
```python
from src.utils.hash_cache import get_hash_cache

cache = get_hash_cache()
stats = cache.get_stats()
print(f"Cache entries: {stats['count']}")
```

### Clear Cache
```python
cache.clear_old_entries(days=7)  # Clear entries older than 7 days
```

---

## 🧠 Adaptive Worker Count

### What it does
Dynamically adjusts parallel workers based on file sizes.

### How it works
```python
# Mostly large files (>10MB): Uses 50% fewer workers
# Example: 8 base workers → 4 adaptive workers

# Mostly small files (<100KB): Uses 2x more workers
# Example: 4 base workers → 8 adaptive workers

# Mixed files: Uses base worker count
# Example: 7 base workers → 7 adaptive workers
```

### Configuration
```python
# Enable (default)
converter = DocumentConverter(adaptive_workers=True)

# Disable - use static worker count
converter = DocumentConverter(adaptive_workers=False, max_workers=4)
```

### File Size Thresholds
- **Small**: < 100KB
- **Medium**: 100KB - 10MB
- **Large**: > 10MB

### Example Output
```
✓ Small files (<100KB): 9
✓ Medium files (100KB-10MB): 5
✓ Large files (>10MB): 1
✓ Adaptive worker count: 7
```

---

## 📊 Priority Queue

### What it does
Processes large files first for better perceived performance.

### Configuration
```python
# Enable (default)
converter = DocumentConverter(priority_large_files=True)

# Disable - process in discovery order
converter = DocumentConverter(priority_large_files=False)
```

### Example
```python
# Files processed in this order:
# 1. large_report.pdf (17.91MB)
# 2. presentation.doc (1.68MB)
# 3. manual.pdf (1.13MB)
# 4. small_note.txt (5KB)
```

### Why it matters
- Users see important files converted first
- Better system resource utilization
- Smoother progress reporting

---

## 📊 Progress Bars

### What it does
Shows real-time conversion progress with beautiful tqdm bars.

### Configuration
```python
# Enable (default, requires tqdm)
converter = DocumentConverter(enable_progress_bar=True)

# Disable - silent operation
converter = DocumentConverter(enable_progress_bar=False)
```

### What you see
```
Processing files:  73%|████████████████▊| 11/15 [00:04<00:01]
✓ Chi_Tiet_Performance_Testing_Presentation.pptx
```

### Features
- ✓/✗ symbols for success/failure
- Elapsed and remaining time
- Current file name
- Completion percentage
- File count (current/total)

### Fallback
If tqdm is not installed:
- Converter still works normally
- No progress bar displayed
- Log messages show progress

---

## 📦 Batch Optimization

### What it does
Groups files by size for optimized processing.

### Configuration
```python
# Enable (default)
converter = DocumentConverter(batch_small_files=True)

# Disable
converter = DocumentConverter(batch_small_files=False)
```

### Categories
```python
small = []   # < 100KB
medium = []  # 100KB - 10MB
large = []   # > 10MB
```

### Benefits
- Small files: Processed quickly with more workers
- Large files: Processed carefully with fewer workers
- Better resource utilization

---

## 🔧 Configuration Examples

### Example 1: All Features Enabled (Default)
```python
converter = DocumentConverter(
    input_dir="./documents",
    output_dir="./pdfs",
    enable_progress_bar=True,
    adaptive_workers=True,
    priority_large_files=True,
    batch_small_files=True
)
stats = converter.convert_all()
```

### Example 2: Silent Mode (No Progress Bar)
```python
converter = DocumentConverter(
    input_dir="./documents",
    output_dir="./pdfs",
    enable_progress_bar=False
)
stats = converter.convert_all()
```

### Example 3: Static Workers (No Adaptation)
```python
converter = DocumentConverter(
    input_dir="./documents",
    output_dir="./pdfs",
    adaptive_workers=False,
    max_workers=4  # Fixed at 4 workers
)
stats = converter.convert_all()
```

### Example 4: Original Order (No Priority)
```python
converter = DocumentConverter(
    input_dir="./documents",
    output_dir="./pdfs",
    priority_large_files=False
)
stats = converter.convert_all()
```

### Example 5: Minimal Features
```python
converter = DocumentConverter(
    input_dir="./documents",
    output_dir="./pdfs",
    enable_progress_bar=False,
    adaptive_workers=False,
    priority_large_files=False,
    batch_small_files=False,
    max_workers=4
)
stats = converter.convert_all()
```

---

## 📈 Performance Tips

### 1. First Run vs. Second Run
```bash
# First run: Calculates hashes, stores in cache
python main.py  # 25.27s

# Second run: Uses cached hashes
python main.py  # 21.97s (13.1% faster!)
```

### 2. Large Files
```python
# For directories with mostly large files
converter = DocumentConverter(
    adaptive_workers=True,  # Reduces workers automatically
    priority_large_files=True  # Process large files first
)
```

### 3. Small Files
```python
# For directories with mostly small files
converter = DocumentConverter(
    adaptive_workers=True,  # Increases workers automatically
    batch_small_files=True  # Optimizes batching
)
```

### 4. Mixed Workloads
```python
# For mixed file sizes (recommended default)
converter = DocumentConverter()  # All features enabled
```

---

## 🔍 Troubleshooting

### Progress Bar Not Showing
```bash
# Check if tqdm is installed
uv pip show tqdm

# Install if missing
uv pip install tqdm>=4.66.0
```

### Cache Not Working
```python
# Check cache location
from src.utils.hash_cache import get_hash_cache
cache = get_hash_cache()
print(f"Cache DB: {cache.db_path}")

# Clear cache if corrupted
cache.clear_old_entries(days=0)
```

### Worker Count Not Adapting
```python
# Verify adaptive_workers is enabled
converter = DocumentConverter(adaptive_workers=True)

# Check file categorization
from pathlib import Path
files = list(Path("./input").rglob("*"))
categorized = converter._categorize_by_size(files)
print(f"Small: {len(categorized['small'])}")
print(f"Medium: {len(categorized['medium'])}")
print(f"Large: {len(categorized['large'])}")
```

---

## 📚 See Also

- **WHATS_NEW_V2.5.md**: Detailed feature explanations
- **README.md**: Full documentation
- **CHANGELOG.md**: Version history
- **tests/test_v2.5_features.py**: Test suite

---

## 🎯 Quick Command Reference

```bash
# Install v2.5 with uv
uv venv ../.venv
uv pip install --python ../.venv/bin/python -r requirements.txt

# Run tests
python tests/test_v2.5_features.py

# Basic conversion (all features)
python main.py

# Check cache stats
python -c "from src.utils.hash_cache import get_hash_cache; print(get_hash_cache().get_stats())"

# Clear old cache entries
python -c "from src.utils.hash_cache import get_hash_cache; get_hash_cache().clear_old_entries(30)"
```

---

**Version 2.5** - Intelligent workload management at your fingertips! 🚀
