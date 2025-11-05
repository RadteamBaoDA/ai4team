"""Device configuration utilities for forcing CPU usage in transformers and llm-guard.

This module provides utilities to configure compute device usage for ML inference,
with options to force CPU-only operation or enable GPU acceleration.

Usage:
    # Force CPU mode (recommended for production)
    from ollama_guardrails.utils.device_config import force_cpu_mode
    force_cpu_mode()  # Call BEFORE any ML library imports
    
    # Check configuration
    from ollama_guardrails.utils.device_config import get_device_config
    config = get_device_config()
"""

import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def force_cpu_mode(verbose: bool = True) -> None:
    """
    Force transformers and llm-guard to use CPU exclusively.
    
    This function must be called BEFORE importing any ML libraries.
    It sets environment variables to disable GPU acceleration and ensure
    all ML operations use CPU.
    
    Args:
        verbose: If True, log detailed configuration information
    
    Example:
        >>> from ollama_guardrails.utils.device_config import force_cpu_mode
        >>> force_cpu_mode()
        >>> from ollama_guardrails.guards.guard_manager import LLMGuardManager
        >>> manager = LLMGuardManager()
    """
    # LLM Guard explicit device setting
    os.environ.setdefault('LLM_GUARD_DEVICE', 'cpu')
    
    # Disable CUDA GPUs (critical - prevents torch from using GPU)
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    
    # Force synchronous CUDA operations (even if somehow enabled)
    os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
    
    # Disable Flash Attention optimization (may not work on CPU)
    os.environ['DISABLE_FLASH_ATTENTION'] = '1'
    
    # PyTorch explicit CPU device
    if 'TORCH_DEVICE' not in os.environ:
        os.environ['TORCH_DEVICE'] = 'cpu'
    
    if verbose:
        logger.info(
            'CPU-only mode enabled for transformers and llm-guard:\n'
            f'  ✓ LLM_GUARD_DEVICE: {os.environ.get("LLM_GUARD_DEVICE")}\n'
            f'  ✓ CUDA_VISIBLE_DEVICES: "" (empty - no GPU access)\n'
            f'  ✓ CUDA_LAUNCH_BLOCKING: {os.environ.get("CUDA_LAUNCH_BLOCKING")}\n'
            f'  ✓ DISABLE_FLASH_ATTENTION: {os.environ.get("DISABLE_FLASH_ATTENTION")}\n'
            f'  ✓ TORCH_DEVICE: {os.environ.get("TORCH_DEVICE")}'
        )


def force_gpu_mode(device: str = 'mps', verbose: bool = True) -> None:
    """
    Force transformers and llm-guard to use GPU acceleration.
    
    Currently only supports Apple Silicon (MPS). CUDA support removed for Python 3.12 compatibility.
    
    Args:
        device: GPU device type ('mps' for Apple Silicon M1/M2/M3)
        verbose: If True, log configuration information
    
    Raises:
        ValueError: If device is not 'mps'
    
    Example:
        >>> from ollama_guardrails.utils.device_config import force_gpu_mode
        >>> force_gpu_mode('mps')  # For Apple Silicon
    """
    if device not in ('mps', 'cpu'):
        raise ValueError(f'Unsupported device: {device}. Only "mps" (Apple Silicon) and "cpu" supported.')
    
    os.environ['LLM_GUARD_DEVICE'] = device
    
    # Remove CUDA restrictions
    if 'CUDA_VISIBLE_DEVICES' in os.environ:
        del os.environ['CUDA_VISIBLE_DEVICES']
    
    if verbose:
        logger.info(f'GPU mode enabled: {device} (Apple Silicon)')


def auto_device_mode(verbose: bool = True) -> None:
    """
    Enable automatic device detection (default llm-guard behavior).
    
    The system will automatically detect and use the best available device:
    - Apple Silicon (arm64/Darwin): MPS GPU acceleration
    - Other systems: CPU
    
    Args:
        verbose: If True, log configuration information
    
    Example:
        >>> from ollama_guardrails.utils.device_config import auto_device_mode
        >>> auto_device_mode()
    """
    # Remove explicit device override to allow auto-detection
    if 'LLM_GUARD_DEVICE' in os.environ:
        del os.environ['LLM_GUARD_DEVICE']
    
    if verbose:
        logger.info('Device auto-detection enabled - system will choose best available device')


