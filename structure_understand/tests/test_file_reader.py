from __future__ import annotations

import zipfile
from pathlib import Path

from structure_understand.file_reader import read_file_for_summary


def _write_zip(path: Path, entries: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def test_read_text_file_respects_max_bytes(tmp_path: Path) -> None:
    file_path = tmp_path / "plain.txt"
    file_path.write_text("Hello world")

    result = read_file_for_summary(file_path, 5)

    assert result == "Hello"


def test_read_docx_extracts_document_text(tmp_path: Path) -> None:
    docx = tmp_path / "notes.docx"
    _write_zip(docx, {
        "word/document.xml": "<w:document><w:body><w:p><w:r><w:t>Docx text</w:t></w:r></w:p></w:body></w:document>"
    })

    result = read_file_for_summary(docx, None)

    assert "Docx text" in result


def test_read_pptx_extracts_slide_text(tmp_path: Path) -> None:
    pptx = tmp_path / "deck.pptx"
    _write_zip(pptx, {
        "ppt/slides/slide1.xml": "<p:spTree><a:txBody><a:p><a:r><a:t>Slide summary</a:t></a:r></a:p></a:txBody></p:spTree>"
    })

    result = read_file_for_summary(pptx, None)

    assert "Slide summary" in result


def test_read_xlsx_includes_shared_strings(tmp_path: Path) -> None:
    xlsx = tmp_path / "workbook.xlsx"
    _write_zip(xlsx, {
        "xl/sharedstrings.xml": "<sst><si><t>Cell text</t></si></sst>",
        "xl/worksheets/sheet1.xml": "<worksheet><sheetData><row><c><v>42</v></c></row></sheetData></worksheet>"
    })

    result = read_file_for_summary(xlsx, None)

    assert "Cell text" in result
    assert "42" in result
