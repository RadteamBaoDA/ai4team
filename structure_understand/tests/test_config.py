from __future__ import annotations

import textwrap

from structure_understand.config import load_config


def test_load_config_resolves_relative_paths(tmp_path):
    (tmp_path / "input_root").mkdir()
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        textwrap.dedent("""
        input_root: ./input_root
        output_file: ./report.md
        exclude_paths:
          - __pycache__
        max_file_bytes: 1234
        max_prompt_chars: 400
        summarizer:
          provider: placeholder
          placeholder:
            max_chars: 150
        """)
    )

    config = load_config(config_file)

    assert config.input_root == (tmp_path / "input_root").resolve()
    assert config.output_file == (tmp_path / "report.md").resolve()
    assert config.exclude_paths == ["__pycache__"]
    assert config.max_file_bytes == 1234
    assert config.max_prompt_chars == 400
    assert config.summarizer_settings["provider"] == "placeholder"
    assert config.config_path == config_file.resolve()
