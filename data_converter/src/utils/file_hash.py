"""
File hash utilities for comparing files with performance optimizations
"""

import hashlib
from pathlib import Path
from typing import Optional
from functools import lru_cache


# Optimized chunk size for better performance (64KB)
CHUNK_SIZE = 65536


@lru_cache(maxsize=128)
def calculate_file_hash(file_path: Path, algorithm: str = 'md5') -> str:
    """
    Calculate hash of a file with caching for better performance
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use (default: md5)
        
    Returns:
        Hex digest of file hash
    """
    hash_obj = hashlib.new(algorithm)
    
    try:
        # Convert to string for hashable cache key
        file_path = Path(file_path)
        
        with open(file_path, 'rb') as f:
            # Read file in optimized chunks for large files
            while chunk := f.read(CHUNK_SIZE):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception:
        return ""


def files_are_identical(file1: Path, file2: Path) -> bool:
    """
    Check if two files have the same content by comparing hashes
    Optimized with size check and early exit
    
    Args:
        file1: First file path
        file2: Second file path
        
    Returns:
        True if files have identical content, False otherwise
    """
    if not file1.exists() or not file2.exists():
        return False
    
    # Quick check: if sizes are different, files are different (avoid hash calculation)
    size1 = file1.stat().st_size
    size2 = file2.stat().st_size
    
    if size1 != size2:
        return False
    
    # For very small files, just compare directly
    if size1 < 1024:  # Less than 1KB
        try:
            with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
                return f1.read() == f2.read()
        except Exception:
            return False
    
    # Compare hashes for larger files
    hash1 = calculate_file_hash(file1)
    hash2 = calculate_file_hash(file2)
    
    return hash1 == hash2 and hash1 != ""


def should_skip_conversion(input_file: Path, output_file: Path) -> bool:
    """
    Check if conversion should be skipped because output already exists
    and matches input
    
    Args:
        input_file: Source file
        output_file: Destination file
        
    Returns:
        True if conversion should be skipped, False otherwise
    """
    # If output doesn't exist, we need to convert
    if not output_file.exists():
        return False
    
    # For copy operations (same extension), check if files are identical
    if input_file.suffix.lower() == output_file.suffix.lower():
        return files_are_identical(input_file, output_file)
    
    # For conversion operations (different extensions), always reconvert
    # unless we want to add more sophisticated checking
    return False


def should_skip_copy(input_file: Path, output_file: Path) -> bool:
    """
    Check if copy should be skipped because output already exists
    and is identical to input
    
    Args:
        input_file: Source file
        output_file: Destination file
        
    Returns:
        True if copy should be skipped, False otherwise
    """
    # If output doesn't exist, we need to copy
    if not output_file.exists():
        return False
    
    # Check if files are identical
    return files_are_identical(input_file, output_file)
