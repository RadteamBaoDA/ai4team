"""Utility helpers for formatting guard responses and toggling inline error handling."""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Sequence

logger = logging.getLogger(__name__)

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


def inline_guard_errors_enabled(config: Any, default: bool = True) -> bool:
    """Return True if inline guard error responses should be used.
    
    Checks in order:
    1. INLINE_GUARD_ERRORS environment variable
    2. config.get('inline_guard_errors') or config['inline_guard_errors']
    3. default parameter (True)
    """
    # First check environment variable
    env_value = os.environ.get('INLINE_GUARD_ERRORS')
    if env_value is not None:
        result = _coerce_bool(env_value, default)
        logger.debug(f"inline_guard_errors_enabled: INLINE_GUARD_ERRORS={env_value} -> {result}")
        return result
    
    # Then check config
    candidate = default
    try:
        if hasattr(config, "get"):
            candidate = config.get("inline_guard_errors", default)
        elif hasattr(config, "__getitem__"):
            candidate = config["inline_guard_errors"]
    except Exception:
        candidate = default
    
    result = _coerce_bool(candidate, default)
    logger.debug(f"inline_guard_errors_enabled: config value={candidate} -> {result}")
    return result


def extract_failed_scanners(scan_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract normalized scanner failure details from scan results."""
    if not isinstance(scan_result, dict):
        logger.debug("extract_failed_scanners: unexpected scan_result type %s", type(scan_result).__name__)
        return []

    failed: List[Dict[str, Any]] = []
    scanners_obj = scan_result.get("scanners", {})
    scanners: Dict[str, Any] = scanners_obj if isinstance(scanners_obj, dict) else {}
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
