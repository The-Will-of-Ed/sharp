"""CLI transport for the same typed operations exposed through MCP."""

import argparse
import json
import sys
from pathlib import Path

import yaml
from pydantic import TypeAdapter

from .operations import build_operations


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        prog="sharp", description="Evidence-backed resumes. CLI and MCP share every operation."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    catalog = build_operations(".")
    for name, operation in catalog.items():
        command = commands.add_parser(name, help=operation.__doc__)
        command.add_argument(
            "--root", default=".", help="Private workspace; all operation paths stay inside it"
        )
        command.add_argument(
            "--args", default="{}", help="JSON object, or @path to a JSON/YAML argument file"
        )
        command.add_argument(
            "--schema", action="store_true", help="Print the operation input contract"
        )
    transport = commands.add_parser("mcp", help="Start the stdio MCP transport")
    transport.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    try:
        if args.command == "mcp":
            from .mcp_server import serve

            serve(args.root)
            return
        operation = build_operations(args.root)[args.command]
        if args.schema:
            result = TypeAdapter(operation).json_schema()
        else:
            raw = args.args
            arguments = (
                yaml.safe_load(Path(raw[1:]).read_text(encoding="utf-8"))
                if raw.startswith("@")
                else json.loads(raw)
            )
            if not isinstance(arguments, dict):
                raise ValueError("Operation arguments must be an object")
            result = operation(**arguments)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Sharp: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
