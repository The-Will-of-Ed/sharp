"""Actual Codex ACP selection on a fixed fictional career and 30 real jobs.

Separate from production code. Reuses an existing Codex installation and login;
no separate API key or new CLI installation is needed.
Includes subprocess startup, selection, deterministic fit, export and validation
in each task's measured duration; excludes job downloading and human review.
"""

import argparse
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import median
from time import perf_counter

from sharp.adapters.files import save
from sharp.adapters.pdf import PdfRenderer
from sharp.adapters.providers import ACPChooser
from sharp.contracts import Career, CreateRequest
from sharp.workflow import create


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--codex", required=True)
    parser.add_argument("--node", default="node")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=150)
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    os.environ["CODEX_PATH"] = str(Path(args.codex).resolve())
    os.environ["INITIAL_AGENT_MODE"] = "read-only"
    # Suppress unrelated integrations and inherited project instructions. The
    # selector receives the entire allowed career and job in its typed prompt.
    os.environ["CODEX_CONFIG"] = json.dumps(
        {"notify": [], "mcp_servers": {}, "project_doc_max_bytes": 0}
    )
    workspace = root / "agent-workspace"
    workspace.mkdir(exist_ok=True)
    career_path = root / "fixture/career.json"
    settings_path = root / "fixture/settings.json"
    career_hash = hashlib.sha256(career_path.read_bytes()).hexdigest()
    career = Career.model_validate_json(career_path.read_text(encoding="utf-8"))
    approved = {b.id: b for b in career.x_resume.bullets}
    jobs = json.loads((root / "jobs.json").read_text(encoding="utf-8"))["jobs"]
    if args.only:
        jobs = [j for j in jobs if j["slug"] in args.only]
    benchmark_start = perf_counter()
    reports = []

    def run(job):
        slug = job["slug"]
        start = perf_counter()
        chooser = ACPChooser(
            args.node, [str(Path(args.adapter).resolve())], cwd=str(workspace), timeout=args.timeout
        )
        request = CreateRequest(
            career_path=str(career_path),
            settings_path=str(settings_path),
            output_dir=str(root / "runs" / slug),
            title=f"{job['role']} - {job['company']}",
            job=(root / job["job_path"]).read_text(encoding="utf-8"),
        )
        print(json.dumps({"event": "started", "job": slug}), flush=True)
        try:
            result = create(request, chooser=chooser, renderer=PdfRenderer())
            task_wall = perf_counter() - start
            out = Path(result.output_dir)
            plan = json.loads((out / "selection.json").read_text(encoding="utf-8"))
            actual_bullets = [
                p for p in result.layout.placed if p.block.kind in ("work_bullet", "project_bullet")
            ]
            checks = {
                "one_page": result.layout.pages == 1,
                "nonempty_evidence": len(actual_bullets) >= 4,
                "approved_source_text_only": all(
                    p.block.id in approved and p.block.text == approved[p.block.id].text
                    for p in actual_bullets
                ),
                "extracted_text_and_order": all(
                    a.checks.get("text") == "passed" and a.checks.get("reading_order")
                    for a in result.artifacts
                    if a.format == "pdf"
                ),
                "no_layout_issues": not result.layout.issues,
                "education_present": sum(
                    p.block.kind == "education" for p in result.layout.placed
                ) == len(career.education),
                "clean_presentation": not any(
                    token in p.block.text.lower()
                    for p in result.layout.placed
                    for token in ("fictional", "example.com", "benchmark")
                ),
            }
            report = dict(
                status="completed",
                job=job,
                task_wall_s=task_wall,
                timings=result.timings,
                acp_timings=chooser.timings,
                acp_session=chooser.session_metadata,
                selected_bullet_ids=[p.block.id for p in actual_bullets],
                ranked_bullet_ids=[r["candidate_id"] for r in plan["ranked"]],
                final_bullets=[
                    dict(id=p.block.id, text=p.block.text, kind=p.block.kind)
                    for p in actual_bullets
                ],
                selection=plan,
                checks=checks,
                page_fill=result.layout.page_fill,
                skills_line_fill=result.layout.skills_line_fill,
                artifacts=[f"runs/{slug}/{Path(a.path).name}" for a in result.artifacts],
            )
        except Exception as exc:
            report = dict(
                status="failed",
                job=job,
                task_wall_s=perf_counter() - start,
                error_type=type(exc).__name__,
                error=str(exc),
                acp_timings=chooser.timings,
                acp_session=chooser.session_metadata,
            )
        save(root / "reports" / f"{slug}.json", report)
        print(
            json.dumps(
                {
                    "event": report["status"],
                    "job": slug,
                    "seconds": round(report["task_wall_s"], 3),
                    "checks": report.get("checks"),
                    "error": report.get("error"),
                }
            ),
            flush=True,
        )
        return report

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run, job) for job in jobs]
        for future in as_completed(futures):
            reports.append(future.result())
    wall = perf_counter() - benchmark_start
    completed = [r for r in reports if r["status"] == "completed"]
    durations = sorted(r["task_wall_s"] for r in completed)
    summary = dict(
        attempted=len(reports),
        completed=len(completed),
        failed=len(reports) - len(completed),
        workers=args.workers,
        batch_wall_s=wall,
        sum_task_wall_s=sum(r["task_wall_s"] for r in reports),
        median_task_s=median(durations) if durations else None,
        min_task_s=min(durations) if durations else None,
        max_task_s=max(durations) if durations else None,
        median_selection_s=median(r["timings"]["selection"] for r in completed)
        if completed
        else None,
        all_checks_pass=all(all(r["checks"].values()) for r in completed)
        and len(completed) == len(jobs),
        unique_final_bullet_sets=len({tuple(sorted(r["selected_bullet_ids"])) for r in completed}),
        career_hash_before=career_hash,
        career_hash_after=hashlib.sha256(career_path.read_bytes()).hexdigest(),
        timing_scope="Wall time per task includes career load, ACP process/session, actual model selection, fit, PDF export, validation and result serialization. Batch wall time uses concurrent workers. Excludes collection/profile authoring/review and interpreter startup.",
        cost_note="Existing authenticated Codex subscription; no separate API key or metered API charge measured. Subscription cost and usage limits still apply. This is not a free-inference claim.",
        manual_comparison=dict(
            assumed_minutes_per_resume=20,
            source="Explicit planning assumption, not a measured human study",
            assumed_total_minutes=20 * len(jobs),
            actual_batch_minutes=wall / 60,
            ratio_assumed_manual_to_batch=(1200 * len(jobs)) / wall,
        ),
        reports=sorted(reports, key=lambda r: r["job"]["slug"]),
    )
    name = "batch-summary.json" if not args.only else "subset-summary.json"
    save(root / name, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "reports"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
