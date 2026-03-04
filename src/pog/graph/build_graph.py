from __future__ import annotations

from langgraph.graph import StateGraph, END

from .state import PogState
from .nodes import (
    node_resolve_sln,
    node_capture,
    node_snapshot,
    node_codegen_generic,
    node_build_gate,
    node_build_and_repair,
    node_finalize, node_codegen_refs_agent,
)


def build_generate_graph() -> StateGraph:
    g = StateGraph(PogState)

    g.add_node("resolve_sln", node_resolve_sln)
    g.add_node("capture", node_capture)
    g.add_node("snapshot", node_snapshot)

    g.add_node("codegen_generic", node_codegen_generic)
    g.add_node("codegen_refs_agent", node_codegen_refs_agent)

    g.add_node("build_gate", node_build_gate)
    g.add_node("build_and_repair", node_build_and_repair)
    g.add_node("finalize", node_finalize)

    g.set_entry_point("resolve_sln")

    def sln_found(state: PogState) -> str:
        return "ok" if state.get("sln_path") else "fail"

    g.add_conditional_edges(
        "resolve_sln",
        sln_found,
        {"ok": "capture", "fail": "finalize"},
    )

    g.add_edge("capture", "snapshot")

    def has_refs(state: PogState) -> str:
        refs = state.get("refs") or []
        return "refs" if refs else "generic"

    g.add_conditional_edges(
        "snapshot",
        has_refs,
        {"refs": "codegen_refs_agent", "generic": "codegen_generic"},
    )

    g.add_edge("codegen_refs_agent", "build_gate")
    g.add_edge("codegen_generic", "build_gate")

    g.add_edge("build_gate", "build_and_repair")
    g.add_edge("build_and_repair", "finalize")
    g.add_edge("finalize", END)

    return g
