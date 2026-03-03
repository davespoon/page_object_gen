from __future__ import annotations

import argparse
from pathlib import Path


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
    from .graph.run import run_generate_graph

    final_state = run_generate_graph(
        url=args.url,
        page_name=args.page_name,
        refs=args.refs if args.refs else None,
        no_build=args.no_build,
        out_dir=Path.cwd(),
    )

    return int(final_state.get("exit_code", 0))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        return cmd_generate(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
