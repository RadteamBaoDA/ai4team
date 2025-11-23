from pathlib import Path

from structure_understand.html_report import build_html_report
from structure_understand.traversal import StructureEntry


def test_html_report_includes_search_and_tree(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    entries = [
        StructureEntry(relative_path=Path("."), kind="folder", size=None, summary="Root summary"),
        StructureEntry(relative_path=Path("foo.txt"), kind="file", size=12, summary="Foo summary"),
    ]

    html = build_html_report(entries, tmp_path / "input", config_path)

    assert "Search files or folders" in html
    assert "tabulator-tables@6.3.5" in html
    assert "tabulator-table" in html
    assert "Summary text view" in html
    assert "Generated from" in html
