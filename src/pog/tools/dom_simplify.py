from __future__ import annotations

from bs4 import BeautifulSoup


def _trim(text: str, max_len: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def simplify_dom_snapshot(
        html: str,
        *,
        max_elements: int = 120,
        max_text_len: int = 80,
) -> dict:
    """
    Produce a bounded DOM snapshot focused on interactive elements.

    Output is intentionally small and stable:
    - interactive element list capped by max_elements
    - trimmed text/attrs
    - a few page markers useful for archetype detection
    """
    soup = BeautifulSoup(html or "", "lxml")

    # Page markers / archetype hints (generic signals)
    has_jsgrid = bool(soup.select("table.jsgrid-table, table[class*='jsgrid-table']"))
    has_select2 = bool(soup.select(".select2, .select2-container, #siteSelector"))
    has_toggle_switch = bool(soup.select(".toggle-switch"))

    elements = []
    interactive_tags = ["input", "button", "select", "textarea", "a"]

    # Collect in DOM order
    for tag in soup.find_all(interactive_tags):
        if len(elements) >= max_elements:
            break

        attrs = tag.attrs or {}
        classes = attrs.get("class") or []
        if isinstance(classes, str):
            classes = [classes]

        # Attribute extraction (bounded)
        item = {
            "tag": tag.name,
            "id": _trim(str(attrs.get("id", "")), 60),
            "name": _trim(str(attrs.get("name", "")), 60),
            "type": _trim(str(attrs.get("type", "")), 30),
            "role": _trim(str(attrs.get("role", "")), 30),
            "class": _trim(" ".join([str(c) for c in classes if c]), 120),
            "aria_label": _trim(str(attrs.get("aria-label", "")), 80),
            "data_testid": _trim(str(attrs.get("data-testid", "")), 80),
            "href": _trim(str(attrs.get("href", "")), 120),
            "placeholder": _trim(str(attrs.get("placeholder", "")), 80),
            "value": _trim(str(attrs.get("value", "")), 80),
            "disabled": bool(attrs.get("disabled") is not None),
            "text": _trim(tag.get_text(" ", strip=True), max_text_len),
        }

        # Basic filtering to reduce noise:
        # - ignore anchors with no href and no text
        # - ignore inputs with no id/name/type placeholder and no value
        if item["tag"] == "a" and not item["href"] and not item["text"]:
            continue
        if item["tag"] == "input" and not any(
                [item["id"], item["name"], item["type"], item["placeholder"], item["value"]]
        ):
            continue

        elements.append(item)

    return {
        "schema_version": "dom_snapshot_v0.1",
        "page": {
            "title": "",  # filled by caller if desired
        },
        "markers": {
            "has_jsgrid_table": has_jsgrid,
            "has_select2": has_select2,
            "has_toggle_switch": has_toggle_switch,
        },
        "elements": elements,
        "limits": {
            "max_elements": max_elements,
            "max_text_len": max_text_len,
            "truncated": len(elements) >= max_elements,
        },
    }
