from __future__ import annotations

from pathlib import Path

from .build_graph import build_generate_graph
from .state import PogState


def run_generate_graph(
        *,
        url: str,
        page_name: str,
        refs: list[str] | None,
        no_build: bool,
        out_dir: Path,
) -> PogState:
    graph = build_generate_graph().compile()

    init: PogState = {
        "url": url,
        "page_name": page_name,
        "refs": refs,
        "no_build": no_build,
        "out_dir": str(out_dir.resolve()),
        "build_ran": False,
        "build_success": False,
        "repairs_used": 0,
        "exit_code": 0,
    }

    final_state: PogState = graph.invoke(init)
    return final_state
