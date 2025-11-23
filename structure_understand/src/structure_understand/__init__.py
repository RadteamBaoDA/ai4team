from __future__ import annotations

from pathlib import Path

package_dir = Path(__file__).resolve().parent
src_dir = package_dir.parent
if str(src_dir) not in __path__:
    __path__.insert(0, str(src_dir))
