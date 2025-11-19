"""Utility helpers for formatting guard responses and toggling inline error handling."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

_BOOL_TRUE = {"1", "true", "yes", "on", "y", "t"}


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in _BOOL_TRUE
    return default


def inline_guard_errors_enabled(config: Any, default: bool = False) -> bool:
    """Return True if inline guard error responses should be used."""
    candidate = default
    try:
        if hasattr(config, "get"):
            candidate = config.get("inline_guard_errors", default)
        elif hasattr(config, "__getitem__"):
            candidate = config["inline_guard_errors"]
    except Exception:
        candidate = default
    return _coerce_bool(candidate, default)


def extract_failed_scanners(scan_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract normalized scanner failure details from scan results."""
    failed: List[Dict[str, Any]] = []
    scanners: Dict[str, Any] = (scan_result or {}).get("scanners", {})
    for scanner_name, info in scanners.items():
        if info and not info.get("passed", True):
            failed.append(
                {
                    "scanner": scanner_name,
                    "reason": info.get("reason", "Content policy violation"),
                    "score": info.get("score"),
                    "remediation": info.get("remediation"),
                }
            )
    return failed


def format_markdown_error(title: str, description: str, failed_scanners: Sequence[Dict[str, Any]]) -> str:
    """Create a markdown-formatted error message for inline responses."""
    lines: List[str] = [f"### {title}"]
    if description:
        lines.extend(["", description])

    if failed_scanners:
        lines.append("")
        lines.extend(["| Scanner | Reason | Score |", "| --- | --- | --- |"])
        for item in failed_scanners:
            score = item.get("score")
            if isinstance(score, (int, float)):
                score_text = f"{score:.3f}"
            else:
                score_text = str(score) if score is not None else "-"
            lines.append(
                f"| {item.get('scanner', '-') } | {item.get('reason', '-') } | {score_text} |"
            )

    lines.extend([
        "",
        "> Please review the input and try again after removing the flagged content.",
    ])
    return "\n".join(lines)
