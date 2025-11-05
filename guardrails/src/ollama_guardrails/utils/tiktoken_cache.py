"""
Tiktoken offline mode configuration for local model caching.

This module configures tiktoken to use local cache directory instead of
downloading encoding files from Azure. This enables offline operation
and reduces network dependencies.

Also initializes Hugging Face offline mode for transformer models.

Environment Variables:
    TIKTOKEN_CACHE_DIR: Path to local tiktoken cache directory (default: ./models/tiktoken_cache)
    TIKTOKEN_OFFLINE_MODE: Enable offline mode (default: true)
    TIKTOKEN_FALLBACK_LOCAL: Use local models as fallback (default: true)
    HF_HOME: Hugging Face home directory (default: ./models/huggingface)
    HF_OFFLINE: Enable HF offline mode (default: true)
    TRANSFORMERS_OFFLINE: Enable transformers offline mode (default: true)
"""

import os
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _setup_huggingface_env() -> None:
    """Setup Hugging Face environment variables for offline mode."""
    try:
        # Import the HF setup function to avoid circular imports
        from .huggingface_cache import setup_huggingface_offline_mode
        setup_huggingface_offline_mode()
    except Exception as e:
        logger.debug(f'Could not setup Hugging Face offline mode: {e}')


def setup_tiktoken_offline_mode(cache_dir: Optional[str] = None) -> bool:
    """
    Configure tiktoken for offline mode using local cache directory.
    Also configures Hugging Face for offline operation.
    
    This function must be called BEFORE importing tiktoken or llm-guard.
    It sets environment variables to ensure tiktoken uses local files
    instead of attempting to download from Azure.
    
    Args:
        cache_dir: Optional path to tiktoken cache directory.
                   If None, uses TIKTOKEN_CACHE_DIR env var or default './models/tiktoken_cache'
    
    Returns:
        bool: True if offline mode was successfully configured, False otherwise
    
    Example:
        >>> from ollama_guardrails.utils.tiktoken_cache import setup_tiktoken_offline_mode
        >>> setup_tiktoken_offline_mode()
        >>> # Now safe to import tiktoken or llm-guard
        >>> import tiktoken
    """
    try:
        # Setup Hugging Face offline mode first
        _setup_huggingface_env()
        
        # Determine cache directory
        if cache_dir is None:
            cache_dir = os.environ.get('TIKTOKEN_CACHE_DIR', './models/tiktoken_cache')
        
        cache_dir = os.path.abspath(cache_dir)
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        logger.info(f"Tiktoken cache directory: {cache_dir}")
        
        # Set environment variables for tiktoken
        os.environ['TIKTOKEN_CACHE_DIR'] = cache_dir
        
        # Disable Azure remote access (OpenAI environment variable)
        os.environ['TIKTOKEN_OFFLINE_MODE'] = os.environ.get('TIKTOKEN_OFFLINE_MODE', 'true')
        
        # Enable local fallback
        os.environ['TIKTOKEN_FALLBACK_LOCAL'] = os.environ.get('TIKTOKEN_FALLBACK_LOCAL', 'true')
        
        logger.info('Tiktoken offline mode configured successfully')
        logger.info(f'  Cache dir: {cache_dir}')
        logger.info(f'  Offline mode: {os.environ.get("TIKTOKEN_OFFLINE_MODE")}')
        logger.info(f'  Fallback local: {os.environ.get("TIKTOKEN_FALLBACK_LOCAL")}')
        
        return True
        
    except Exception as e:
        logger.error(f'Failed to configure tiktoken offline mode: {e}')
        return False


def ensure_tiktoken_cache_dir(base_path: str = './models') -> str:
    """
    Ensure tiktoken cache directory exists and return its path.
    
    Args:
        base_path: Base path for models directory (default: './models')
    
    Returns:
        str: Absolute path to tiktoken cache directory
    """
    tiktoken_cache = os.path.join(base_path, 'tiktoken')
    tiktoken_cache = os.path.abspath(tiktoken_cache)
    os.makedirs(tiktoken_cache, exist_ok=True)
    return tiktoken_cache


