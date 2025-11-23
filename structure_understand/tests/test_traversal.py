from __future__ import annotations

from pathlib import Path

from structure_understand.config import StructureConfig
from structure_understand.summarizer import build_summary_engine
from structure_understand.traversal import build_markdown, collect_structure


def _build_config(tmp_path: Path) -> StructureConfig:
    return StructureConfig(
        input_root=tmp_path / "input",
        output_file=tmp_path / "report.md",
        exclude_paths=[],
        max_file_bytes=100,
        max_prompt_chars=50,
        summarizer_settings={"provider": "placeholder"},
        config_path=tmp_path / "config.yaml",
        summary_workers=2,
        summary_extensions=[],
        html_output_file=tmp_path / "report.html",
        json_output_file=tmp_path / "report.json",
    )


def test_collect_structure_includes_folders_and_files(tmp_path):
    input_root = tmp_path / "input"
    nested = input_root / "nested"
    nested.mkdir(parents=True)
    (input_root / "alpha.txt").write_text("alpha")
    (nested / "beta.md").write_text("beta")

    config = _build_config(tmp_path)
    config.input_root.mkdir(exist_ok=True)
    summarizer = build_summary_engine(config.summarizer_settings)

    entries = collect_structure(config, summarizer)

    assert any(entry.kind == "folder" and entry.relative_path == Path(".") for entry in entries)
    assert any(entry.kind == "file" and entry.relative_path == Path("alpha.txt") for entry in entries)
    assert any(entry.kind == "file" and entry.relative_path == Path("nested/beta.md") for entry in entries)

    markdown = build_markdown(entries, config.input_root, config.config_path)
    assert "| ./alpha.txt | file" in markdown


def test_collect_structure_respects_extension_filter(tmp_path):
    input_root = tmp_path / "input"
    input_root.mkdir(exist_ok=True)
    (input_root / "allowed.md").write_text("allowed")
    (input_root / "blocked.txt").write_text("blocked")

    config = _build_config(tmp_path)
    config.summary_extensions = [".md"]
    summarizer = build_summary_engine(config.summarizer_settings)

    entries = collect_structure(config, summarizer)

    blocked_entry = next(entry for entry in entries if entry.relative_path == Path("blocked.txt"))
    assert "Summary skipped" in blocked_entry.summary
    allowed_entry = next(entry for entry in entries if entry.relative_path == Path("allowed.md"))
    assert "Summary skipped" not in allowed_entry.summary