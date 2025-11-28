from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_PATH = REPO_ROOT / "guardrails" / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ollama_guardrails.utils.language import LanguageDetector, get_language_message


def test_detect_language_uses_unicode_patterns():
    text = "你好，世界"
    assert LanguageDetector.detect_language(text) == "zh"


def test_detect_language_falls_back_to_english():
    text = "This is a simple sentence"
    assert LanguageDetector.detect_language(text) == "en"


def test_normalize_lang_code_aliases():
    assert LanguageDetector.normalize_lang_code("en-US") == "en"
    assert LanguageDetector.normalize_lang_code("pt-BR") == "pt"
    assert LanguageDetector.normalize_lang_code("xx") == "en"


def test_get_error_message_and_localized_message():
    message = LanguageDetector.get_error_message("prompt_blocked", "en", "unsafe")
    assert "unsafe" in message
    localized = get_language_message("你好", "server_busy")
    assert localized