def download_tiktoken_encoding(encoding_name: str = 'cl100k_base', 
                               cache_dir: Optional[str] = None) -> bool:
    """
    Download and cache a specific tiktoken encoding locally.
    
    This function downloads encoding files from OpenAI and stores them locally
    for offline use. Call this during setup to pre-download required encodings.
    
    Args:
        encoding_name: Name of encoding to download (default: 'cl100k_base')
        cache_dir: Cache directory (default: from TIKTOKEN_CACHE_DIR env var)
    
    Returns:
        bool: True if encoding was successfully cached, False otherwise
    
    Example:
        >>> from ollama_guardrails.utils.tiktoken_cache import download_tiktoken_encoding
        >>> download_tiktoken_encoding('cl100k_base', './models/tiktoken_cache')
        >>> download_tiktoken_encoding('p50k_base', './models/tiktoken_cache')
    """
    try:
        # Setup offline mode first
        setup_tiktoken_offline_mode(cache_dir)
        
        # Import tiktoken after environment setup
        try:
            import tiktoken
        except ImportError:
            logger.error('tiktoken is not installed. Install with: pip install tiktoken')
            return False
        
        logger.info(f'Downloading tiktoken encoding: {encoding_name}')
        
        # This will download and cache the encoding
        encoding = tiktoken.get_encoding(encoding_name)
        
        logger.info(f'Successfully cached encoding: {encoding_name}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to download tiktoken encoding {encoding_name}: {e}')
        return False


def get_tiktoken_cache_info() -> dict:
    """
    Get information about tiktoken cache configuration.
    
    Returns:
        dict: Information about tiktoken cache setup
    """
    cache_dir = os.environ.get('TIKTOKEN_CACHE_DIR', './models/tiktoken_cache_cache')
    cache_dir = os.path.abspath(cache_dir)
    
    # Check what encodings are cached
    cached_encodings = []
    if os.path.exists(cache_dir):
        for item in os.listdir(cache_dir):
            cached_encodings.append(item)
    
    return {
        'cache_dir': cache_dir,
        'cache_dir_exists': os.path.exists(cache_dir),
        'offline_mode': os.environ.get('TIKTOKEN_OFFLINE_MODE', 'true').lower() == 'true',
        'fallback_local': os.environ.get('TIKTOKEN_FALLBACK_LOCAL', 'true').lower() == 'true',
        'cached_files': cached_encodings,
        'cache_size_mb': sum(os.path.getsize(os.path.join(cache_dir, f)) 
                              for f in cached_encodings if os.path.isfile(os.path.join(cache_dir, f))) / (1024 * 1024) 
                        if os.path.exists(cache_dir) else 0,
    }


def init_tiktoken_with_retry(max_retries: int = 3, cache_dir: Optional[str] = None) -> bool:
    """
    Initialize tiktoken with retry logic for offline mode.
    
    Attempts to initialize tiktoken, with retries in case of transient errors.
    Useful for ensuring tiktoken is ready before guard scanners are initialized.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        cache_dir: Cache directory path (optional)
    
    Returns:
        bool: True if tiktoken was successfully initialized, False otherwise
    """
    setup_tiktoken_offline_mode(cache_dir)
    
    try:
        import tiktoken
    except ImportError:
        logger.warning('tiktoken is not installed')
        return False
    
    for attempt in range(max_retries):
        try:
            # Try to get a common encoding to test
            encoding = tiktoken.get_encoding('cl100k_base')
            logger.info('Tiktoken initialized successfully')
            return True
        except Exception as e:
            logger.warning(f'Tiktoken initialization attempt {attempt + 1}/{max_retries} failed: {e}')
            if attempt < max_retries - 1:
                import time
                time.sleep(1)  # Wait before retry
            continue
    
    logger.error(f'Failed to initialize tiktoken after {max_retries} attempts')
    return False
