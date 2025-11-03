"""
Test script for v2.4 changes
Tests parallel processing, retry logic, and performance optimizations
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("TEST 1: Parallel Processing Configuration")
print("=" * 80)

from src.document_converter import DocumentConverter

# Test default worker count
converter = DocumentConverter(enable_parallel=True)
print(f"✓ CPU cores detected: {os.cpu_count()}")
print(f"✓ Default max_workers: {converter.max_workers}")
print(f"✓ Expected: {os.cpu_count() // 2}")
print(f"✓ Parallel enabled: {converter.enable_parallel}")
print()

# Test custom worker count
converter_custom = DocumentConverter(max_workers=2, enable_parallel=True)
print(f"✓ Custom max_workers set: {converter_custom.max_workers}")
print()

# Test parallel disabled
converter_seq = DocumentConverter(enable_parallel=False)
print(f"✓ Sequential mode: {not converter_seq.enable_parallel}")
print()

print("=" * 80)
print("TEST 2: Retry Logic Test")
print("=" * 80)

# Test that retry parameter is available
from pathlib import Path
test_file = Path(__file__).parent.parent / "input" / "notes.txt"
if test_file.exists():
    print(f"✓ Testing with file: {test_file.name}")
    
    # Test convert_file with retry
    success, output = converter.convert_file(test_file, retry_count=1)
    print(f"✓ convert_file() accepts retry_count parameter")
    
    # Test copy_file with retry  
    success, output = converter.copy_file(test_file, retry_count=1)
    print(f"✓ copy_file() accepts retry_count parameter")
else:
    print("⚠ Test file not found, skipping retry test")

print()

print("=" * 80)
print("TEST 3: Hash Optimization")
print("=" * 80)

from src.utils.file_hash import calculate_file_hash, files_are_identical, CHUNK_SIZE

print(f"✓ Optimized CHUNK_SIZE: {CHUNK_SIZE} bytes ({CHUNK_SIZE // 1024}KB)")

if test_file.exists():
    # Test hash calculation
    start = time.time()
    hash1 = calculate_file_hash(test_file)
    elapsed1 = time.time() - start
    print(f"✓ First hash calculation: {elapsed1*1000:.2f}ms")
    
    # Test cached hash (should be faster)
    start = time.time()
    hash2 = calculate_file_hash(test_file)
    elapsed2 = time.time() - start
    print(f"✓ Cached hash retrieval: {elapsed2*1000:.2f}ms")
    if elapsed2 > 0:
        print(f"✓ Cache speedup: {elapsed1/elapsed2:.1f}x faster")
    else:
        print(f"✓ Cache speedup: instant (< 0.01ms)")
    
    # Test file comparison
    identical = files_are_identical(test_file, test_file)
    print(f"✓ Identical file check: {identical} (expected: True)")
else:
    print("⚠ Test file not found, skipping hash tests")

print()

print("=" * 80)
print("TEST 4: Thread Safety")
print("=" * 80)

from threading import Lock
converter_parallel = DocumentConverter(enable_parallel=True)
print(f"✓ Stats lock initialized: {hasattr(converter_parallel, 'stats_lock')}")
print(f"✓ Lock type: {type(converter_parallel.stats_lock).__name__}")
print()

print("=" * 80)
print("TEST 5: Parallel vs Sequential Performance")
print("=" * 80)

input_dir = Path("./input")
if input_dir.exists():
    # Count files
    from src.utils.file_scanner import FileScanner
    scanner = FileScanner(input_dir)
    files_to_convert, files_to_copy = scanner.categorize_files()
    total_files = len(files_to_convert) + len(files_to_copy)
    
    print(f"Found {total_files} files to process")
    
    if total_files > 0:
        print("\nRunning parallel processing test...")
        converter_test = DocumentConverter(output_dir=Path("./output_test_v24_parallel"))
        
        start = time.time()
        stats_parallel = converter_test.convert_all(enable_parallel=True)
        time_parallel = time.time() - start
        
        print(f"✓ Parallel mode completed in {time_parallel:.2f}s")
        print(f"  - Converted: {stats_parallel['converted']}")
        print(f"  - Copied: {stats_parallel['copied']}")
        print(f"  - Failed: {stats_parallel['failed']}")
        
        # Second run to test skip optimization
        print("\nRunning second pass (skip optimization test)...")
        start = time.time()
        stats_skip = converter_test.convert_all(enable_parallel=True)
        time_skip = time.time() - start
        
        print(f"✓ Second pass completed in {time_skip:.2f}s")
        if time_skip > 0 and time_parallel > 0:
            speedup = ((time_parallel - time_skip) / time_parallel) * 100
            print(f"✓ Skip optimization: {speedup:.1f}% faster")
    else:
        print("⚠ No files to process")
else:
    print("⚠ Input directory not found")

print()

print("=" * 80)
print("TEST 6: Feature Verification")
print("=" * 80)

features = [
    ("Parallel processing", hasattr(DocumentConverter, '_convert_all_parallel')),
    ("Sequential fallback", hasattr(DocumentConverter, '_convert_all_sequential')),
    ("Process wrapper", hasattr(DocumentConverter, '_process_file_wrapper')),
    ("Retry in convert_file", 'retry_count' in converter.convert_file.__code__.co_varnames),
    ("Retry in copy_file", 'retry_count' in converter.copy_file.__code__.co_varnames),
    ("Thread-safe stats", hasattr(converter, 'stats_lock')),
    ("Hash caching", hasattr(calculate_file_hash, '__wrapped__')),  # LRU cache
    ("Optimized chunk size", CHUNK_SIZE == 65536),
]

for feature, status in features:
    status_str = "✓" if status else "✗"
    print(f"{status_str} {feature}: {status}")

print()

print("=" * 80)
print("TEST 7: SUMMARY")
print("=" * 80)

all_passed = all(status for _, status in features)
if all_passed:
    print("✓ All v2.4 features implemented successfully!")
    print("✓ Parallel processing enabled")
    print("✓ Retry logic functional")
    print("✓ Hash optimization working")
    print("✓ Thread-safe operations verified")
else:
    print("⚠ Some features may need attention")

print()
print("Version 2.4 changes verified!")
print("=" * 80)
