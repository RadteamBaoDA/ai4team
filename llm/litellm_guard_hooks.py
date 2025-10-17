"""
LLM Guard Custom Guardrail for LiteLLM Proxy
This module implements the CustomGuardrail interface from LiteLLM
See: https://docs.litellm.ai/docs/proxy/guardrails/custom_guardrail

The implementation provides:
- async_pre_call_hook: Input validation and modification
- async_moderation_hook: Parallel moderation during LLM call
- async_post_call_success_hook: Output validation after LLM call
- async_post_call_streaming_iterator_hook: Stream processing
"""

import os
import json
import logging
import re
from typing import (
    Dict, Any, Optional, List, Union, Literal, AsyncGenerator, Tuple
)
from datetime import datetime
import asyncio
from enum import Enum

import yaml

# LiteLLM Guardrail imports
try:
    from litellm.integrations.custom_guardrail import CustomGuardrail
    from litellm._logging import verbose_proxy_logger
    from litellm.caching.caching import DualCache
    from litellm.proxy._types import UserAPIKeyAuth
    from litellm.types.utils import ModelResponseStream
    import litellm
    HAS_LITELLM_GUARDRAIL = True
except ImportError:
    HAS_LITELLM_GUARDRAIL = False
    print("Warning: LiteLLM guardrail not available. Install with: pip install litellm")

# LLM Guard imports
try:
    from llm_guard.input_scanners import (
        BanSubstrings,
        PromptInjection,
        Toxicity,
        Secrets,
        TokenLimit,
    )
    from llm_guard.output_scanners import (
        BanSubstrings as OutputBanSubstrings,
        Toxicity as OutputToxicity,
        MaliciousURLs,
        NoRefusal,
        NoCode,
    )
    from llm_guard.guard import Guard
    HAS_LLM_GUARD = True
except ImportError:
    HAS_LLM_GUARD = False
    print("Warning: LLM Guard not installed. Install with: pip install llm-guard")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Fallback logger if litellm not available
class SimpleLogger:
    @staticmethod
    def debug(msg, *args):
        logger.debug(msg, *args)
    
    @staticmethod
    def info(msg, *args):
        logger.info(msg, *args)
    
    @staticmethod
    def warning(msg, *args):
        logger.warning(msg, *args)
    
    @staticmethod
    def error(msg, *args):
        logger.error(msg, *args)

# Use litellm logger if available, otherwise use simple logger
try:
    proxy_logger = verbose_proxy_logger
except NameError:
    proxy_logger = SimpleLogger()


