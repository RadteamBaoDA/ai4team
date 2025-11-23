from __future__ import annotations

import sys
import textwrap

from structure_understand.cli import main as cli_main


def test_cli_generates_markdown_report(tmp_path, monkeypatch):
    input_root = tmp_path / "input"
    input_root.mkdir()
    (input_root / "sample.txt").write_text("content")
    config_file = tmp_path / "config.yaml"
    report_file = tmp_path / "report.md"
    config_file.write_text(
        textwrap.dedent(
            f"""
            input_root: "{input_root.as_posix()}"
            output_file: "{report_file.as_posix()}"
            summarizer:
              provider: placeholder
            """
        )
    )

    monkeypatch.setattr(sys, "argv", ["prog", "--config", str(config_file)])

    cli_main()

    assert report_file.exists()
    contents = report_file.read_text()
    assert "| ./sample.txt | file" in contents