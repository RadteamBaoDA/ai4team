from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from .config import StructureConfig
from .summarizer import SummaryEngine

logger = logging.getLogger(__name__)


@dataclass
class StructureEntry:
    relative_path: Path
    kind: str  # "file" or "folder"
    size: int | None
    summary: str


def _is_excluded(path: Path, exclude_names: Iterable[str]) -> bool:
    exclude_set = set(exclude_names)
    return any(part in exclude_set for part in path.parts if part and part != ".")


def _read_preview(path: Path, max_bytes: int) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return handle.read(max_bytes)
    except OSError as exc:
        logger.warning("Unable to read %s: %s", path, exc)
        return ""


def _safe_stat(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError as exc:
        logger.debug("Unable to stat %s: %s", path, exc)
        return None


def _describe_folder(file_count: int, dir_count: int) -> str:
    parts = []
    if file_count == 1:
        parts.append("1 file")
    elif file_count:
        parts.append(f"{file_count} files")
    if dir_count == 1:
        parts.append("1 subfolder")
    elif dir_count:
        parts.append(f"{dir_count} subfolders")
    if not parts:
        return "Empty folder"
    return "Contains " + " and ".join(parts)


def collect_structure(config: StructureConfig, summarizer: SummaryEngine) -> List[StructureEntry]:
    entries: List[StructureEntry] = []
    file_tasks: List[tuple[StructureEntry, Future[str]]] = []
    with ThreadPoolExecutor(max_workers=config.summary_workers) as executor:
        for dirpath, dirnames, filenames in os.walk(config.input_root, topdown=True):
            current = Path(dirpath)
            rel_dir = current.relative_to(config.input_root) if current != config.input_root else Path(".")
            dirnames[:] = [d for d in sorted(dirnames) if not _is_excluded(rel_dir / d, config.exclude_paths)]
            filtered_files = [f for f in sorted(filenames) if not _is_excluded(rel_dir / f, config.exclude_paths)]
            entries.append(
                StructureEntry(
                    relative_path=rel_dir,
                    kind="folder",
                    size=None,
                    summary=_describe_folder(len(filtered_files), len(dirnames)),
                )
            )
            for filename in filtered_files:
                file_path = current / filename
                rel_file = rel_dir / filename
                preview = _read_preview(file_path, config.max_file_bytes)
                trimmed = preview[: config.max_prompt_chars]
                entry = StructureEntry(
                    relative_path=rel_file,
                    kind="file",
                    size=_safe_stat(file_path),
                    summary="",
                )
                entries.append(entry)
                task = executor.submit(summarizer.summarize, rel_file.as_posix(), trimmed)
                file_tasks.append((entry, task))
    for entry, future in file_tasks:
        entry.summary = future.result()
    return entries


def build_markdown(entries: List[StructureEntry], input_root: Path, config_path: Path) -> str:
    lines = [
        f"# Structure map for `{input_root}`",
        "",
        f"_Generated from {config_path}._",
        "",
        "| Path | Type | Size | Summary |",
        "| --- | --- | --- | --- |",
    ]
    for entry in entries:
        display_path = entry.relative_path.as_posix()
        if display_path == ".":
            display_path = "./"
        elif not display_path.startswith("./"):
            display_path = "./" + display_path
        size_column = str(entry.size) if entry.size is not None else ""
        summary = entry.summary.replace("\n", " ").replace("|", "\\|")
        lines.append(f"| {display_path} | {entry.kind} | {size_column} | {summary} |")
    return "\n".join(lines) + "\n"
