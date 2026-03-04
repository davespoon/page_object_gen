from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_trace_file(out_dir: Path, run_id: str, trace: list[dict[str, Any]]) -> Path:
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / f".pog-trace-{run_id}.json"
    payload: dict[str, Any] = {
        "run_id": run_id,
        "events": trace,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
