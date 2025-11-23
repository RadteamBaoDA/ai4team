from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class StructureConfig:
    input_root: Path
    output_file: Path
    exclude_paths: list[str]
    max_file_bytes: int | None
    max_prompt_chars: int | None
    summarizer_settings: dict[str, Any]
    config_path: Path
    summary_workers: int
    summary_extensions: list[str]
    html_output_file: Path


def _resolve_path(base: Path, raw_value: Any) -> Path:
    if raw_value is None:
        raise ValueError("Configuration is missing a required path")
    candidate = Path(raw_value)
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def _normalize_extensions(raw_value: Any) -> list[str]:
    if not raw_value:
        return []
    normalized: list[str] = []
    for item in raw_value:
        if item is None:
            continue
        ext = str(item).strip()
        if not ext:
            continue
        if not ext.startswith('.'):
            ext = '.' + ext
        normalized.append(ext.lower())
    return normalized


def load_config(path: Path) -> StructureConfig:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    base = path.parent
    input_root = _resolve_path(base, raw.get("input_root", "../input"))
    output_file = _resolve_path(base, raw.get("output_file", "structure_summary.md"))
    html_output_file = _resolve_path(base, raw.get("html_output_file", "structure_summary.html"))
    exclude_paths = list(raw.get("exclude_paths", []))
    max_file_bytes = raw.get("max_file_bytes")
    if max_file_bytes is not None:
        max_file_bytes = int(max_file_bytes)
    max_prompt_chars = raw.get("max_prompt_chars")
    if max_prompt_chars is not None:
        max_prompt_chars = int(max_prompt_chars)
    summary_type = str(raw.get("summary_type", "ollama")).lower()
    summarizer_settings = raw.get("summarizer", {}) or {}
    summarizer_settings.setdefault("provider", summary_type)
    default_workers = os.cpu_count() or 4
    requested_workers = raw.get("summary_workers")
    summary_workers = max(1, int(requested_workers)) if requested_workers is not None else default_workers
    summary_extensions = _normalize_extensions(raw.get("summary_extensions"))
    return StructureConfig(
        input_root=input_root,
        output_file=output_file,
        exclude_paths=exclude_paths,
        max_file_bytes=max_file_bytes,
        max_prompt_chars=max_prompt_chars,
        summarizer_settings=summarizer_settings,
        config_path=path.resolve(),
        summary_workers=summary_workers,
        summary_extensions=summary_extensions,
        html_output_file=html_output_file,
    )
