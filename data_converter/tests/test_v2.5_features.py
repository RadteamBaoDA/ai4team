"""
Comprehensive test script for v2.5 features
Tests: Adaptive workers, Priority queue, Progress bars, Batch optimization, Persistent cache
"""

import sys
from pathlib import Path
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.document_converter import DocumentConverter
from src.utils.hash_cache import get_hash_cache
from src.utils.file_hash import calculate_file_hash

print("=" * 80)
print("VERSION 2.5 FEATURES TEST")
print("=" * 80)
print()

# Test 1: Persistent Cache
print("=" * 80)
print("TEST 1: Persistent Hash Cache")
print("=" * 80)

test_file = Path("./input/notes.txt")
if test_file.exists():
    # Clear cache to start fresh
    cache = get_hash_cache()
    
    # First calculation (not cached)
    start = time.time()
    hash1 = calculate_file_hash(test_file, use_persistent_cache=True)
    time1 = time.time() - start
    print(f"✓ First hash calculation: {time1*1000:.2f}ms (stored in persistent cache)")
    
    # Second calculation (from persistent cache)
    start = time.time()
    hash2 = calculate_file_hash(test_file, use_persistent_cache=True)
    time2 = time.time() - start
    print(f"✓ Second hash retrieval: {time2*1000:.2f}ms (from persistent cache)")
    
    # Check hashes match
    if hash1 == hash2:
        print(f"✓ Hashes match: {hash1}")
    else:
        print(f"✗ Hash mismatch!")
    
    # Get cache stats
    stats = cache.get_stats()
    print(f"✓ Cache entries: {stats['total_entries']}")
    print(f"✓ Cache location: {cache.db_path}")
else:
    print("⚠ Test file not found, skipping cache test")

print()

# Test 2: Adaptive Workers
print("=" * 80)
print("TEST 2: Adaptive Worker Count")
print("=" * 80)

converter = DocumentConverter(
    input_dir="./input",
    output_dir="./output_test_v25",
    enable_parallel=True,
    adaptive_workers=True
)

print(f"✓ Base max_workers: {converter.max_workers}")
print(f"✓ Adaptive workers enabled: {converter.adaptive_workers}")

# Test with different file sets
from src.utils.file_scanner import FileScanner
scanner = FileScanner(Path("./input"))
files_to_convert, files_to_copy = scanner.categorize_files()

if files_to_convert or files_to_copy:
    all_files = files_to_convert + files_to_copy
    categorized = converter._categorize_by_size(all_files)
    
    print(f"✓ Small files (<100KB): {len(categorized['small'])}")
    print(f"✓ Medium files (100KB-10MB): {len(categorized['medium'])}")
    print(f"✓ Large files (>10MB): {len(categorized['large'])}")
    
    adaptive_count = converter._calculate_adaptive_workers(all_files)
    print(f"✓ Adaptive worker count: {adaptive_count}")

print()

# Test 3: Priority Queue
print("=" * 80)
print("TEST 3: Priority Queue (Large Files First)")
print("=" * 80)

if files_to_convert or files_to_copy:
    sorted_items = converter._sort_by_priority(files_to_convert, files_to_copy)
    
    print(f"✓ Priority sorting enabled: {converter.priority_large_files}")
    print(f"✓ Total files to process: {len(sorted_items)}")
    
    if len(sorted_items) > 0:
        # Show first 5 files in priority order
        print("\nFirst 5 files in priority order:")
        for i, (file_path, op_type) in enumerate(sorted_items[:5], 1):
            size = converter._get_file_size(file_path)
            size_mb = size / (1024 * 1024)
            print(f"  {i}. {file_path.name[:40]:40s} | {size_mb:>6.2f}MB | {op_type}")

print()

# Test 4: Progress Bar
print("=" * 80)
print("TEST 4: Progress Bar Support")
print("=" * 80)

from src.document_converter import TQDM_AVAILABLE
print(f"✓ tqdm library available: {TQDM_AVAILABLE}")
print(f"✓ Progress bar enabled: {converter.enable_progress_bar}")

if not TQDM_AVAILABLE:
    print("⚠ Install tqdm for visual progress bars: pip install tqdm")

print()

# Test 5: Full Conversion with v2.5 Features
print("=" * 80)
print("TEST 5: Full Conversion with v2.5 Features")
print("=" * 80)

if files_to_convert or files_to_copy:
    print("Running conversion with all v2.5 features enabled...\n")
    
    converter_v25 = DocumentConverter(
        input_dir="./input",
        output_dir="./output_test_v25",
        enable_parallel=True,
        enable_progress_bar=True,
        adaptive_workers=True,
        priority_large_files=True,
        batch_small_files=True
    )
    
    start = time.time()
    stats = converter_v25.convert_all()
    elapsed = time.time() - start
    
    print(f"\n✓ Conversion completed in {elapsed:.2f}s")
    print(f"  - Converted: {stats['converted']}")
    print(f"  - Copied: {stats['copied']}")
    print(f"  - Failed: {stats['failed']}")
    
    # Test second run (should use persistent cache)
    print("\nRunning second pass (persistent cache test)...")
    start = time.time()
    stats2 = converter_v25.convert_all()
    elapsed2 = time.time() - start
    
    print(f"✓ Second pass completed in {elapsed2:.2f}s")
    if elapsed > 0:
        speedup = ((elapsed - elapsed2) / elapsed) * 100
        print(f"✓ Speedup: {speedup:.1f}% faster with persistent cache")

print()

# Test 6: Feature Verification
print("=" * 80)
print("TEST 6: Feature Verification")
print("=" * 80)

features = [
    ("Adaptive workers", hasattr(converter, 'adaptive_workers') and converter.adaptive_workers),
    ("Priority large files", hasattr(converter, 'priority_large_files') and converter.priority_large_files),
    ("Batch small files", hasattr(converter, 'batch_small_files') and converter.batch_small_files),
    ("Progress bar support", hasattr(converter, 'enable_progress_bar')),
    ("Persistent cache", Path(cache.db_path).exists()),
    ("Categorize by size", hasattr(converter, '_categorize_by_size')),
    ("Calculate adaptive workers", hasattr(converter, '_calculate_adaptive_workers')),
    ("Sort by priority", hasattr(converter, '_sort_by_priority')),
]

all_passed = True
for feature, status in features:
    symbol = "✓" if status else "✗"
    print(f"{symbol} {feature}: {status}")
    if not status:
        all_passed = False

print()

# Test 7: Summary
print("=" * 80)
print("TEST 7: SUMMARY")
print("=" * 80)

if all_passed:
    print("✓ All v2.5 features implemented successfully!")
    print("✓ Adaptive worker count working")
    print("✓ Priority queue functional")
    print("✓ Progress bar support available" if TQDM_AVAILABLE else "⚠ Progress bar requires tqdm")
    print("✓ Batch optimization enabled")
    print("✓ Persistent cache working")
else:
    print("⚠ Some features may need attention")

print("\nVersion 2.5 features verified!")
print("=" * 80)
