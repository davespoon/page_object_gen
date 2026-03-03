from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RefFile:
    path: str
    content: str
    truncated: bool


def load_ref_files(paths: list[str], *, max_chars_per_file: int = 35_000) -> list[RefFile]:
    refs: list[RefFile] = []
    for p in paths:
        path = Path(p).expanduser().resolve()
        text = path.read_text(encoding="utf-8", errors="replace")
        truncated = False
        if len(text) > max_chars_per_file:
            text = text[:max_chars_per_file] + "\n/* [TRUNCATED] */\n"
            truncated = True
        refs.append(RefFile(path=str(path), content=text, truncated=truncated))
    return refs
