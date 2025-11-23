from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_PATH = REPO_ROOT / "guardrails" / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ollama_guardrails.utils import guard_responses as gr


def test_coerce_bool_and_inline_guard_env(monkeypatch):
    assert gr._coerce_bool("yes") is True
    assert gr._coerce_bool("no") is False
    monkeypatch.setenv("INLINE_GUARD_ERRORS", "0")
    config = {"inline_guard_errors": True}
    assert gr.inline_guard_errors_enabled(config) is False
    monkeypatch.delenv("INLINE_GUARD_ERRORS", raising=False)
    config = {"inline_guard_errors": False}
    assert gr.inline_guard_errors_enabled(config) is False


def test_extract_failed_scanners_filters_passed():
    scan = {
        "scanners": {
            "Good": {"passed": True},
            "Bad": {"passed": False, "reason": "bad", "score": 0.5},
        }
    }
    failed = gr.extract_failed_scanners(scan)
    assert len(failed) == 1
    assert failed[0]["scanner"] == "Bad"


def test_format_markdown_error_builds_table():
    text = gr.format_markdown_error(
        "Input blocked",
        "Nope",
        [{"scanner": "X", "reason": "bad", "score": 0.9}],
    )
    assert "### Input blocked" in text
    assert "| Scanner |" in text
    assert "X" in text
*** End Patch