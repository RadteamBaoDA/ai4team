import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class LanguageDetector:
    """Detect language from text and provide localized error messages."""
    LANGUAGE_PATTERNS = {
        'zh': {'patterns': [re.compile(r'[\u4e00-\u9fff]')], 'name': 'Chinese'},
        'vi': {'patterns': [re.compile(r'[\u0102\u0103\u0110\u0111\u0128\u0129\u0168\u0169\u01a0\u01a1\u01af\u01b0]')], 'name': 'Vietnamese'},
        'ja': {'patterns': [re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')], 'name': 'Japanese'},
        'ko': {'patterns': [re.compile(r'[\uac00-\ud7af]')], 'name': 'Korean'},
        'ru': {'patterns': [re.compile(r'[\u0400-\u04ff]')], 'name': 'Russian'},
        'ar': {'patterns': [re.compile(r'[\u0600-\u06ff]')], 'name': 'Arabic'},
    }
    ENGLISH_PATTERN = re.compile(r'\b(the|a|an|and|or|is|are|was|were|be|have|has|had)\b', re.IGNORECASE)

    ERROR_MESSAGES: Dict[str, Dict[str, str]] = {
        'en': {
            'prompt_blocked': 'Your input was blocked by the security scanner. Reason: {reason}',
            'prompt_blocked_detail': 'Input contains unsafe content and cannot be processed.',
            'response_blocked': 'Model output was blocked by the security scanner.',
            'server_error': 'Internal server error.',
            'upstream_error': 'Upstream service error.',
            'server_busy': 'Server is currently busy processing other requests. Please try again later.',
            'request_timeout': 'Request timed out. Please try again with a shorter prompt or later.',
            'queue_full': 'Request queue is full. Server is currently overloaded.',
        },
        # Additional languages omitted for brevity; main file retains full set if needed.
    }

    @staticmethod
    def detect_language(text: str) -> str:
        if not text:
            return 'en'
        for lang_code, lang_info in LanguageDetector.LANGUAGE_PATTERNS.items():
            for pattern in lang_info['patterns']:
                if pattern.search(text):
                    logger.info("Detected language: %s", lang_info['name'])
                    return lang_code
        if LanguageDetector.ENGLISH_PATTERN.search(text):
            return 'en'
        return 'en'

    @staticmethod
    def get_error_message(message_key: str, language: str, reason: str = '') -> str:
        messages = LanguageDetector.ERROR_MESSAGES.get(language, LanguageDetector.ERROR_MESSAGES['en'])
        message = messages.get(message_key, '')
        if reason and '{reason}' in message:
            message = message.format(reason=reason)
        return message


def get_language_message(text: str, message_key: str, reason: str = '') -> str:
    """Get localized error message based on detected language."""
    language = LanguageDetector.detect_language(text)
    return LanguageDetector.get_error_message(message_key, language, reason)
