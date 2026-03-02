from __future__ import annotations

from pathlib import Path
from typing import Optional


def find_nearest_sln(start_dir: Path) -> Optional[Path]:
    """Walk upward from start_dir to find the nearest *.sln file.

    Returns the first .sln found (lexicographically sorted within the directory),
    or None if not found.
    """
    cur = start_dir.resolve()

    while True:
        slns = sorted(cur.glob("*.sln"))
        if slns:
            return slns[0]

        parent = cur.parent
        if parent == cur:
            return None
        cur = parent
