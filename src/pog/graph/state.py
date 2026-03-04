from __future__ import annotations

from typing import Any, Optional, TypedDict


class PogState(TypedDict, total=False):
    # Inputs
    url: str
    page_name: str
    out_dir: str
    refs: Optional[list[str]]
    no_build: bool

    # Derived
    sln_path: Optional[str]
    out_path: Optional[str]

    # Capture artifacts
    url_final: Optional[str]
    title: Optional[str]
    html: Optional[str]
    dom_snapshot: Optional[dict[str, Any]]

    # Refs + style contract
    style_contract: Optional[dict[str, Any]]

    # Code
    generated_code: Optional[str]

    # Build/repair
    build_ran: bool
    build_success: bool
    build_returncode: int
    build_stdout: str
    build_stderr: str
    repairs_used: int

    # Control
    wants_build: bool
    exit_code: int

    # Run metadata + debug trace
    run_id: str
    trace: list[dict[str, Any]]
