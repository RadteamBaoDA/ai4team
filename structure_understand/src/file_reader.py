from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


Reader = Callable[[Path], str]


def read_file_for_summary(path: Path, max_bytes: int | None) -> str:
    reader = _EXTENSION_READERS.get(path.suffix.lower(), _read_text_file)
    content = reader(path)
    if not content:
        content = _read_text_file(path)
    return _truncate_text(content, max_bytes)


def _truncate_text(text: str, max_bytes: int | None) -> str:
    if max_bytes is None:
        return text
    encoded = text.encode("utf-8", errors="ignore")
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[:max_bytes]
    return truncated.decode("utf-8", errors="ignore")


def _read_text_file(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return handle.read()
    except OSError as exc:
        logger.warning("Unable to read %s: %s", path, exc)
        return ""


def _read_docx(path: Path) -> str:
    return _read_archive_text(path, _is_docx_entry)


def _read_pptx(path: Path) -> str:
    return _read_archive_text(path, _is_pptx_entry)


def _read_xlsx(path: Path) -> str:
    return _read_archive_text(path, _is_xlsx_entry)


def _read_pdf(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # pragma: no cover - best effort
        logger.debug("Unable to open PDF %s: %s", path, exc)
        return ""
    texts: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text()
        except Exception:
            page_text = ""
        if page_text:
            texts.append(page_text)
    return "\n".join(texts)


def _read_archive_text(path: Path, predicate: Callable[[str], bool]) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            chunks: list[str] = []
            for name in archive.namelist():
                lowered = name.lower()
                if not predicate(lowered):
                    continue
                try:
                    data = archive.read(name)
                except (KeyError, OSError):
                    continue
                chunk = _extract_text_from_xml(data)
                if chunk:
                    chunks.append(chunk)
            return "\n".join(chunks)
    except (zipfile.BadZipFile, OSError) as exc:
        logger.debug("Failed to read %s as archive: %s", path, exc)
        return ""


def _extract_text_from_xml(data: bytes) -> str:
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return ""
    parts: list[str] = []
    for element in root.iter():
        text = element.text
        if text:
            stripped = text.strip()
            if stripped:
                parts.append(stripped)
    return " ".join(parts)


def _is_docx_entry(name: str) -> bool:
    return name.startswith("word/") and name.endswith(".xml")


def _is_pptx_entry(name: str) -> bool:
    return name.startswith("ppt/") and name.endswith(".xml")


def _is_xlsx_entry(name: str) -> bool:
    return (name.startswith("xl/worksheets/") or name == "xl/sharedstrings.xml") and name.endswith(".xml")


_EXTENSION_READERS: dict[str, Reader] = {
    ".docx": _read_docx,
    ".pptx": _read_pptx,
    ".xlsx": _read_xlsx,
    ".pdf": _read_pdf,
}