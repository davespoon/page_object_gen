from __future__ import annotations

from langgraph.graph import StateGraph, END

from .state import PogState
from .nodes import (
    node_resolve_sln,
    node_capture,
    node_snapshot,
    node_style_contract_if_refs,
    node_codegen,
    node_build_gate,
    node_build_and_repair,
    node_finalize,
)


def build_generate_graph() -> StateGraph:
    g = StateGraph(PogState)

    g.add_node("resolve_sln", node_resolve_sln)
    g.add_node("capture", node_capture)
    g.add_node("snapshot", node_snapshot)
    g.add_node("style_contract", node_style_contract_if_refs)
    g.add_node("codegen", node_codegen)
    g.add_node("build_gate", node_build_gate)
    g.add_node("build_and_repair", node_build_and_repair)
    g.add_node("finalize", node_finalize)

    # Happy path
    g.set_entry_point("resolve_sln")

    # If sln not found -> finalize early
    def sln_found(state: PogState) -> str:
        return "ok" if state.get("sln_path") else "fail"

    g.add_conditional_edges(
        "resolve_sln",
        sln_found,
        {
            "ok": "capture",
            "fail": "finalize",
        },
    )

    g.add_edge("capture", "snapshot")
    g.add_edge("snapshot", "style_contract")
    g.add_edge("style_contract", "codegen")
    g.add_edge("codegen", "build_gate")
    g.add_edge("build_gate", "build_and_repair")
    g.add_edge("build_and_repair", "finalize")
    g.add_edge("finalize", END)

    return g
