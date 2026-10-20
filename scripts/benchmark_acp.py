"""Opt-in real Codex ACP selection and PDF benchmark, using an existing login.

No CLI installation, credential copying, or paid API key is performed here.
Supply an installed ACP entrypoint and existing CODEX_PATH explicitly.
"""

import argparse
import json
import os
from importlib.resources import files
from pathlib import Path
from time import perf_counter

import yaml

from sharp.adapters.files import save
from sharp.adapters.providers import ACPChooser
from sharp.contracts import Career, CreateRequest, Settings
from sharp.service import summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True, help="Installed codex-acp JS entrypoint")
    parser.add_argument("--codex", required=True, help="Existing native Codex executable")
    parser.add_argument("--node", default="node")
    parser.add_argument("--output", default="outputs/acp-live")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--model", help="Optional override; otherwise existing Codex default")
    parser.add_argument("--reasoning", choices=["low", "medium", "high"])
    args = parser.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    workspace = root / "agent-workspace"
    workspace.mkdir(exist_ok=True)
    os.environ["CODEX_PATH"] = str(Path(args.codex).resolve())
    os.environ["INITIAL_AGENT_MODE"] = "read-only"
    config = {"notify": [], "mcp_servers": {}}
    if args.model:
        config["model"] = args.model
    if args.reasoning:
        config["model_reasoning_effort"] = args.reasoning
    os.environ["CODEX_CONFIG"] = json.dumps(config)
    career = Career.model_validate(
        yaml.safe_load(
            files("sharp").joinpath("defaults/career.example.yaml").read_text(encoding="utf-8")
        )
    )
    # Independent relevant and irrelevant evidence makes selection nontrivial.
    career.projects.append({"x_id": "art_project", "name": "Community art event"})
    from sharp.contracts import Bullet

    career.x_resume.bullets.append(
        Bullet(
            id="art_event",
            owner_id="art_project",
            text="Coordinated a community watercolor exhibition and arranged artwork display space.",
            approval="approved",
            evidence_ids=["example_account"],
        )
    )
    save(root / "career.json", career)
    save(root / "settings.local.yaml", Settings())
    job = """Company: Example Technology
Role: Software Engineer - Python Backend
Build maintainable Python backend services and REST APIs. Work with SQL data imports,
validation, automated regression tests, Git, and operations stakeholders. Deliver reliable
software from ambiguous requirements. Documentation search experience is useful.
Prioritize directly relevant engineering evidence. Art event coordination is not relevant.
"""
    (root / "job.txt").write_text(job, encoding="utf-8")
    chooser = ACPChooser(
        args.node, [str(Path(args.adapter).resolve())], cwd=str(workspace), timeout=args.timeout
    )
    request = CreateRequest(
        career_path=str(root / "career.json"),
        settings_path=str(root / "settings.local.yaml"),
        output_dir=str(root / "run"),
        title="Python Backend Engineer",
        job=job,
    )
    start = perf_counter()
    try:
        # Same public workflow; only provider is supplied as an object at composition.
        from sharp.adapters.pdf import PdfRenderer
        from sharp.workflow import create

        result = create(request, chooser=chooser, renderer=PdfRenderer())
        wall = perf_counter() - start
        selection = json.loads((root / "run/selection.json").read_text(encoding="utf-8"))
        ids = [d["candidate_id"] for d in selection["ranked"]]
        checks = {
            "engineering_selected": "example_delivery" in ids and "example_validation" in ids,
            "irrelevant_art_omitted": "art_event" not in ids,
            "one_page": result.layout.pages == 1,
        }
        report = {
            "status": "completed",
            "python": os.sys.executable,
            "adapter": str(Path(args.adapter).resolve()),
            "existing_codex": os.environ["CODEX_PATH"],
            "configured_model": args.model or "existing Codex default",
            "configured_reasoning": args.reasoning or "existing Codex default",
            "end_to_end_wall_s": wall,
            "timings": result.timings,
            "acp_timings": chooser.timings,
            "acp_session": chooser.session_metadata,
            "quality_checks": checks,
            "selection": selection,
            "result": summarize(result).model_dump(),
        }
        save(root / "report.json", report)
        print(
            json.dumps(
                {k: v for k, v in report.items() if k not in ("selection", "result")}, indent=2
            ),
            flush=True,
        )
        if not all(checks.values()):
            raise SystemExit("Real selection failed quality checks; see report.json")
    except Exception as exc:
        save(
            root / "failure.json",
            {
                "status": "failed",
                "elapsed_s": perf_counter() - start,
                "error_type": type(exc).__name__,
                "message": str(exc),
            },
        )
        raise


if __name__ == "__main__":
    main()
