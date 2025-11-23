"""Pytest helpers that make the package importable regardless of CWD."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_PATH = str(PROJECT_ROOT)
if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)
