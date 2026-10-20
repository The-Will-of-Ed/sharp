"""Thin command line. The same service functions back MCP."""

import argparse
import json
import sys
from pathlib import Path

import yaml

from .contracts import Career, CreateRequest, ProposedChanges, Settings


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="sharp",
        description="Evidence-backed resumes. PDF first; editable exports only when requested.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser(
        "init", help="Create a local workspace; never overwrite existing settings"
    )
    init.add_argument("directory", nargs="?", default=".")
    demo = commands.add_parser("demo", help="Render synthetic example data without any AI")
    demo.add_argument("--output", default="outputs/demo")
    schema = commands.add_parser("contracts", help="Print every public input/output schema")
    schema.add_argument("name", nargs="?")
    intake = commands.add_parser(
        "intake",
        help="Extract source text for your agent; does not invent career claims",
    )
    intake.add_argument("paths", nargs="+")
    intake.add_argument("--output", required=True)
    migrate = commands.add_parser(
        "migrate", help="Import an old career file into a NEW proposed master"
    )
    migrate.add_argument("source")
    migrate.add_argument("destination")
    context = commands.add_parser(
        "context", help="Prepare a compact choice request for your current agent"
    )
    context.add_argument("--career", default="master.yaml")
    context.add_argument("--settings", default="settings.local.yaml")
    context.add_argument("--job", default="")
    context.add_argument("--job-file")
    create = commands.add_parser(
        "create",
        help="Generate from a common request and optional provider configuration",
    )
    create.add_argument("--request", required=True)
    create.add_argument(
        "--provider",
        help="JSON/YAML config: kind=litellm or acp; credentials stay in environment",
    )
    edit = commands.add_parser("edit", help="Refit an existing run; never calls AI")
    edit.add_argument("directory")
    edit.add_argument(
        "--changes",
        required=True,
        help='JSON dotted settings changes, e.g. {"styles.body.size":9.5}',
    )
    export = commands.add_parser(
        "export", help="Export a saved layout without re-selection or refitting"
    )
    export.add_argument("directory")
    export.add_argument("--format", choices=["pdf", "pptx", "docx"], required=True)
    inspect = commands.add_parser(
        "inspect", help="Inspect selection, geometry, remaining space and timings"
    )
    inspect.add_argument("directory")
    approve = commands.add_parser(
        "approve",
        help="Apply an explicitly approved proposal with a matching career hash",
    )
    approve.add_argument("career")
    approve.add_argument("proposal")
    serve = commands.add_parser("mcp", help="Start a workspace-scoped stdio MCP server")
    serve.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    from . import service
    from .adapters.files import import_material, load, migrate_legacy, save

    try:
        if args.command == "init":
            result = service.initialize(args.directory)
        elif args.command == "contracts":
            all_contracts = service.contracts()
            result = all_contracts[args.name] if args.name else all_contracts
        elif args.command == "intake":
            result = import_material(args.paths)
            save(args.output, result)
            result = {"path": str(Path(args.output).resolve()), "sources": len(result)}
        elif args.command == "migrate":
            if Path(args.destination).exists():
                raise ValueError("Destination exists; migration never overwrites files")
            result = migrate_legacy(yaml.safe_load(Path(args.source).read_text(encoding="utf-8")))
            save(args.destination, result)
            result = {
                "path": str(Path(args.destination).resolve()),
                "review": "Imported bullets are proposed and unrated; review before approving",
            }
        elif args.command == "context":
            from .adapters.jobs import job_text
            from .career import choice_input

            text = Path(args.job_file).read_text(encoding="utf-8") if args.job_file else args.job
            result = choice_input(
                load(args.career, Career),
                load(args.settings, Settings),
                job_text(text, Path(args.settings).parent / ".cache/jobs"),
            ).model_dump(by_alias=True)
        elif args.command == "create":
            provider = (
                yaml.safe_load(Path(args.provider).read_text(encoding="utf-8"))
                if args.provider
                else None
            )
            result = service.summarize(
                service.generate(load(args.request, CreateRequest), provider=provider)
            ).model_dump()
        elif args.command == "edit":
            result = service.summarize(
                service.refit(args.directory, json.loads(args.changes))
            ).model_dump()
        elif args.command == "export":
            result = service.export_saved(args.directory, args.format).model_dump()
        elif args.command == "inspect":
            result = service.inspect_run(args.directory)
        elif args.command == "approve":
            result = service.apply_career(args.career, load(args.proposal, ProposedChanges))
        elif args.command == "demo":
            from importlib.resources import files

            root = Path(args.output).resolve()
            root.mkdir(parents=True, exist_ok=True)
            for source, name in [
                ("career.example.yaml", "career.json"),
                ("selection.example.yaml", "selection.json"),
            ]:
                save(
                    root / name,
                    yaml.safe_load(
                        files("sharp").joinpath("defaults/" + source).read_text(encoding="utf-8")
                    ),
                )
            save(root / "settings.local.yaml", Settings())
            result = service.summarize(
                service.generate(
                    CreateRequest(
                        career_path=str(root / "career.json"),
                        settings_path=str(root / "settings.local.yaml"),
                        selection_path=str(root / "selection.json"),
                        output_dir=str(root),
                        title="Software Engineer",
                    )
                )
            ).model_dump()
        else:
            from .mcp_server import serve

            serve(args.root)
            return
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, KeyError) as exc:
        print(f"Sharp: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
