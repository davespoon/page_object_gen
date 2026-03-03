from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

STYLE_CONTRACT_V0_2_DESCRIPTION = """
You must output a single JSON object matching Style Contract schema v0.2.

Decision object shape:
  { "value": <any>, "confidence": <0..1>, "evidence": ["short", ...] }

All decision fields must be decision objects. If unknown, value=null, low confidence, include evidence.

Top-level required keys:
- schema_version: "0.2"
- meta
- strictness
- csharp
- runtime_abstractions
- behavioral_conventions
- codegen_limits

Return JSON only. No markdown. No commentary.
""".strip()


@dataclass(frozen=True)
class StyleContract:
    data: dict[str, Any]


def _is_decision(obj: Any) -> bool:
    return (
            isinstance(obj, dict)
            and "value" in obj
            and "confidence" in obj
            and "evidence" in obj
            and isinstance(obj["confidence"], (int, float))
            and 0.0 <= float(obj["confidence"]) <= 1.0
            and isinstance(obj["evidence"], list)
    )


def _wrap_decision(value: Any, *, confidence: float = 0.35, evidence: str = "Auto-wrapped by validator") -> dict:
    return {"value": value, "confidence": confidence, "evidence": [evidence]}


def _normalize_decisions(obj: Any) -> Any:
    """
    Walk the JSON tree and ensure that common decision fields are decision objects.
    We normalize aggressively but safely:
      - If we find an object that looks like a decision -> keep it
      - If we find a dict that is NOT a decision -> recurse
      - Scalars/lists are left as-is unless we know they are a decision field at a known path
    """
    if isinstance(obj, list):
        return [_normalize_decisions(x) for x in obj]
    if isinstance(obj, dict):
        if _is_decision(obj):
            # normalize nested under decision.value too, in case value is complex
            obj["value"] = _normalize_decisions(obj["value"])
            return obj
        return {k: _normalize_decisions(v) for k, v in obj.items()}
    return obj


def _ensure_path_decision(root: dict[str, Any], path: list[str]) -> None:
    """
    Ensure root[path...] is a decision object. If missing, create as null decision.
    If present but not a decision, wrap it.
    """
    cur: Any = root
    for key in path[:-1]:
        if not isinstance(cur, dict):
            return
        cur = cur.setdefault(key, {})
    if not isinstance(cur, dict):
        return
    leaf = path[-1]
    if leaf not in cur:
        cur[leaf] = _wrap_decision(None, confidence=0.2, evidence="Missing in model output; defaulted to null")
        return
    if not _is_decision(cur[leaf]):
        cur[leaf] = _wrap_decision(cur[leaf], confidence=0.3, evidence="Model returned non-decision; wrapped")


def normalize_style_contract_v0_2(data: dict[str, Any]) -> dict[str, Any]:
    data = _normalize_decisions(data)

    # Ensure required top-level keys exist
    data.setdefault("schema_version", "0.2")
    data.setdefault("meta", {})
    data.setdefault("strictness", _wrap_decision("prefer_refs", confidence=0.4, evidence="Defaulted by validator"))
    data.setdefault("csharp", {})
    data.setdefault("runtime_abstractions", {})
    data.setdefault("behavioral_conventions", {})
    data.setdefault("codegen_limits", {})

    # Ensure critical decision paths exist and are decision objects
    required_decision_paths = [
        ["strictness"],
        ["csharp", "namespace"],
        ["runtime_abstractions", "mode"],
    ]
    for p in required_decision_paths:
        _ensure_path_decision(data, p)

    return data


def validate_style_contract_v0_2(raw: str) -> StyleContract:
    try:
        data = json.loads(raw)
    except Exception as e:
        raise ValueError(f"Style contract is not valid JSON: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("Style contract must be a JSON object")

    data = normalize_style_contract_v0_2(data)

    if data.get("schema_version") != "0.2":
        raise ValueError("Style contract schema_version must be '0.2'")

    required_top = [
        "meta",
        "strictness",
        "csharp",
        "runtime_abstractions",
        "behavioral_conventions",
        "codegen_limits",
    ]
    for k in required_top:
        if k not in data:
            raise ValueError(f"Style contract missing required key: {k}")

    if not _is_decision(data["strictness"]):
        raise ValueError("strictness must be a decision object {value, confidence, evidence}")

    if not _is_decision(data.get("csharp", {}).get("namespace")):
        raise ValueError("csharp.namespace must be a decision object")

    if not _is_decision(data.get("runtime_abstractions", {}).get("mode")):
        raise ValueError("runtime_abstractions.mode must be a decision object")

    return StyleContract(data=data)
