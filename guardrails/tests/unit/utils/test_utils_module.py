from pathlib import Path
from types import SimpleNamespace
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_PATH = REPO_ROOT / "guardrails" / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ollama_guardrails.utils import utils


def test_extract_model_and_text_helpers():
    assert utils.extract_model_from_payload({"model": "llama"}) == "llama"
    assert utils.extract_model_from_payload({}) == "default"
    payload = {"prompt": "hello"}
    assert utils.extract_text_from_payload(payload) == "hello"
    payload = {"input": "data"}
    assert utils.extract_text_from_payload(payload) == "data"
    response = {"text": "done"}
    assert utils.extract_text_from_response(response) == "done"
    response = {"other": "value", "another": "part"}
    assert "value" in utils.extract_text_from_response(response)


def test_combine_messages_text_filters_roles():
    messages = [
        {"role": "system", "content": "set"},
        {"role": "user", "content": "first"},
        {"role": "user", "content": "second"},
    ]
    combined = utils.combine_messages_text(messages, roles=("user",))
    assert combined == "first\nsecond"
    latest = utils.combine_messages_text(messages, roles=("user",), latest_only=True)
    assert latest == "second"


def test_build_ollama_options_merges_known_fields():
    payload = {
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 128,
        "options": {"stop": ["END"]},
    }
    options = utils.build_ollama_options_from_openai_payload(payload)
    assert options["temperature"] == 0.2
    assert options["top_p"] == 0.9
    assert options["num_predict"] == 128
    assert options["stop"] == ["END"]


def test_extract_prompt_from_completion_payload_handles_list():
    payload = {"prompt": ["one", 2, None, "three"]}
    assert utils.extract_prompt_from_completion_payload(payload) == "one\n2\nthree"
    payload = {"prompt": None}
    assert utils.extract_prompt_from_completion_payload(payload) == ""
