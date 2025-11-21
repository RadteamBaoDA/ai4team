"""
Hugging Face offline mode configuration for local model caching.

This module configures Hugging Face transformers library to use local cache
directory instead of downloading models from the internet. This enables offline
operation and reduces network dependencies.

Environment Variables:
    HF_HOME: Hugging Face home directory (default: ~/.cache/huggingface)
    HF_OFFLINE: Enable offline mode (default: false, set by this module)
    HF_DATASETS_OFFLINE: Offline mode for datasets (default: false)
    HF_HUB_OFFLINE: Offline mode for hub (default: false)
    TRANSFORMERS_OFFLINE: Offline mode for transformers (default: false)
    TRANSFORMERS_CACHE: Transformers model cache directory
    HF_DATASETS_CACHE: Datasets cache directory
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def setup_huggingface_offline_mode(cache_dir: Optional[str] = None) -> bool:
    """
    Configure Hugging Face for offline mode using local cache directory.
    
    This function must be called BEFORE importing any huggingface_hub or
    transformers modules. It sets environment variables to ensure Hugging Face
    uses local files instead of attempting to download from the internet.
    
    Args:
        cache_dir: Optional path to Hugging Face cache directory.
                   If None, uses HF_HOME env var or default ~/.cache/huggingface
    
    Returns:
        bool: True if offline mode was successfully configured, False otherwise
    
    Example:
        >>> from ollama_guardrails.utils.huggingface_cache import setup_huggingface_offline_mode
        >>> setup_huggingface_offline_mode()
        >>> # Now safe to import transformers or huggingface_hub
        >>> from transformers import AutoTokenizer
    """
    try:
        # Determine cache directory
        if cache_dir is None:
            cache_dir = os.environ.get('HF_HOME')
            if not cache_dir:
                # Use custom path under models folder if available
                models_dir = os.path.abspath('./models/huggingface')
                cache_dir = models_dir
            else:
                cache_dir = os.path.abspath(cache_dir)
        else:
            cache_dir = os.path.abspath(cache_dir)
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        logger.info(f"Hugging Face cache directory: {cache_dir}")
        
        # Set Hugging Face environment variables
        os.environ['HF_HOME'] = cache_dir
        
        # Enable offline mode - prevents automatic downloads
        os.environ['HF_OFFLINE'] = 'true'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        os.environ['HF_DATASETS_OFFLINE'] = '1'
        os.environ['HF_HUB_OFFLINE'] = '1'
        
        # Set cache directories explicitly
        transformers_cache = os.path.join(cache_dir, 'transformers')
        datasets_cache = os.path.join(cache_dir, 'datasets')
        
        os.makedirs(transformers_cache, exist_ok=True)
        os.makedirs(datasets_cache, exist_ok=True)
        
        os.environ['TRANSFORMERS_CACHE'] = transformers_cache
        os.environ['HF_DATASETS_CACHE'] = datasets_cache
        
        logger.info('Hugging Face offline mode configured successfully')
        logger.info(f'  HF_HOME: {cache_dir}')
        logger.info(f'  TRANSFORMERS_CACHE: {transformers_cache}')
        logger.info(f'  HF_DATASETS_CACHE: {datasets_cache}')
        logger.info(f'  Offline mode: {os.environ.get("HF_OFFLINE")}')
        
        return True
        
    except Exception as e:
        logger.error(f'Failed to configure Hugging Face offline mode: {e}')
        return False


def ensure_huggingface_cache_dir(base_path: str = './models') -> Dict[str, str]:
    """
    Ensure Hugging Face cache directories exist and return their paths.
    
    Args:
        base_path: Base path for models directory (default: './models')
    
    Returns:
        dict: Dictionary with 'hf_home', 'transformers', and 'datasets' paths
    """
    base_path = os.path.abspath(base_path)
    hf_home = os.path.join(base_path, 'huggingface')
    transformers_cache = os.path.join(hf_home, 'transformers')
    datasets_cache = os.path.join(hf_home, 'datasets')
    
    for directory in [hf_home, transformers_cache, datasets_cache]:
        os.makedirs(directory, exist_ok=True)
    
    return {
        'hf_home': hf_home,
        'transformers': transformers_cache,
        'datasets': datasets_cache,
    }


def get_huggingface_cache_info() -> Dict[str, Any]:
    """
    Get information about Hugging Face cache configuration.
    
    Returns:
        dict: Information about Hugging Face cache setup
    """
    hf_home = os.environ.get('HF_HOME', os.path.expanduser('~/.cache/huggingface'))
    hf_home = os.path.abspath(hf_home)
    
    transformers_cache = os.environ.get('TRANSFORMERS_CACHE', os.path.join(hf_home, 'transformers'))
    datasets_cache = os.environ.get('HF_DATASETS_CACHE', os.path.join(hf_home, 'datasets'))
    
    # Calculate cache sizes
    def get_dir_size(path):
        if not os.path.exists(path):
            return 0
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total += os.path.getsize(filepath)
        return total
    
    # Get model files
    def get_model_files(path):
        if not os.path.exists(path):
            return []
        files = []
        for root, dirs, filenames in os.walk(path):
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), path)
                files.append(rel_path)
        return files
    
    return {
        'hf_home': hf_home,
        'hf_home_exists': os.path.exists(hf_home),
        'transformers_cache': transformers_cache,
        'transformers_exists': os.path.exists(transformers_cache),
        'datasets_cache': datasets_cache,
        'datasets_exists': os.path.exists(datasets_cache),
        'offline_mode': os.environ.get('HF_OFFLINE', '').lower() == 'true',
        'transformers_offline': os.environ.get('TRANSFORMERS_OFFLINE', '').lower() in ('1', 'true'),
        'datasets_offline': os.environ.get('HF_DATASETS_OFFLINE', '').lower() in ('1', 'true'),
        'hf_home_size_mb': get_dir_size(hf_home) / (1024 * 1024),
        'transformers_files': len(get_model_files(transformers_cache)),
        'datasets_files': len(get_model_files(datasets_cache)),
    }


def download_huggingface_model(model_id: str, cache_dir: Optional[str] = None) -> bool:
    """
    Download a specific Hugging Face model locally.
    
    This requires online access at the time of download. After downloading,
    the model can be used offline.
    
    Args:
        model_id: Hugging Face model ID (e.g., 'bert-base-uncased')
        cache_dir: Cache directory (default: from HF_HOME env var)
    
    Returns:
        bool: True if model was successfully cached, False otherwise
    
    Example:
        >>> from ollama_guardrails.utils.huggingface_cache import download_huggingface_model
        >>> download_huggingface_model('sentence-transformers/all-mpnet-base-v2', './models/huggingface')
    """
    try:
        # Setup offline mode first
        setup_huggingface_offline_mode(cache_dir)
        
        # Import transformers after environment setup
        try:
            from transformers import AutoModel, AutoTokenizer
        except ImportError:
            logger.error('transformers library is not installed. Install with: pip install transformers')
            return False
        
        logger.info(f'Downloading Hugging Face model: {model_id}')
        
        # Download tokenizer
        try:
            logger.info(f'  Downloading tokenizer for {model_id}...')
            AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
            logger.info(f'  ✓ Tokenizer downloaded')
        except Exception as e:
            logger.warning(f'  Could not download tokenizer: {e}')
        
        # Download model
        try:
            logger.info(f'  Downloading model for {model_id}...')
            AutoModel.from_pretrained(model_id, trust_remote_code=True)
            logger.info(f'  ✓ Model downloaded')
        except Exception as e:
            logger.warning(f'  Could not download model: {e}')
        
        logger.info(f'Successfully cached model: {model_id}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to download Hugging Face model {model_id}: {e}')
        return False


def init_huggingface_with_retry(max_retries: int = 3, cache_dir: Optional[str] = None) -> bool:
    """
    Initialize Hugging Face with retry logic for offline mode.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        cache_dir: Cache directory path (optional)
    
    Returns:
        bool: True if Hugging Face was successfully initialized, False otherwise
    """
    setup_huggingface_offline_mode(cache_dir)
    
    try:
        import transformers
        logger.debug('transformers module detected (version: %s)', getattr(transformers, '__version__', 'unknown'))
    except ImportError:
        logger.warning('transformers library is not installed')
        return False
    
    for attempt in range(max_retries):
        try:
            logger.info('Hugging Face initialized successfully')
            return True
        except Exception as e:
            logger.warning(f'Hugging Face initialization attempt {attempt + 1}/{max_retries} failed: {e}')
            if attempt < max_retries - 1:
                import time
                time.sleep(1)  # Wait before retry
            continue
    
    logger.error(f'Failed to initialize Hugging Face after {max_retries} attempts')
    return False
