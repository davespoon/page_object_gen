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

    if args.no_build:
        log("Build: disabled via --no-build (later slice will skip build entirely).")
    else:
        log("Build: interactive prompt will be added in a later slice.")

    log("Skeleton complete (no code generated yet).")
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