def get_device_config() -> Dict[str, str]:
    """
    Get current device configuration as a dictionary.
    
    Returns:
        Dictionary with current device settings
    
    Example:
        >>> from ollama_guardrails.utils.device_config import get_device_config
        >>> config = get_device_config()
        >>> for key, value in config.items():
        ...     print(f'{key}: {value}')
    """
    return {
        'LLM_GUARD_DEVICE': os.environ.get('LLM_GUARD_DEVICE', '(auto-detected)'),
        'CUDA_VISIBLE_DEVICES': os.environ.get('CUDA_VISIBLE_DEVICES', '(system default)'),
        'CUDA_LAUNCH_BLOCKING': os.environ.get('CUDA_LAUNCH_BLOCKING', '(system default)'),
        'DISABLE_FLASH_ATTENTION': os.environ.get('DISABLE_FLASH_ATTENTION', '(enabled by default)'),
        'TORCH_DEVICE': os.environ.get('TORCH_DEVICE', '(auto)'),
    }


def print_device_config() -> None:
    """
    Print current device configuration to console.
    
    Example:
        >>> from ollama_guardrails.utils.device_config import print_device_config
        >>> print_device_config()
    """
    print('\n' + '='*60)
    print('Device Configuration')
    print('='*60)
    config = get_device_config()
    for key, value in config.items():
        print(f'{key:.<40} {value}')
    print('='*60 + '\n')


def is_cpu_only_mode() -> bool:
    """
    Check if CPU-only mode is enabled.
    
    Returns:
        True if CPU-only mode is active, False otherwise
    
    Example:
        >>> from ollama_guardrails.utils.device_config import is_cpu_only_mode
        >>> if is_cpu_only_mode():
        ...     print('CPU-only mode active')
    """
    cuda_disabled = os.environ.get('CUDA_VISIBLE_DEVICES', '') == ''
    llm_guard_cpu = os.environ.get('LLM_GUARD_DEVICE', '').lower() == 'cpu'
    torch_cpu = os.environ.get('TORCH_DEVICE', '').lower() == 'cpu'
    
    return cuda_disabled or llm_guard_cpu or torch_cpu


def is_gpu_mode() -> bool:
    """
    Check if GPU mode is enabled.
    
    Returns:
        True if GPU mode is configured (currently only 'mps'), False otherwise
    
    Example:
        >>> from ollama_guardrails.utils.device_config import is_gpu_mode
        >>> if is_gpu_mode():
        ...     print('GPU mode active')
    """
    device = os.environ.get('LLM_GUARD_DEVICE', '').lower()
    return device in ('mps', 'cuda', 'gpu')


def setup_transformers_cpu() -> None:
    """
    Additional configuration specifically for Hugging Face transformers.
    
    This is called automatically by force_cpu_mode() but can be called
    separately if needed.
    
    Disables:
    - Flash Attention (causes issues on CPU)
    - SDPA attention (falls back to standard attention)
    
    Example:
        >>> from ollama_guardrails.utils.device_config import setup_transformers_cpu
        >>> setup_transformers_cpu()
    """
    # Disable Flash Attention
    os.environ['DISABLE_FLASH_ATTENTION'] = '1'
    
    # Additional transformers configuration
    os.environ.setdefault('TRANSFORMERS_NO_ADVISORY_WARNINGS', '1')
    
    logger.debug('Transformers CPU configuration applied')


def get_recommended_config() -> Dict[str, str]:
    """
    Get recommended environment variable configuration.
    
    Returns:
        Dictionary of recommended CPU-only settings
    
    Example:
        >>> from ollama_guardrails.utils.device_config import get_recommended_config
        >>> config = get_recommended_config()
        >>> for key, value in config.items():
        ...     print(f'export {key}="{value}"')
    """
    return {
        'LLM_GUARD_DEVICE': 'cpu',
        'CUDA_VISIBLE_DEVICES': '',
        'CUDA_LAUNCH_BLOCKING': '1',
        'DISABLE_FLASH_ATTENTION': '1',
        'TORCH_DEVICE': 'cpu',
        'TRANSFORMERS_NO_ADVISORY_WARNINGS': '1',
    }


# Auto-initialize CPU mode if environment variable is set
if os.environ.get('LLM_GUARD_FORCE_CPU', '').lower() in ('1', 'true', 'yes', 'on'):
    force_cpu_mode(verbose=True)
