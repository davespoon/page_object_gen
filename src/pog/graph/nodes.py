from __future__ import annotations

from pathlib import Path

from .state import PogState
from ..utils.logging import log
from ..tools.sln_finder import find_nearest_sln
from ..tools.selenium_capture import capture_page
from ..tools.dom_simplify import simplify_dom_snapshot
from ..tools.file_writer import write_text_file
from ..tools.dotnet_build import run_dotnet_build
from ..codegen.generic_pom import generate_generic_pom
from ..tools.refs_loader import load_ref_files
from ..llm.derive_and_codegen import (
    derive_style_contract_from_refs,
    generate_pom_with_style,
    repair_pom_from_build_errors,
)


def node_resolve_sln(state: PogState) -> PogState:
    cwd = Path(state["out_dir"]).resolve()
    log(f"Working directory: {cwd}")

    sln = find_nearest_sln(cwd)
    if sln is None:
        log("ERROR: No .sln found in current or parent directories.")
        log("Run `pog` from within a repo containing a .sln.")
        return {"sln_path": None, "exit_code": 2}

    log(f"Found solution: {sln}")
    return {"sln_path": str(sln), "exit_code": 0}


def node_capture(state: PogState) -> PogState:
    log("Launching browser (headless) and navigating…")
    captured = capture_page(state["url"], headless=True)
    log(f"Navigation complete. Final URL: {captured.url_final}")
    log(f"Page title: {captured.title!r}")
    log(f"Captured HTML size: {len(captured.html)} chars")
    return {
        "url_final": captured.url_final,
        "title": captured.title,
        "html": captured.html,
    }


def node_snapshot(state: PogState) -> PogState:
    log("Building bounded DOM snapshot…")
    snapshot = simplify_dom_snapshot(state.get("html") or "")
    snapshot["page"]["title"] = state.get("title") or ""
    log(
        f"DOM snapshot: {len(snapshot['elements'])} interactive elements "
        f"(truncated={snapshot['limits']['truncated']})"
    )
    log(
        "Markers: "
        f"jsgrid={snapshot['markers']['has_jsgrid_table']}, "
        f"select2={snapshot['markers']['has_select2']}, "
        f"toggleSwitch={snapshot['markers']['has_toggle_switch']}"
    )
    return {"dom_snapshot": snapshot}


def node_style_contract_if_refs(state: PogState) -> PogState:
    refs = state.get("refs") or []
    if not refs:
        log("No reference files provided: will use generic POM style.")
        return {"style_contract": None}

    log(f"Loading reference files… ({len(refs)})")
    loaded = load_ref_files(refs)

    log("Deriving Style Contract (v0.2) from refs via OpenAI…")
    style_contract = derive_style_contract_from_refs(loaded)
    log("Style Contract derived.")
    return {"style_contract": style_contract}


def node_codegen(state: PogState) -> PogState:
    out_dir = Path(state["out_dir"]).resolve()
    out_path = (out_dir / f"{state['page_name']}.cs").resolve()

    refs = state.get("refs") or []
    if refs:
        log("Generating POM with Style Contract via OpenAI…")
        code = generate_pom_with_style(
            page_name=state["page_name"],
            url=state.get("url_final") or state["url"],
            dom_snapshot=state["dom_snapshot"] or {},
            style_contract=state.get("style_contract") or {},
        )
    else:
        log("Generating generic C# POM (heuristic, no refs)…")
        code = generate_generic_pom(
            page_name=state["page_name"],
            url=state.get("url_final") or state["url"],
            snapshot=state.get("dom_snapshot") or {},
            namespace="PageObjects",
            max_elements=12,
        )

    log(f"Writing: {out_path}")
    write_text_file(out_path, code)

    return {"generated_code": code, "out_path": str(out_path)}


def node_build_gate(state: PogState) -> PogState:
    if state.get("no_build", False):
        log("Build: disabled via --no-build.")
        return {"wants_build": False, "build_ran": False}

    answer = input("Run 'dotnet build' now? (y/N): ").strip().lower()
    wants = answer in ("y", "yes")
    if not wants:
        log("Build: skipped by user.")
    return {"wants_build": wants, "build_ran": wants}


def node_build_and_repair(state: PogState) -> PogState:
    if not state.get("wants_build", False):
        return {
            "build_success": False,
            "build_returncode": 0,
            "build_stdout": "",
            "build_stderr": "",
            "repairs_used": 0,
        }

    sln_path = state.get("sln_path")
    if not sln_path:
        return {"exit_code": 2}

    log("Build: running dotnet build…")
    result = run_dotnet_build(Path(sln_path))

    if result.success:
        log("Build: SUCCESS ✅")
        return {
            "build_success": True,
            "build_returncode": result.returncode,
            "build_stdout": result.stdout,
            "build_stderr": result.stderr,
            "repairs_used": 0,
        }

    log(f"Build: FAILED (exit code {result.returncode})")
    tail_len = 2000
    if result.stdout:
        log("dotnet build stdout (tail):")
        print(result.stdout[-tail_len:])
    if result.stderr:
        log("dotnet build stderr (tail):")
        print(result.stderr[-tail_len:])

    out_path_str = state.get("out_path")
    if not out_path_str:
        return {"exit_code": 3}

    out_path = Path(out_path_str)
    max_repairs = 2
    repairs_used = 0

    for attempt in range(1, max_repairs + 1):
        repairs_used += 1
        log(f"Repair attempt {attempt}/{max_repairs}: asking OpenAI to fix compilation errors…")

        current_code = out_path.read_text(encoding="utf-8", errors="replace")
        repaired = repair_pom_from_build_errors(
            page_name=state["page_name"],
            current_code=current_code,
            build_stdout=result.stdout,
            build_stderr=result.stderr,
            style_contract=state.get("style_contract"),
        )

        if not repaired.strip():
            log("Repair returned empty output. Stopping.")
            break

        write_text_file(out_path, repaired)
        log("Repaired file written. Rebuilding…")

        result = run_dotnet_build(Path(sln_path))
        if result.success:
            log(f"Build: SUCCESS after repair {attempt}/{max_repairs} ✅")
            return {
                "build_success": True,
                "build_returncode": result.returncode,
                "build_stdout": result.stdout,
                "build_stderr": result.stderr,
                "repairs_used": repairs_used,
            }

        log(f"Build still failing after repair {attempt}/{max_repairs} (exit code {result.returncode}).")
        if result.stdout:
            log("dotnet build stdout (tail):")
            print(result.stdout[-tail_len:])
        if result.stderr:
            log("dotnet build stderr (tail):")
            print(result.stderr[-tail_len:])

    return {
        "build_success": False,
        "build_returncode": result.returncode,
        "build_stdout": result.stdout,
        "build_stderr": result.stderr,
        "repairs_used": repairs_used,
    }


def node_finalize(state: PogState) -> PogState:
    out_path = state.get("out_path")
    if out_path:
        log(f"Output: {out_path}")

    if state.get("build_ran", False):
        if state.get("build_success", False):
            log("Final: build succeeded.")
            return {"exit_code": 0}
        log(f"Final: build failed after {state.get('repairs_used', 0)} repair attempts.")
        return {"exit_code": 3}

    log("Final: build was not run.")
    return {"exit_code": 0}
