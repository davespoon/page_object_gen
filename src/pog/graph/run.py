from __future__ import annotations

import uuid
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

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
    run_id = uuid.uuid4().hex

    checkpointer = MemorySaver()
    graph = build_generate_graph().compile(checkpointer=checkpointer)

    init: PogState = {
        "run_id": run_id,
        "trace": [],
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

    # thread_id is required for checkpointing separation across runs
    final_state: PogState = graph.invoke(init, config={"configurable": {"thread_id": run_id}})
    return final_state