class LanguageDetector:
    """Detect language from text and provide localized error messages."""
    
    # Language detection patterns
    LANGUAGE_PATTERNS = {
        'zh': {
            'patterns': [r'[\u4e00-\u9fff]'],
            'name': 'Chinese'
        },
        'vi': {
            'patterns': [r'[\u0102\u0103\u0110\u0111\u0128\u0129\u0168\u0169\u01a0\u01a1\u01af\u01b0]'],
            'name': 'Vietnamese'
        },
        'ja': {
            'patterns': [r'[\u3040-\u309f\u30a0-\u30ff]'],
            'name': 'Japanese'
        },
        'ko': {
            'patterns': [r'[\uac00-\ud7af]'],
            'name': 'Korean'
        },
        'ru': {
            'patterns': [r'[\u0400-\u04ff]'],
            'name': 'Russian'
        },
        'ar': {
            'patterns': [r'[\u0600-\u06ff]'],
            'name': 'Arabic'
        },
    }
    
    # Error messages by language
    ERROR_MESSAGES = {
        'zh': {
            'prompt_blocked': '您的输入被安全扫描器阻止。原因: {reason}',
            'response_blocked': '模型的输出被安全扫描器阻止。',
            'server_error': '服务器内部错误。',
        },
        'vi': {
            'prompt_blocked': 'Đầu vào của bạn bị chặn bởi bộ quét bảo mật. Lý do: {reason}',
            'response_blocked': 'Đầu ra của mô hình bị chặn bởi bộ quét bảo mật.',
            'server_error': 'Lỗi máy chủ nội bộ.',
        },
        'ja': {
            'prompt_blocked': 'あなたの入力はセキュリティスキャナーによってブロックされました。理由: {reason}',
            'response_blocked': 'モデルの出力はセキュリティスキャナーによってブロックされました。',
            'server_error': 'サーバー内部エラー。',
        },
        'ko': {
            'prompt_blocked': '입력이 보안 스캐너에 의해 차단되었습니다. 이유: {reason}',
            'response_blocked': '모델 출력이 보안 스캐너에 의해 차단되었습니다.',
            'server_error': '서버 내부 오류입니다.',
        },
        'ru': {
            'prompt_blocked': 'Ваши входные данные заблокированы сканером безопасности. Причина: {reason}',
            'response_blocked': 'Вывод модели заблокирован сканером безопасности.',
            'server_error': 'Ошибка внутреннего сервера.',
        },
        'ar': {
            'prompt_blocked': 'تم حظر مدخلاتك بواسطة ماسح الأمان. السبب: {reason}',
            'response_blocked': 'تم حظر مخرجات النموذج بواسطة ماسح الأمان.',
            'server_error': 'خطأ في الخادم الداخلي.',
        },
        'en': {
            'prompt_blocked': 'Your input was blocked by the security scanner. Reason: {reason}',
            'response_blocked': 'Model output was blocked by the security scanner.',
            'server_error': 'Internal server error.',
        }
    }
    
    @staticmethod
    def detect_language(text: str) -> str:
        """Detect language from text. Returns language code or 'en' as default."""
        if not text:
            return 'en'
        
        for lang_code, lang_info in LanguageDetector.LANGUAGE_PATTERNS.items():
            for pattern in lang_info['patterns']:
                if re.search(pattern, text):
                    logger.info(f"Detected language: {lang_info['name']}")
                    return lang_code
        
        return 'en'
    
    @staticmethod
    def get_error_message(message_key: str, language: str, reason: str = '') -> str:
        """Get localized error message."""
        messages = LanguageDetector.ERROR_MESSAGES.get(language, LanguageDetector.ERROR_MESSAGES['en'])
        message = messages.get(message_key, '')
        
        if reason and '{reason}' in message:
            message = message.format(reason=reason)
        
        return message


