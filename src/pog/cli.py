from __future__ import annotations

import argparse
from pathlib import Path

from .tools.sln_finder import find_nearest_sln
from .utils.logging import log


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pog", description="Generate C# Page Object Model from a URL.")
    sub = p.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate a C# Page Object file from the given URL.")
    gen.add_argument("url", help="Public URL to open and inspect.")
    gen.add_argument("page_name", help="C# class name for the generated page object (e.g., CheckoutPage).")
    gen.add_argument(
        "--refs",
        nargs="*",
        default=None,
        help="Optional reference .cs files to infer style. If omitted, generates a generic POM.",
    )
    gen.add_argument(
        "--no-build",
        action="store_true",
        help="Skip build prompt and do not run dotnet build.",
    )
    return p


def cmd_generate(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    log(f"Working directory: {cwd}")

    sln = find_nearest_sln(cwd)
    if sln is None:
        log("ERROR: No .sln found in current or parent directories.")
        log("Run `pog` from within a repo containing a .sln.")
        return 2

    log(f"Found solution: {sln}")
    log(f"Requested generation: url={args.url!r}, page_name={args.page_name!r}")

    if args.refs:
        log(f"Reference files provided ({len(args.refs)}): {', '.join(args.refs)}")
    else:
        log("No reference files provided: will generate a generic POM style (later slice).")

    # Slice 2: Capture + bounded DOM snapshot
    from .tools.selenium_capture import capture_page
    from .tools.dom_simplify import simplify_dom_snapshot

    log("Launching browser (headless) and navigating…")
    captured = capture_page(args.url, headless=True)
    log(f"Navigation complete. Final URL: {captured.url_final}")
    log(f"Page title: {captured.title!r}")
    log(f"Captured HTML size: {len(captured.html)} chars")

    log("Building bounded DOM snapshot…")
    snapshot = simplify_dom_snapshot(captured.html)
    snapshot["page"]["title"] = captured.title

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

    # Slice 3: Generate + write a generic C# POM (no LLM yet)
    from .codegen.generic_pom import generate_generic_pom
    from .tools.file_writer import write_text_file

    out_path = (Path.cwd() / f"{args.page_name}.cs").resolve()

    log("Generating generic C# POM (heuristic, no refs-based style yet)…")
    code = generate_generic_pom(
        page_name=args.page_name,
        url=captured.url_final,
        snapshot=snapshot,
        namespace="PageObjects",
        max_elements=12,
    )

    log(f"Writing: {out_path}")
    write_text_file(out_path, code)

    if args.no_build:
        log("Build: disabled via --no-build.")
    else:
        log("Build: interactive prompt will be added in the next slice.")

    log("Slice 3 complete: C# file generated.")
    return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        return cmd_generate(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
