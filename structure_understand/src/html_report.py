from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable
import json

from .traversal import StructureEntry


def serialize_entries(entries: Iterable[StructureEntry]) -> list[dict[str, str]]:
    return [
        {
            "path": _format_path(entry.relative_path),
            "kind": entry.kind,
            "size": entry.size if entry.size is not None else "",
            "summary": (entry.summary or "").replace("\n", " "),
        }
        for entry in entries
    ]


def build_html_report(
    entries: Iterable[StructureEntry],
    input_root: Path,
    config_path: Path,
    data_json: str | None = None,
) -> str:
    data = serialize_entries(entries)
    table_rows = "\n".join(
        """
        <tr>
          <td class=\"text-nowrap\">{path}</td>
          <td>{kind}</td>
          <td class=\"text-end\">{size}</td>
          <td>{summary}</td>
        </tr>
        """.format(
            path=escape(row["path"]),
            kind=escape(row["kind"]),
            size=escape(str(row["size"])),
            summary=escape(row["summary"]),
        )
        for row in data
    )
    markdown_entries = "\n\n".join(
        "Path: {path}\nType: {kind}\nSize: {size}\nSummary: {summary}".format(
            path=escape(row["path"]),
            kind=escape(row["kind"]),
            size=escape(str(row["size"])),
            summary=escape(row["summary"]),
        )
        for row in data
    )
    json_payload = data_json or json.dumps(data, ensure_ascii=False)
    html_parts = [
        "<!doctype html>",
        "<html lang=\"en\">",
        "<head>",
        "<meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        "<link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/@tabler/core@latest/dist/css/tabler.min.css\">",
        "<script src=\"https://cdn.jsdelivr.net/npm/@tabler/core@latest/dist/js/tabler.min.js\"></script>",
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
        "<div class=\"d-flex align-items-center mb-3\">",
        "<label class=\"form-label text-muted me-2 mb-0\" for=\"path-filter-input\">Filter by path:</label>",
        "<input id=\"path-filter-input\" class=\"form-control form-control-sm w-50\" placeholder=\"Enter path text\" autocomplete=\"off\">",
        "</div>",
        "<div class=\"table-responsive\">",
        "<table id=\"entries-table\" class=\"table card-table table-striped table-hover\">",
        "<thead>",
        "<tr>",
        "<th>Path</th>",
        "<th>Type</th>",
        "<th class=\"text-end\">Size</th>",
        "<th>Summary</th>",
        "</tr>",
        "</thead>",
        "<tbody>",
        table_rows,
        "</tbody>",
        "</table>",
        "</div>",
        "</div>",
        "</div>",
        "<div class=\"card mt-4\">",
        "<div class=\"card-header\">",
        "<strong>Data JSON</strong>",
        "</div>",
        "<div class=\"card-body bg-dark text-white\">",
        f"<pre class=\"mb-0\">{escape(json_payload)}</pre>",
        "</div>",
        "</div>",
        "<div class=\"card mt-4\">",
        "<div class=\"card-header\">",
        "<strong>Entries (Markdown)</strong>",
        "</div>",
        "<div class=\"card-body bg-black text-white font-monospace\">",
        f"<pre class=\"mb-0\">{escape(markdown_entries)}</pre>",
        "</div>",
        "</div>",
        "</div>",
        "</div>",
        "</div>",
        "</div>",
        "</body>",
        "<script>",
        "(function(){",
        "  const filterInput = document.getElementById('path-filter-input');",
        "  const tableRows = document.querySelectorAll('#entries-table tbody tr');",
        "  if (!filterInput) return;",
        "  filterInput.addEventListener('input', () => {",
        "    const term = filterInput.value.trim().toLowerCase();",
        "    tableRows.forEach((row) => {",
        "      const pathCell = row.querySelector('td:first-child');",
        "      const text = pathCell ? pathCell.textContent?.toLowerCase() ?? '' : '';",
        "      row.style.display = term && !text.includes(term) ? 'none' : '';",
        "    });",
        "  });",
        "})();",
        "</script>",
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