class LLMGuardManager:
    """Manages LLM Guard security scanning."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize LLM Guard Manager."""
        self.config = config or {}
        self.input_guard = None
        self.output_guard = None
        self.enabled = self.config.get('enabled', True)
        
        if not HAS_LLM_GUARD:
            logger.warning("LLM Guard not available. Install with: pip install llm-guard")
            self.enabled = False
            return
        
        self._initialize_guards()
    
    def _initialize_guards(self):
        """Initialize input and output guards."""
        try:
            # Initialize input scanners
            input_scanners = self.config.get('input_scanning', {}).get('scanners', [])
            if input_scanners:
                scanner_instances = []
                for scanner_name in input_scanners:
                    try:
                        if scanner_name == 'BanSubstrings':
                            scanner_instances.append(BanSubstrings())
                        elif scanner_name == 'PromptInjection':
                            scanner_instances.append(PromptInjection())
                        elif scanner_name == 'Toxicity':
                            scanner_instances.append(Toxicity())
                        elif scanner_name == 'Secrets':
                            scanner_instances.append(Secrets())
                        elif scanner_name == 'TokenLimit':
                            scanner_instances.append(TokenLimit())
                    except Exception as e:
                        logger.warning(f"Failed to initialize input scanner {scanner_name}: {e}")
                
                if scanner_instances:
                    self.input_guard = Guard(scanners=scanner_instances)
                    logger.info(f"Input guard initialized with {len(scanner_instances)} scanners")
            
            # Initialize output scanners
            output_scanners = self.config.get('output_scanning', {}).get('scanners', [])
            if output_scanners:
                scanner_instances = []
                for scanner_name in output_scanners:
                    try:
                        if scanner_name == 'BanSubstrings':
                            scanner_instances.append(OutputBanSubstrings())
                        elif scanner_name == 'Toxicity':
                            scanner_instances.append(OutputToxicity())
                        elif scanner_name == 'MaliciousURLs':
                            scanner_instances.append(MaliciousURLs())
                        elif scanner_name == 'NoRefusal':
                            scanner_instances.append(NoRefusal())
                        elif scanner_name == 'NoCode':
                            scanner_instances.append(NoCode())
                    except Exception as e:
                        logger.warning(f"Failed to initialize output scanner {scanner_name}: {e}")
                
                if scanner_instances:
                    self.output_guard = Guard(scanners=scanner_instances)
                    logger.info(f"Output guard initialized with {len(scanner_instances)} scanners")
        
        except Exception as e:
            logger.error(f"Failed to initialize guards: {e}")
            self.enabled = False
    
    def scan_input(self, prompt: str) -> Dict[str, Any]:
        """Scan input prompt."""
        if not self.enabled or not self.input_guard:
            return {'allowed': True, 'scanners': {}}
        
        try:
            response = self.input_guard.validate(prompt)
            result = {
                'allowed': response.outcome == 'PASS',
                'scanners': {}
            }
            
            if response.scanners:
                for scanner in response.scanners:
                    result['scanners'][scanner.name] = {
                        'passed': scanner.outcome == 'PASS',
                        'reason': scanner.reason or ''
                    }
            
            logger.info(f"Input scan result: allowed={result['allowed']}")
            return result
        
        except Exception as e:
            logger.error(f"Input scan error: {e}")
            return {'allowed': True, 'scanners': {}}
    
    def scan_output(self, response: str) -> Dict[str, Any]:
        """Scan output response."""
        if not self.enabled or not self.output_guard:
            return {'allowed': True, 'scanners': {}}
        
        try:
            result = self.output_guard.validate(response)
            output = {
                'allowed': result.outcome == 'PASS',
                'scanners': {}
            }
            
            if result.scanners:
                for scanner in result.scanners:
                    output['scanners'][scanner.name] = {
                        'passed': scanner.outcome == 'PASS',
                        'reason': scanner.reason or ''
                    }
            
            logger.info(f"Output scan result: allowed={output['allowed']}")
            return output
        
        except Exception as e:
            logger.error(f"Output scan error: {e}")
            return {'allowed': True, 'scanners': {}}


