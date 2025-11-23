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