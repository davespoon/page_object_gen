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