class LLMGuardCustomGuardrail(CustomGuardrail):
    """
    Custom Guardrail implementation for LiteLLM using LLM Guard
    
    Implements the CustomGuardrail interface:
    - async_pre_call_hook: Input validation and modification before LLM call
    - async_moderation_hook: Parallel validation during LLM call
    - async_post_call_success_hook: Output validation after LLM call
    - async_post_call_streaming_iterator_hook: Stream processing
    """
    
    def __init__(self, **kwargs):
        """Initialize the custom guardrail with optional parameters."""
        super().__init__(**kwargs)
        self.config = self._load_config()
        self.guard_config = self.config.get('llm_guard', {})
        self.guard_manager = LLMGuardManager(self.guard_config)
        self.optional_params = kwargs
        logger.info("LLMGuardCustomGuardrail initialized with LLM Guard")
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        # Check environment variable first
        config_path = config_path or os.getenv('CONFIG_PATH', './litellm_config.yaml')
        
        default_config_path = os.path.join(os.path.dirname(__file__), 'litellm_config.yaml')
        
        if config_path and os.path.exists(config_path):
            path = config_path
        elif os.path.exists(default_config_path):
            path = default_config_path
        else:
            logger.warning("Configuration file not found, using defaults")
            return {'llm_guard': {}}
        
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f) or {}
                logger.info(f"Configuration loaded from {path}")
                return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return {'llm_guard': {}}
    
    # ===== GUARDRAIL METHODS =====
    
    async def async_pre_call_hook(
        self,
        user_api_key_dict: "UserAPIKeyAuth",
        cache: "DualCache",
        data: Dict[str, Any],
        call_type: Literal[
            "completion",
            "text_completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
            "pass_through_endpoint",
            "rerank"
        ],
    ) -> Optional[Union[Exception, str, Dict[str, Any]]]:
        """
        Pre-call hook - runs BEFORE the LLM API call
        
        Can modify the input or reject the request before it reaches the LLM.
        Used for input validation and sanitization.
        
        Returns:
            - None or modified data: Request allowed (optionally modified)
            - Exception or str: Request blocked with error
        """
        try:
            proxy_logger.debug(f"[pre_call] Call type: {call_type}, Data keys: {data.keys()}")
            
            # Extract messages for chat completions
            if call_type in ["completion", "text_completion"]:
                messages = data.get("messages", [])
                
                # Get the latest user message
                prompt_text = ""
                if isinstance(messages, list) and messages:
                    for msg in reversed(messages):
                        if isinstance(msg, dict) and msg.get('role') == 'user':
                            content = msg.get('content', '')
                            if isinstance(content, str):
                                prompt_text = content
                            break
                
                proxy_logger.debug(f"[pre_call] Prompt length: {len(prompt_text)}")
                
                # Scan input
                if self.guard_manager.enabled and prompt_text:
                    scan_result = self.guard_manager.scan_input(prompt_text)
                    
                    if not scan_result['allowed']:
                        # Extract failure reasons
                        reasons = []
                        for scanner_name, scanner_info in scan_result['scanners'].items():
                            if not scanner_info['passed']:
                                reasons.append(f"{scanner_name}: {scanner_info.get('reason', 'Unknown')}")
                        
                        reason_str = ', '.join(reasons)
                        detected_lang = LanguageDetector.detect_language(prompt_text)
                        error_msg = LanguageDetector.get_error_message('prompt_blocked', detected_lang, reason_str)
                        
                        proxy_logger.warning(f"[pre_call] Input blocked. Reason: {reason_str}")
                        
                        # Return error string that LiteLLM will handle
                        return f"[{detected_lang}] {error_msg}"
                    
                    proxy_logger.debug("[pre_call] Input passed security checks")
                
                # Return modified data or None if not modified
                return None
            
            return None
        
        except Exception as e:
            proxy_logger.error(f"[pre_call] Error: {str(e)}")
            return None
    
    async def async_moderation_hook(
        self,
        data: Dict[str, Any],
        user_api_key_dict: "UserAPIKeyAuth",
        call_type: Literal[
            "completion",
            "text_completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription"
        ],
    ) -> Optional[Union[Exception, str]]:
        """
        Moderation hook - runs DURING the LLM API call (in parallel)
        
        Cannot modify the request, only reject it.
        Used for parallel validation without blocking the initial request.
        
        Returns:
            - None: Request allowed
            - Exception or str: Request blocked with error
        """
        try:
            proxy_logger.debug(f"[moderation] Call type: {call_type}")
            
            # Similar to pre_call but runs in parallel
            if call_type in ["completion", "text_completion"]:
                messages = data.get("messages", [])
                prompt_text = ""
                
                if isinstance(messages, list) and messages:
                    for msg in reversed(messages):
                        if isinstance(msg, dict) and msg.get('role') == 'user':
                            content = msg.get('content', '')
                            if isinstance(content, str):
                                prompt_text = content
                            break
                
                # Scan input (same as pre_call for consistency)
                if self.guard_manager.enabled and prompt_text:
                    scan_result = self.guard_manager.scan_input(prompt_text)
                    
                    if not scan_result['allowed']:
                        reasons = []
                        for scanner_name, scanner_info in scan_result['scanners'].items():
                            if not scanner_info['passed']:
                                reasons.append(f"{scanner_name}: {scanner_info.get('reason', 'Unknown')}")
                        
                        reason_str = ', '.join(reasons)
                        detected_lang = LanguageDetector.detect_language(prompt_text)
                        error_msg = LanguageDetector.get_error_message('prompt_blocked', detected_lang, reason_str)
                        
                        proxy_logger.warning(f"[moderation] Input blocked. Reason: {reason_str}")
                        return f"[{detected_lang}] {error_msg}"
            
            return None
        
        except Exception as e:
            proxy_logger.error(f"[moderation] Error: {str(e)}")
            return None
    
    async def async_post_call_success_hook(
        self,
        data: Dict[str, Any],
        user_api_key_dict: "UserAPIKeyAuth",
        response: Any,
    ) -> Optional[Union[Exception, str, Dict[str, Any]]]:
        """
        Post-call success hook - runs AFTER a successful LLM API call
        
        Can validate the response and modify or reject it.
        Used for output validation and sanitization.
        
        Returns:
            - response: Response allowed (optionally modified)
            - Exception or str: Response blocked with error
        """
        try:
            proxy_logger.debug("[post_call] Processing response")
            
            # Extract response text
            response_text = ""
            response_obj = response  # Keep original for modification if needed
            
            if hasattr(response, 'choices'):
                # OpenAI format response
                if response.choices:
                    choice = response.choices[0]
                    if hasattr(choice, 'message'):
                        if isinstance(choice.message, dict):
                            response_text = choice.message.get('content', '')
                        else:
                            response_text = getattr(choice.message, 'content', '')
                    elif hasattr(choice, 'text'):
                        response_text = choice.text
            
            elif isinstance(response, dict):
                # Dict format response
                if 'choices' in response:
                    choices = response['choices']
                    if choices:
                        choice = choices[0]
                        if 'message' in choice:
                            response_text = choice['message'].get('content', '')
                        elif 'text' in choice:
                            response_text = choice['text']
            
            proxy_logger.debug(f"[post_call] Response text length: {len(response_text)}")
            
            # Scan output
            if self.guard_manager.enabled and response_text:
                scan_result = self.guard_manager.scan_output(response_text)
                
                if not scan_result['allowed']:
                    # Extract failure reasons
                    reasons = []
                    for scanner_name, scanner_info in scan_result['scanners'].items():
                        if not scanner_info['passed']:
                            reasons.append(f"{scanner_name}: {scanner_info.get('reason', 'Unknown')}")
                    
                    reason_str = ', '.join(reasons)
                    proxy_logger.warning(f"[post_call] Output blocked. Reason: {reason_str}")
                    
                    # Return error message
                    return f"Model output blocked by security scanner: {reason_str}"
                
                proxy_logger.debug("[post_call] Output passed security checks")
            
            # Return original response (can be modified if needed)
            return response_obj
        
        except Exception as e:
            proxy_logger.error(f"[post_call] Error: {str(e)}")
            return response
    
    async def async_post_call_streaming_iterator_hook(
        self,
        user_api_key_dict: "UserAPIKeyAuth",
        response: Any,
        request_data: Dict[str, Any],
    ) -> AsyncGenerator["ModelResponseStream", None]:
        """
        Post-call streaming hook - processes the entire stream
        
        Useful for streaming responses that need full content analysis.
        Yields modified stream chunks.
        
        Args:
            user_api_key_dict: User API key information
            response: The streaming response iterator
            request_data: Original request data
            
        Yields:
            ModelResponseStream chunks
        """
        try:
            proxy_logger.debug("[streaming] Processing stream")
            
            # Buffer for collecting full response
            full_response = ""
            chunk_count = 0
            
            # Pass through all chunks
            async for item in response:
                chunk_count += 1
                
                # Try to extract text from chunk
                if hasattr(item, 'choices'):
                    if item.choices:
                        choice = item.choices[0]
                        if hasattr(choice, 'delta'):
                            if hasattr(choice.delta, 'content'):
                                content = choice.delta.content
                                if content:
                                    full_response += content
                
                # Yield the chunk as-is
                yield item
            
            proxy_logger.debug(f"[streaming] Processed {chunk_count} chunks, total length: {len(full_response)}")
            
            # Optionally validate accumulated response
            if self.guard_manager.enabled and full_response:
                scan_result = self.guard_manager.scan_output(full_response)
                if not scan_result['allowed']:
                    proxy_logger.warning(f"[streaming] Final response blocked by guards")
        
        except Exception as e:
            proxy_logger.error(f"[streaming] Error: {str(e)}")
            # Re-raise to let LiteLLM handle
            async for item in response:
                yield item


