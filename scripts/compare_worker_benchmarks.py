"""Audit an additional worker-count run and compare it with the frozen baseline.

Does not call AI or regenerate PDFs. Failed attempts remain in timing totals.
The first-batch comparison uses the same 30 attempts; completion timing includes
retries and operator gaps in both runs. This is one observation, not a scaling
guarantee or controlled estimate of model quality.
"""

import argparse
import importlib.util
import json
import zipfile
from pathlib import Path
from statistics import median


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    baseline = Path(args.baseline).resolve()
    root = Path(args.run).resolve()
    spec = importlib.util.spec_from_file_location(
        "benchmark_audit", Path(__file__).with_name("audit_real_jobs_benchmark.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = root
    metrics, runs, inventory = module.audit()
    if not metrics["all_pdf_checks_pass"]:
        raise SystemExit("All 30 outputs must pass the audit before comparison is published")
    share = module.package(metrics, runs, inventory)
    # The original package helper includes baseline-specific narrative. Replace
    # that narrative here; retain its common data/PDF copying implementation.
    old = read(baseline / "audit.json")["metrics"]
    old_initial = read(baseline / "batch-summary.json")
    new_initial = read(root / "batch-summary.json")
    old_jobs = read(baseline / "jobs.json")
    new_jobs = read(root / "jobs.json")
    same_inputs = {
        "career_bytes": (baseline / "fixture/career.json").read_bytes()
        == (root / "fixture/career.json").read_bytes(),
        "settings_bytes": (baseline / "fixture/settings.json").read_bytes()
        == (root / "fixture/settings.json").read_bytes(),
        "job_manifest": old_jobs == new_jobs,
        "all_job_text": all(
            (baseline / j["job_path"]).read_bytes() == (root / j["job_path"]).read_bytes()
            for j in old_jobs["jobs"]
        ),
    }
    if not all(same_inputs.values()):
        raise SystemExit("Inputs changed; this is not a same-workload concurrency comparison")
    first_pass = {}
    for name, folder, summary in [
        ("baseline", baseline, old_initial),
        ("more_workers", root, new_initial),
    ]:
        # Ignore report-only failures when a committed result exists. A saved
        # first attempt distinguishes a genuine generation failure from repair.
        actual_failures = [
            r
            for r in summary["reports"]
            if r["status"] == "failed"
            and (
                (folder / "reports" / f"{r['job']['slug']}.first-attempt.json").exists()
                or not (folder / "runs" / r["job"]["slug"] / "result.json").exists()
            )
        ]
        first_pass[name] = dict(
            workers=summary["workers"],
            seconds=summary["batch_wall_s"],
            attempts=summary["attempted"],
            generated=summary["attempted"] - len(actual_failures),
            failed_attempts=[
                dict(job=r["job"]["slug"], type=r["error_type"], error=r["error"])
                for r in actual_failures
            ],
            median_all_attempt_s=median(r["task_wall_s"] for r in summary["reports"]),
        )
    comparison = dict(
        identical_inputs=same_inputs,
        first_30_attempts=first_pass,
        initial_batch_speedup=old_initial["batch_wall_s"] / new_initial["batch_wall_s"],
        observed_all_complete_speedup=old["batch_wall_s"] / metrics["batch_wall_s"],
        baseline_metrics=old,
        more_workers_metrics=metrics,
        limitation="One run per setting, same profile/jobs/model/prompt. Model and service conditions can vary. Completion wall clocks include operator pauses before retries. Not a tested maximum concurrency or a guarantee of scaling.",
    )
    (share / "worker-comparison.json").write_text(
        json.dumps(comparison, indent=2), encoding="utf-8"
    )
    report = f"""# Same 30 jobs, more concurrent workers

A worker is one in-flight resume task: start ACP, ask the existing Codex model to
select evidence, fit the selected content, export a PDF and check it. Ten workers
allow up to ten such tasks at once. Three was a conservative setting, not a limit.

| Observation | 3 workers | {metrics["workers"]} workers |
|---|---:|---:|
| First 30 attempts | {old_initial["batch_wall_s"]:.2f}s | {new_initial["batch_wall_s"]:.2f}s |
| Generated on first attempt | {first_pass["baseline"]["generated"]}/30 | {first_pass["more_workers"]["generated"]}/30 |
| All 30 complete, including retries/operator pauses | {old["batch_wall_s"]:.2f}s | {metrics["batch_wall_s"]:.2f}s |
| Median per job, all its attempts included | {old["median_task_s"]:.2f}s | {metrics["median_task_s"]:.2f}s |
| Total inference attempts | {old["inference_attempts"]} | {metrics["inference_attempts"]} |
| Final PDF content/geometry checks | 30/30 | 30/30 |

The first 30 attempts ran **{comparison["initial_batch_speedup"]:.2f}x faster as a batch**.
More concurrency improved throughput; it did not make an individual model reply
ten times faster. All inputs were byte-identical and model metadata stayed
gpt-6-sol/medium via codex-acp 2.2.2. Actual selections can vary across calls.

The original retry was a schema-reference error: a decision referenced a
requirement ID absent from that response's requirement dictionary. Validation
rejected it rather than silently accepting the broken mapping.

The new run's actual failed attempts are listed in worker-comparison.json.
It includes a requirement-reference validation failure and an ACP ProcessLookupError
after prompt completion. The latter is consistent with a local subprocess
shutdown race; the exact call site is unconfirmed because no traceback was saved.
It is not evidence of a service rate limit. Separate Windows extended-path
reporting errors did not require new inference; their existing PDFs were audited.

All final PDFs preserve approved fictional source wording, summaries and skills;
they are single-page, extractable, ordered and inside the page margins. Same
five-job relevance rubric: {metrics["independent_rubric"]["themes_with_direct_work_evidence"]}/25 themes
have direct work evidence. That is not an ATS, hiring or full-qualification score.
Skills 95% last-line fill met in {metrics["skills_fill_target_met"]}/30 outputs;
fill warnings are retained. The profile remains entirely fictional; no private
candidate data is included.

One run per setting cannot establish a maximum or ideal concurrency. Higher
settings can be tested, but these results do not prove they will scale linearly.
Use the first-attempt batch timing for the clearest concurrency comparison;
completion timing includes different operator retry pauses in each experiment.

Files: resumes/, job_posts/, selections/, previews/, results.csv, results.json,
fictional-master.yaml, job-sources.json and worker-comparison.json.
"""
    (share / "README.md").write_text(report, encoding="utf-8")
    (root / "WORKER_COMPARISON.md").write_text(report, encoding="utf-8")
    archive = root / f"Sharp - 30 jobs - {metrics['workers']} workers.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for p in share.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(share))
    print(
        json.dumps(
            {
                "speedup_first_batch": comparison["initial_batch_speedup"],
                "old_complete_s": old["batch_wall_s"],
                "new_complete_s": metrics["batch_wall_s"],
                "archive": str(archive),
            }
        )
    )


if __name__ == "__main__":
    main()
