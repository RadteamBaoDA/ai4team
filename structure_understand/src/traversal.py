from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

from .config import StructureConfig
from .file_reader import read_file_for_summary
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


def _should_summarize(path: Path, extensions: list[str]) -> bool:
    if not extensions:
        return True
    suffix = path.suffix.lower()
    return bool(suffix and suffix in extensions)


def _skipped_extension_message(path: Path) -> str:
    suffix = path.suffix.lower() or "<no extension>"
    return f"Summary skipped for extension {suffix}"


def collect_structure(config: StructureConfig, summarizer: SummaryEngine) -> List[StructureEntry]:
    logger.info("Collecting structure from %s", config.input_root)
    entries: List[StructureEntry] = []
    summary_targets: List[Tuple[StructureEntry, Path]] = []
    allowed_extensions = config.summary_extensions
    for dirpath, dirnames, filenames in os.walk(config.input_root, topdown=True):
        current = Path(dirpath)
        rel_dir = current.relative_to(config.input_root) if current != config.input_root else Path(".")
        dirnames[:] = [d for d in sorted(dirnames) if not _is_excluded(rel_dir / d, config.exclude_paths)]
        filtered_files = [f for f in sorted(filenames) if not _is_excluded(rel_dir / f, config.exclude_paths)]
        logger.info(
            "Scanned folder %s (files: %d, subfolders: %d)",
            rel_dir,
            len(filtered_files),
            len(dirnames),
        )
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
            entry = StructureEntry(
                relative_path=rel_file,
                kind="file",
                size=_safe_stat(file_path),
                summary="",
            )
            entries.append(entry)
            if _should_summarize(rel_file, allowed_extensions):
                logger.info("Queueing summary for %s", rel_file)
                summary_targets.append((entry, file_path))
            else:
                logger.info("Skipping summary for %s (extension filtered)", rel_file)
                entry.summary = _skipped_extension_message(rel_file)
    if summary_targets:
        logger.info("Preparing %d summary tasks", len(summary_targets))
        tasks = _prepare_summary_tasks(summary_targets)
        with ThreadPoolExecutor(max_workers=config.summary_workers) as executor:
            futures = [
                executor.submit(
                    _read_and_summarize,
                    summarizer,
                    entry,
                    rel_path,
                    file_path,
                    config.max_file_bytes,
                    config.max_prompt_chars,
                )
                for entry, file_path, rel_path in tasks
            ]
            for future in futures:
                future.result()
    return entries


def _prepare_summary_tasks(summary_targets: List[Tuple[StructureEntry, Path]]) -> list[Tuple[StructureEntry, Path, str]]:
    tasks: list[Tuple[StructureEntry, Path, str]] = []
    for entry, file_path in summary_targets:
        rel_path = entry.relative_path.as_posix()
        tasks.append((entry, file_path, rel_path))
    return tasks


def _read_and_summarize(
    summarizer: SummaryEngine,
    entry: StructureEntry,
    rel_path: str,
    file_path: Path,
    max_bytes: int | None,
    max_prompt: int | None,
) -> None:
    logger.info("Reading %s for summarization", rel_path)
    raw_text = read_file_for_summary(file_path, max_bytes)
    if max_prompt is None:
        prompt_text = raw_text
    else:
        prompt_text = raw_text[:max_prompt]
    logger.info("Sending %s to summarizer", rel_path)
    entry.summary = summarizer.summarize(rel_path, prompt_text)


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
