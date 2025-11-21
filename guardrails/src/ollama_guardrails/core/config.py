import os
import yaml
from typing import Any, Dict, Optional, List
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


class Config:
    """A flexible configuration loader for the proxy.

    It retrieves settings with the following priority:
    1. Environment variables (e.g., `OLLAMA_URL`).
    2. Values from a YAML configuration file.
    3. Default values specified in the code.

    The `get` method is cached to ensure fast access to configuration values
    during runtime.
    """

    def __init__(self, config_file: Optional[str] = None):
        self._config_data: Dict[str, Any] = {}
        self._env_data: Dict[str, Any] = {}
        self._load(config_file)

    def _load(self, config_file: Optional[str] = None) -> None:
        """Load configurations from file and environment."""
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._config_data = yaml.safe_load(f) or {}
                logger.info(f"Successfully loaded configuration from {config_file}")
            except (IOError, yaml.YAMLError) as e:
                logger.error(f"Failed to load or parse config file {config_file}: {e}")
        
        # Store relevant environment variables
        self._env_data = {k: v for k, v in os.environ.items() if k.isupper()}

        logger.info('Configuration loaded. Access via get() method.')

    @lru_cache(maxsize=128)
    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a configuration value.

        Args:
            key: The configuration key (e.g., 'ollama_url').
            default: The default value to return if the key is not found.

        Returns:
            The configuration value.
        """
        env_key = key.upper()
        
        # 1. Check environment variables first
        if env_key in self._env_data:
            value = self._env_data[env_key]
            # Attempt to convert to the same type as the default
            if default is not None:
                return self._cast_to_default_type(value, default)
            return value

        # 2. Check YAML file data
        if key in self._config_data:
            return self._config_data[key]

        # 3. Return default
        return default

    def _cast_to_default_type(self, value: str, default: Any) -> Any:
        """Attempt to cast a string value to the type of the default value."""
        caster = type(default)
        try:
            if caster == bool:
                return str(value).lower() in ('1', 'true', 'yes', 'on')
            if caster == list:
                # Handle comma-separated lists from env vars
                return [item.strip() for item in value.split(',') if item.strip()]
            return caster(value)
        except (ValueError, TypeError):
            logger.warning(
                f"Could not cast env var value '{value}' to type {caster.__name__}. "
                f"Returning as string."
            )
            return value

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Helper to get a boolean value."""
        return self.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """Helper to get an integer value."""
        return self.get(key, default)

    def get_str(self, key: str, default: str = "") -> str:
        """Helper to get a string value."""
        return self.get(key, default)

    def get_list(self, key: str, default: Optional[List[str]] = None) -> List[str]:
        """Helper to get a list value."""
        # Don't pass mutable default to cached get() - it's unhashable
        result = self.get(key, None)
        if result is None:
            return default or []
        if isinstance(result, list):
            return result
        # If it's a string from env var, split it
        if isinstance(result, str):
            return [item.strip() for item in result.split(',') if item.strip()]
        return default or []

# Example of how the new Config class would be used in ollama_guard_proxy.py
# This is for demonstration and should not be run directly.
def _demonstrate_usage():
    # In the main application:
    # config = Config(os.environ.get('CONFIG_FILE'))
    # port = config.get_int('proxy_port', 8080)
    # is_enabled = config.get_bool('enable_input_guard', True)
    # whitelist = config.get_list('nginx_whitelist', [])
    pass