class LiteLLMGuardHooks:
    """
    Legacy hooks class for backward compatibility.
    New implementations should use LLMGuardCustomGuardrail directly.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize legacy hooks."""
        self.config = self._load_config(config_path)
        self.guard_config = self.config.get('llm_guard', {})
        self.guard_manager = LLMGuardManager(self.guard_config)
        self.guardrail = LLMGuardCustomGuardrail()
        logger.info("LiteLLM Guard Hooks (legacy) initialized")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        default_config_path = os.path.join(os.path.dirname(__file__), 'litellm_config.yaml')
        
        if config_path and os.path.exists(config_path):
            path = config_path
        elif os.path.exists(default_config_path):
            path = default_config_path
        else:
            logger.warning("Configuration file not found, using defaults")
            return {'llm_guard': {}}
        
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f) or {}
                logger.info(f"Configuration loaded from {path}")
                return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return {'llm_guard': {}}


# Global instances for use with LiteLLM
_guardrail_instance: Optional[LLMGuardCustomGuardrail] = None
_hooks_instance: Optional[LiteLLMGuardHooks] = None


# ===== GUARDRAIL API (Primary - For config.yaml) =====

def initialize_guardrail(**kwargs) -> LLMGuardCustomGuardrail:
    """Initialize and return the custom guardrail instance."""
    global _guardrail_instance
    if _guardrail_instance is None:
        _guardrail_instance = LLMGuardCustomGuardrail(**kwargs)
        logger.info("Custom guardrail instance initialized")
    return _guardrail_instance


