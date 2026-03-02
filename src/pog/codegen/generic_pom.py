from __future__ import annotations

import re
from typing import Any

_CSHARP_KEYWORDS = {
    "class", "namespace", "public", "private", "protected", "internal", "void", "string",
    "int", "bool", "new", "return", "base", "this", "null", "true", "false",
}


def _to_identifier(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^a-zA-Z0-9_]+", " ", name)
    parts = [p for p in name.split() if p]
    if not parts:
        return "Element"
    s = parts[0].lower() + "".join(p[:1].upper() + p[1:] for p in parts[1:])
    s = re.sub(r"[^a-zA-Z0-9_]", "", s)
    if not s or s[0].isdigit():
        s = "e" + s
    if s in _CSHARP_KEYWORDS:
        s = s + "Element"
    return s


def _pick_locator(e: dict) -> tuple[str, str]:
    """
    Returns (byKind, selectorLiteral) where byKind is one of: Id, Css, XPath.
    selectorLiteral is a C# string literal content (not quoted).
    """
    if e.get("id"):
        return ("Id", e["id"])
    if e.get("data_testid"):
        # CSS attribute selector
        return ("Css", f"[data-testid='{e['data_testid']}']")
    if e.get("name"):
        return ("Css", f"[name='{e['name']}']")
    if e.get("aria_label"):
        # XPath by aria-label
        v = e["aria_label"].replace("'", "\\'")
        return ("XPath", f"//*[@aria-label='{v}']")
    # Fallbacks by tag + text for buttons/links
    tag = (e.get("tag") or "").lower()
    text = (e.get("text") or "").strip()
    if tag in ("button", "a") and text:
        t = text.replace("'", "\\'")
        return ("XPath", f"//{tag}[normalize-space()='{t}']")
    # Last resort: tag only (weak)
    if tag:
        return ("XPath", f"//{tag}")
    return ("XPath", "//*")


def _escape_csharp_string(s: str) -> str:
    # Use verbatim string for simplicity when possible
    if "\n" in s or "\r" in s:
        s = s.replace('"', '""')
        return f'@"{s}"'
    # normal string
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return f"\"{s}\""


def generate_generic_pom(
        *,
        page_name: str,
        url: str,
        snapshot: dict[str, Any],
        namespace: str = "PageObjects",
        max_elements: int = 12,
) -> str:
    elements = snapshot.get("elements") or []
    picked = []

    # Prefer: inputs/select/textarea first, then buttons, then links
    priority = {"input": 1, "select": 2, "textarea": 3, "button": 4, "a": 5}
    elements_sorted = sorted(elements, key=lambda e: priority.get((e.get("tag") or "").lower(), 99))

    seen_locators = set()
    for e in elements_sorted:
        if len(picked) >= max_elements:
            break
        by_kind, selector = _pick_locator(e)
        key = (by_kind, selector)
        if key in seen_locators:
            continue
        seen_locators.add(key)
        picked.append((e, by_kind, selector))

    # Build members
    locator_lines = []
    method_lines = []

    for i, (e, by_kind, selector) in enumerate(picked, start=1):
        tag = (e.get("tag") or "").lower()
        raw_name = e.get("id") or e.get("name") or e.get("data_testid") or e.get("aria_label") or e.get(
            "text") or f"{tag}{i}"
        ident = _to_identifier(raw_name)

        loc_field = f"_{ident}Locator"
        loc = _escape_csharp_string(selector)

        if by_kind == "Id":
            locator_lines.append(f"    private readonly By {loc_field} = By.Id({loc});")
        elif by_kind == "Css":
            locator_lines.append(f"    private readonly By {loc_field} = By.CssSelector({loc});")
        else:
            locator_lines.append(f"    private readonly By {loc_field} = By.XPath({loc});")

        # Methods
        if tag in ("input", "textarea"):
            mname = ident[:1].upper() + ident[1:]
            method_lines.append(
                f"""\
    public {page_name} Enter{mname}(string value)
    {{
        var el = Find({loc_field});
        el.Clear();
        el.SendKeys(value);
        return this;
    }}"""
            )
        elif tag == "select":
            mname = ident[:1].upper() + ident[1:]
            method_lines.append(
                f"""\
    public {page_name} Select{mname}(string text)
    {{
        var el = Find({loc_field});
        var select = new SelectElement(el);
        select.SelectByText(text);
        return this;
    }}"""
            )
        elif tag in ("button", "a"):
            mname = ident[:1].upper() + ident[1:]
            method_lines.append(
                f"""\
    public {page_name} Click{mname}()
    {{
        Find({loc_field}).Click();
        WaitForReady();
        return this;
    }}"""
            )

    locators_block = "\n".join(
        locator_lines) if locator_lines else "    // No interactive elements detected in snapshot."
    methods_block = "\n\n".join(
        method_lines) if method_lines else "    // No action methods generated (snapshot empty)."

    title = (snapshot.get("page") or {}).get("title") or ""
    title_comment = f"// Title: {title}\n" if title else ""

    return f"""\
using System;
using OpenQA.Selenium;
using OpenQA.Selenium.Support.UI;

namespace {namespace};

{title_comment}public class {page_name}
{{
    private readonly IWebDriver _driver;
    private readonly WebDriverWait _wait;

    public {page_name}(IWebDriver driver, TimeSpan? timeout = null)
    {{
        _driver = driver;
        _wait = new WebDriverWait(_driver, timeout ?? TimeSpan.FromSeconds(10));
    }}

    public {page_name} Open()
    {{
        _driver.Navigate().GoToUrl({_escape_csharp_string(url)});
        WaitForReady();
        return this;
    }}

{locators_block}

    public bool IsLoaded()
    {{
        // Best-effort: page is "loaded" if document is complete.
        try
        {{
            return ((IJavaScriptExecutor)_driver).ExecuteScript("return document.readyState")?.ToString() == "complete";
        }}
        catch
        {{
            return true;
        }}
    }}

{methods_block}

    private IWebElement Find(By by)
    {{
        return _wait.Until(d => d.FindElement(by));
    }}

    private void WaitForReady()
    {{
        _wait.Until(d =>
        {{
            try
            {{
                return ((IJavaScriptExecutor)d).ExecuteScript("return document.readyState")?.ToString() == "complete";
            }}
            catch
            {{
                return true;
            }}
        }});
    }}
}}
"""
