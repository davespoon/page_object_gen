from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from ..llm.openai_client import get_model
from ..tools.refs_loader import load_ref_files
from ..tools.file_writer import write_text_file


def _extract_json_object(text: str) -> dict[str, Any]:
    """
    Best-effort extraction of a JSON object from model output.
    We expect the final assistant message to be JSON only, but this is defensive.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty model output")

    # Fast path: already JSON
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Try to find the first {...} block
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("Could not find JSON object in model output")
    obj = json.loads(m.group(0))
    if not isinstance(obj, dict):
        raise ValueError("Extracted JSON is not an object")
    return obj


@tool
def load_reference_files(paths: list[str]) -> dict:
    """
    Load reference .cs files and return their content (possibly truncated).
    Input: list of file paths.
    Output: { "refs": [ { "path": str, "truncated": bool, "content": str } ] }
    """
    refs = load_ref_files(paths)
    return {
        "refs": [
            {"path": r.path, "truncated": r.truncated, "content": r.content}
            for r in refs
        ]
    }


@tool
def write_csharp_file(out_dir: str, page_name: str, content: str) -> dict:
    """
    Write the generated C# file into out_dir as <page_name>.cs.
    Output: { "out_path": "<full path>", "bytes": <int> }
    """
    out_dir_path = Path(out_dir).resolve()
    out_path = (out_dir_path / f"{page_name}.cs").resolve()
    write_text_file(out_path, content)
    return {"out_path": str(out_path), "bytes": len(content.encode("utf-8", errors="ignore"))}


def _build_refs_agent_graph() -> Any:
    tools = [load_reference_files, write_csharp_file]
    tool_node = ToolNode(tools)

    llm = ChatOpenAI(model=get_model(), temperature=0.1).bind_tools(tools)

    def assistant(state: MessagesState) -> Dict[str, Any]:
        # Standard agent pattern: LLM decides whether to call tools or finish.
        msg = llm.invoke(state["messages"])
        return {"messages": [msg]}

    g = StateGraph(MessagesState)
    g.add_node("assistant", assistant)
    g.add_node("tools", tool_node)

    g.set_entry_point("assistant")

    # Canonical routing: if last assistant message has tool calls -> tools; else end
    g.add_conditional_edges("assistant", tools_condition)
    g.add_edge("tools", "assistant")

    return g.compile()


def run_refs_codegen_agent(
        *,
        url_final: str,
        page_name: str,
        out_dir: Path,
        dom_snapshot: dict[str, Any],
        refs_paths: list[str],
        recursion_limit: int = 20,
) -> dict[str, Any]:
    """
    Runs a LangGraph tool-using agent to:
      1) load refs via tool
      2) derive style contract (v0.2) + generate C# code (LLM)
      3) write file via tool
      4) return JSON summary: { out_path, style_contract }
    """
    graph = _build_refs_agent_graph()

    sys = SystemMessage(
        content=(
            "You generate C# Page Object Model code for Selenium tests.\n"
            "You have tools:\n"
            "- load_reference_files(paths)\n"
            "- write_csharp_file(out_dir, page_name, content)\n\n"
            "Your required process:\n"
            "1) Call load_reference_files with the provided ref file paths.\n"
            "2) From refs, infer a Style Contract JSON (schema_version '0.2').\n"
            "   - Use decision objects everywhere: {value, confidence 0..1, evidence[]}\n"
            "   - Keep evidence short.\n"
            "3) Generate a SINGLE C# file whose class name is exactly the provided page_name.\n"
            "   - Use the DOM snapshot to choose locators.\n"
            "   - Prefer stable attributes: id, data-testid, name, aria-label, then stable xpath.\n"
            "   - Keep it small (handful of elements + methods).\n"
            "4) Call write_csharp_file to write the code.\n"
            "5) Finally output ONLY a JSON object with keys:\n"
            "   - out_path (string)\n"
            "   - style_contract (object)\n"
            "No markdown. No explanation. No extra text."
        )
    )

    user = HumanMessage(
        content=(
            "Inputs:\n"
            f"- page_name: {page_name}\n"
            f"- out_dir: {str(out_dir.resolve())}\n"
            f"- url_final: {url_final}\n"
            f"- refs_paths: {json.dumps(refs_paths)}\n\n"
            f"DOM SNAPSHOT JSON:\n{json.dumps(dom_snapshot)[:180000]}\n"
        )
    )

    state: MessagesState = {"messages": [sys, user]}

    final: MessagesState = graph.invoke(state, config={"recursion_limit": recursion_limit})
    last = final["messages"][-1].content if final.get("messages") else ""
    summary = _extract_json_object(last)

    # Minimal validation of expected keys
    if "out_path" not in summary:
        raise ValueError("Agent summary missing out_path")
    if "style_contract" not in summary:
        # allow missing but normalize for downstream
        summary["style_contract"] = None

    return summary
