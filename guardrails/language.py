import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class LanguageDetector:
    """Detect language from text and provide localized error messages."""
    LANGUAGE_PATTERNS = {
        'zh': {'patterns': [r'[\u4e00-\u9fff]'], 'name': 'Chinese'},
        'vi': {'patterns': [r'[\u0102\u0103\u0110\u0111\u0128\u0129\u0168\u0169\u01a0\u01a1\u01af\u01b0]'], 'name': 'Vietnamese'},
        'ja': {'patterns': [r'[\u3040-\u309f\u30a0-\u30ff]'], 'name': 'Japanese'},
        'ko': {'patterns': [r'[\uac00-\ud7af]'], 'name': 'Korean'},
        'ru': {'patterns': [r'[\u0400-\u04ff]'], 'name': 'Russian'},
        'ar': {'patterns': [r'[\u0600-\u06ff]'], 'name': 'Arabic'},
    }

    ERROR_MESSAGES: Dict[str, Dict[str, str]] = {
        'en': {
            'prompt_blocked': 'Your input was blocked by the security scanner. Reason: {reason}',
            'prompt_blocked_detail': 'Input contains unsafe content and cannot be processed.',
            'response_blocked': 'Model output was blocked by the security scanner.',
            'server_error': 'Internal server error.',
            'upstream_error': 'Upstream service error.',
        },
        # Additional languages omitted for brevity; main file retains full set if needed.
    }

    @staticmethod
    def detect_language(text: str) -> str:
        if not text:
            return 'en'
        for lang_code, lang_info in LanguageDetector.LANGUAGE_PATTERNS.items():
            for pattern in lang_info['patterns']:
                if re.search(pattern, text):
                    logger.info("Detected language: %s", lang_info['name'])
                    return lang_code
        if re.search(r'\b(the|a|an|and|or|is|are|was|were|be|have|has|had)\b', text, re.IGNORECASE):
            return 'en'
        return 'en'

    @staticmethod
    def get_error_message(message_key: str, language: str, reason: str = '') -> str:
        messages = LanguageDetector.ERROR_MESSAGES.get(language, LanguageDetector.ERROR_MESSAGES['en'])
        message = messages.get(message_key, '')
        if reason and '{reason}' in message:
            message = message.format(reason=reason)
        return message
