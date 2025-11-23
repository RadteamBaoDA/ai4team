from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable
import json

from .traversal import StructureEntry


def build_html_report(entries: Iterable[StructureEntry], input_root: Path, config_path: Path) -> str:
    data = [
        {
            "path": _format_path(entry.relative_path),
            "kind": entry.kind,
            "size": entry.size if entry.size is not None else "",
            "summary": (entry.summary or "").replace("\n", " "),
        }
        for entry in entries
    ]
    text_entries = "\n\n".join(
        f"Path: {_format_path(entry.relative_path)}\nSummary: {escape(entry.summary or '')}"
        for entry in entries
    )
    data_json = json.dumps(data, ensure_ascii=False)
    html_parts = [
        "<!doctype html>",
        "<html lang=\"en\">",
        "<head>",
        "<meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        "<link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/@tabler/core@2.6.0/dist/css/tabler.min.css\">",
        "<link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/tabulator-tables@6.3.5/dist/css/tabulator_min.css\">",
        f"<title>Structure map for {escape(str(input_root))}</title>",
        "</head>",
        "<body class=\"antialiased bg-body\">",
        "<div class=\"page\">",
        "<div class=\"page-body\">",
        "<div class=\"container py-4\">",
        "<div class=\"card shadow-sm\">",
        "<div class=\"card-header\">",
        f"<h2 class=\"card-title\">Structure map for {escape(str(input_root))}</h2>",
        f"<p class=\"text-muted mb-0\">Generated from {escape(str(config_path))}</p>",
        "</div>",
        "<div class=\"card-body\">",
        "<div class=\"mb-3\">",
        "<input id=\"search-input\" class=\"form-control\" placeholder=\"Search files or folders\" autocomplete=\"off\">",
        "</div>",
        "<div id=\"tabulator-table\"></div>",
        "</div>",
        "</div>",
        "</div>",
        "</div>",
        "</div>",
        "<div class=\"card mt-4\">",
        "<div class=\"card-header\">",
        "<strong>Summary text view</strong>",
        "</div>",
        "<div class=\"card-body\">",
        f"<pre class=\"bg-body-secondary text-break p-3\">{escape(text_entries)}</pre>",
        "</div>",
        "</div>",
        "<script type=\"module\">",
        "import {Table} from 'https://cdn.jsdelivr.net/npm/tabulator-tables@6.3.5/dist/js/tabulator_esm.min.js';",
        "const data = ",
        data_json,
        ";",
        "const table = new Table({",
        "  element: document.getElementById('tabulator-table'),",
        "  data,",
        "  layout: 'fitColumns',",
        "  movableColumns: true,",
        "  columns: [",
        "    { title: 'Path', field: 'path', headerFilter: 'input', sorter: 'string' },",
        "    { title: 'Type', field: 'kind', width: 90, sorter: 'string' },",
        "    { title: 'Size', field: 'size', hozAlign: 'right', sorter: 'number' },",
        "    { title: 'Summary', field: 'summary', responsive: 0 },",
        "  ],",
        "});",
        "const search = document.getElementById('search-input');",
        "search.addEventListener('input', () => {",
        "  const term = search.value.trim().toLowerCase();",
        "  if (!term) {",
        "    table.clearFilter(true);",
        "    return;",
        "  }",
        "  table.setFilter((row) => {",
        "    const path = (row.getData().path || '').toLowerCase();",
        "    const summary = (row.getData().summary || '').toLowerCase();",
        "    return path.includes(term) || summary.includes(term);",
        "  });",
        "});",
        "</script>",
        "</body>",
        "</html>",
    ]
    return "\n".join(html_parts)


def _format_path(relative: Path) -> str:
    display = relative.as_posix()
    if display == ".":
        return "./"
    if not display.startswith("./"):
        return "./" + display
    return display
