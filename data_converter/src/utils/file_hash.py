"""File hash utilities with caching and safety optimisations."""

from functools import lru_cache
import hashlib
from pathlib import Path

# Optimised chunk size for better performance (64KB)
CHUNK_SIZE = 65_536


@lru_cache(maxsize=128)
def _calculate_file_hash_cached(
    path_str: str,
    algorithm: str,
    modified_ns: int,
    file_size: int,
) -> str:
    """Internal helper to cache file hash values in memory.

    The cache key includes the absolute path, last-modified timestamp (ns), and
    file size so cached values stay valid even when files change in place.
    """

    try:
        hash_obj = hashlib.new(algorithm)
    except ValueError:
        return ""

    try:
        with open(path_str, "rb") as source:
            while chunk := source.read(CHUNK_SIZE):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception:
        return ""


def calculate_file_hash(file_path: Path, algorithm: str = "md5", use_persistent_cache: bool = True) -> str:
    """Calculate a hash for the given file with resilient caching.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (default: md5)
        use_persistent_cache: Use persistent SQLite cache (default: True)
    
    Returns:
        Hex digest of file hash
    """

    path_obj = Path(file_path)

    try:
        stat_info = path_obj.stat()
    except (FileNotFoundError, PermissionError, OSError):
        return ""

    file_size = stat_info.st_size
    modified_ns = getattr(stat_info, "st_mtime_ns", int(stat_info.st_mtime * 1_000_000_000))
    
    # Try persistent cache first (v2.5 feature)
    if use_persistent_cache:
        try:
            from .hash_cache import get_hash_cache
            cache = get_hash_cache()
            cached_hash = cache.get(path_obj, file_size, modified_ns, algorithm)
            if cached_hash:
                return cached_hash
        except Exception:
            # Fall back to memory cache if persistent cache fails
            pass
    
    # Calculate hash (will use memory cache)
    hash_value = _calculate_file_hash_cached(
        str(path_obj.resolve()),
        algorithm,
        modified_ns,
        file_size,
    )
    
    # Store in persistent cache
    if use_persistent_cache and hash_value:
        try:
            from .hash_cache import get_hash_cache
            cache = get_hash_cache()
            cache.set(path_obj, file_size, modified_ns, hash_value, algorithm)
        except Exception:
            # Silently ignore cache write failures
            pass
    
    return hash_value


# Expose cache helpers for compatibility with existing diagnostics/tests.
calculate_file_hash.cache_info = _calculate_file_hash_cached.cache_info  # type: ignore[attr-defined]
calculate_file_hash.cache_clear = _calculate_file_hash_cached.cache_clear  # type: ignore[attr-defined]
calculate_file_hash.__wrapped__ = _calculate_file_hash_cached  # type: ignore[attr-defined]


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
