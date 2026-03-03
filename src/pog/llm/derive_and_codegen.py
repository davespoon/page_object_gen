from __future__ import annotations

import datetime
import json
from typing import Any

from .openai_client import get_client, get_model
from .style_contract_v0_2 import STYLE_CONTRACT_V0_2_DESCRIPTION, validate_style_contract_v0_2
from ..tools.refs_loader import RefFile


def derive_style_contract_from_refs(refs: list[RefFile]) -> dict[str, Any]:
    client = get_client()
    model = get_model()

    refs_payload = [
        {"path": r.path, "truncated": r.truncated, "content": r.content}
        for r in refs
    ]

    system = (
        "You are a senior test automation engineer. "
        "You extract coding conventions and framework usage patterns from reference C# Page Objects."
    )
    user = (
        f"{STYLE_CONTRACT_V0_2_DESCRIPTION}\n\n"
        f"Reference files (JSON):\n{json.dumps(refs_payload)[:180000]}\n\n"
        f"Important: infer conventions from these files only."
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "developer", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
    )

    text = resp.choices[0].message.content or ""

    try:
        contract = validate_style_contract_v0_2(text).data
    except Exception as e:
        # Print a short tail to diagnose formatting without dumping everything
        tail = text[-2000:] if text else ""
        raise ValueError(f"Style contract validation failed: {e}\n--- model output tail ---\n{tail}") from e
    if "meta" in contract and isinstance(contract["meta"], dict):
        contract["meta"].setdefault("created_utc", datetime.datetime.utcnow().isoformat() + "Z")
    return contract


def generate_pom_with_style(
        *,
        page_name: str,
        url: str,
        dom_snapshot: dict[str, Any],
        style_contract: dict[str, Any],
) -> str:
    client = get_client()
    model = get_model()

    system = (
        "You generate C# Page Object Model code for Selenium-based UI tests. "
        "Follow the provided Style Contract strictly when confident; "
        "when confidence is low, use safe defaults consistent with the contract."
    )

    user = (
            "Generate a SINGLE C# file for a Page Object.\n"
            "Rules:\n"
            "- Output ONLY C# code. No markdown. No explanation.\n"
            "- The class name must be exactly: " + page_name + "\n"
                                                               "- Use the DOM snapshot to choose locators for interactive elements.\n"
                                                               "- Prefer stable attributes in this order: id, data-testid, name, aria-label, stable xpath.\n"
                                                               "- Keep it small: pick a handful of important elements and actions; avoid generating 100 methods.\n"
                                                               "- Use the Style Contract to match namespace/base page/wrappers/grids/fluent methods/JS strategies.\n\n"
                                                               "Inputs:\n"
                                                               f"URL (final): {url}\n\n"
                                                               f"DOM SNAPSHOT JSON:\n{json.dumps(dom_snapshot)[:180000]}\n\n"
                                                               f"STYLE CONTRACT JSON:\n{json.dumps(style_contract)[:180000]}\n"
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "developer", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
    )
    return resp.choices[0].message.content or ""


def repair_pom_from_build_errors(
        *,
        page_name: str,
        current_code: str,
        build_stdout: str,
        build_stderr: str,
        style_contract: dict[str, Any] | None,
) -> str:
    client = get_client()
    model = get_model()

    # Keep prompt bounded (avoid huge tool output)
    def tail(s: str, n: int = 6000) -> str:
        s = s or ""
        return s if len(s) <= n else ("…[TRUNCATED]…\n" + s[-n:])

    system = (
        "You fix C# compilation errors in a generated Page Object file. "
        "Output must be a SINGLE corrected C# file. No markdown, no explanation.\n"
        "Constraints:\n"
        "- Keep the class name exactly as provided.\n"
        "- Do not remove public methods unless necessary for compilation.\n"
        "- Prefer minimal changes: add missing usings, fix types, fix syntax, adjust namespace if needed.\n"
        "- If a Style Contract is provided, follow it when possible.\n"
    )

    user = (
        f"Class name must remain exactly: {page_name}\n\n"
        "Here is the current C# file:\n"
        "----- BEGIN C# -----\n"
        f"{current_code}\n"
        "----- END C# -----\n\n"
        "dotnet build output (stdout tail):\n"
        "----- BEGIN STDOUT -----\n"
        f"{tail(build_stdout)}\n"
        "----- END STDOUT -----\n\n"
        "dotnet build output (stderr tail):\n"
        "----- BEGIN STDERR -----\n"
        f"{tail(build_stderr)}\n"
        "----- END STDERR -----\n\n"
    )

    if style_contract is not None:
        user += (
            "STYLE CONTRACT JSON (may be partial; use it as guidance):\n"
            "----- BEGIN STYLE CONTRACT -----\n"
            f"{json.dumps(style_contract)[:120000]}\n"
            "----- END STYLE CONTRACT -----\n\n"
        )

    user += "Return ONLY the corrected C# file content."

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "developer", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
    )
    return resp.choices[0].message.content or ""
