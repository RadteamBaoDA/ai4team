import os
import yaml
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Simple configuration loader used by the proxy.

    Prefers environment variables, then YAML file values, then defaults.
    """

    def __init__(self, config_file: Optional[str] = None):
        self._raw: Dict[str, Any] = {}
        self._load(config_file)

    def _load(self, config_file: Optional[str] = None) -> None:
        data = {}
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}

        def env_or(key: str, default: Any):
            return os.environ.get(key, data.get(key, default))

        self._raw['ollama_url'] = env_or('OLLAMA_URL', 'http://127.0.0.1:11434')
        self._raw['ollama_path'] = env_or('OLLAMA_PATH', '/api/generate')
        self._raw['proxy_port'] = int(env_or('PROXY_PORT', data.get('proxy_port', 8080)))
        self._raw['proxy_host'] = env_or('PROXY_HOST', data.get('proxy_host', '0.0.0.0'))

        def bool_env(key: str, default: bool) -> bool:
            val = os.environ.get(key)
            if val is None:
                return bool(data.get(key, default))
            return str(val).lower() in ('1', 'true', 'yes', 'on')

        self._raw['enable_input_guard'] = bool_env('ENABLE_INPUT_GUARD', True)
        self._raw['enable_output_guard'] = bool_env('ENABLE_OUTPUT_GUARD', True)
        self._raw['block_on_guard_error'] = bool_env('BLOCK_ON_GUARD_ERROR', False)
        
        # Local models configuration
        self._raw['use_local_models'] = bool_env('LLM_GUARD_USE_LOCAL_MODELS', False)
        self._raw['models_path'] = env_or('LLM_GUARD_MODELS_PATH', data.get('models_path', './models'))

        nginx_env = os.environ.get('NGINX_WHITELIST')
        if nginx_env:
            self._raw['nginx_whitelist'] = [ip.strip() for ip in nginx_env.split(',') if ip.strip()]
        else:
            self._raw['nginx_whitelist'] = data.get('nginx_whitelist', []) or []

        logger.info('Configuration loaded')

    def get(self, key: str, default: Any = None) -> Any:
        return self._raw.get(key, default)