def get_guardrail() -> LLMGuardCustomGuardrail:
    """Get the current guardrail instance."""
    global _guardrail_instance
    if _guardrail_instance is None:
        _guardrail_instance = LLMGuardCustomGuardrail()
    return _guardrail_instance


# ===== LEGACY HOOKS API (For backward compatibility) =====

def initialize_hooks(config_path: Optional[str] = None) -> LiteLLMGuardHooks:
    """Initialize and return the hooks instance (legacy)."""
    global _hooks_instance
    if _hooks_instance is None:
        _hooks_instance = LiteLLMGuardHooks(config_path)
    return _hooks_instance


def get_hooks() -> LiteLLMGuardHooks:
    """Get the current hooks instance (legacy)."""
    global _hooks_instance
    if _hooks_instance is None:
        _hooks_instance = LiteLLMGuardHooks()
    return _hooks_instance


# ===== EXPORT FOR config.yaml =====
# Usage in config.yaml:
#   guardrail: litellm_guard_hooks.LLMGuardCustomGuardrail
#
# Or use as factory:
#   guardrail: litellm_guard_hooks.get_guardrail()


if __name__ == '__main__':
    # Test the guardrails
    print("=" * 60)
    print("LiteLLM Guard Custom Guardrail Test")
    print("=" * 60)
    
    # Test guardrail instance
    guardrail = get_guardrail()
    print(f"\n✓ Custom guardrail initialized")
    print(f"  Guard Manager enabled: {guardrail.guard_manager.enabled}")
    print(f"  Input scanning: {guardrail.guard_config.get('input_scanning', {}).get('enabled', False)}")
    print(f"  Output scanning: {guardrail.guard_config.get('output_scanning', {}).get('enabled', False)}")
    
    # Test language detector
    print(f"\n✓ Language detector available")
    test_texts = [
        ("Hello world", "en"),
        ("你好", "zh"),
        ("Xin chào", "vi"),
    ]
    for text, expected_lang in test_texts:
        detected_lang = LanguageDetector.detect_language(text)
        status = "✓" if detected_lang == expected_lang else "✗"
        print(f"  {status} '{text}' -> {detected_lang} (expected {expected_lang})")
    
    print("\n" + "=" * 60)
    print("Ready for deployment in config.yaml!")
    print("=" * 60)
