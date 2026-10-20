"""Audit saved runs, preserving inference timings and reporting real limitations.

Uses an independent five-job rubric declared before seeing selections. Coverage
is coverage of supported themes, not an ATS score, qualification or hiring claim.
No AI is called here. Windows extended path prefixes are normalized only when
locating existing output files; no generation or selection is repeated.
"""

import csv
import hashlib
import json
import shutil
import textwrap
import zipfile
from datetime import datetime
from pathlib import Path
from statistics import median

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1] / "outputs/real-jobs-30"

# Separate reviewer saw postings and fixture, but no selection results.
RUBRIC = {
    "01-google-129511213234037446": [
        ("Backend services and design", ["harbor_payments", "ibm_enterprise", "pine_tracking"]),
        ("React/TypeScript delivery", ["harbor_merchant_ui", "pine_frontend", "alder_web"]),
        ("Accessibility and testing", ["harbor_accessibility", "pr_accessibility_kit"]),
        ("Design leadership", ["harbor_mentoring", "harbor_merchant_ui", "pine_roadmap"]),
        (
            "Full lifecycle and operations",
            ["harbor_delivery", "harbor_observability", "ibm_tests", "ibm_support"],
        ),
    ],
    "03-amazon-10556318": [
        ("Ingestion and data quality", ["pine_streaming", "pine_analytics", "ibm_migration"]),
        ("Distributed delivery semantics", ["pine_tracking", "harbor_event_delivery"]),
        (
            "Transformation and database performance",
            ["pine_analytics", "pine_database", "pr_feature_store"],
        ),
        (
            "AWS deployment and operations",
            ["pine_kubernetes", "pine_oncall", "harbor_observability"],
        ),
        ("Internal customers and leadership", ["pine_roadmap", "harbor_mentoring"]),
    ],
    "05-apple-200684861": [
        ("Payments and distributed guarantees", ["harbor_payments", "harbor_event_delivery"]),
        ("Java/Spring and REST/gRPC", ["harbor_payments", "ibm_enterprise", "pine_tracking"]),
        (
            "Observability and performance",
            ["harbor_observability", "pine_oncall", "harbor_api_latency", "pine_database"],
        ),
        ("Cloud-native delivery", ["pine_kubernetes", "harbor_delivery", "pine_ci"]),
        (
            "Security/privacy and influence",
            ["harbor_identity", "harbor_privacy", "harbor_mentoring"],
        ),
    ],
    "06-stripe-7557899": [
        ("SDKs and compatibility", ["harbor_sdk", "pine_contracts"]),
        ("Go and backend languages", ["pine_tracking", "ibm_enterprise", "alder_web"]),
        ("API design and developer interfaces", ["harbor_sdk", "ibm_enterprise", "pine_roadmap"]),
        (
            "Developer tooling and documentation",
            ["pine_ci", "ibm_docker", "harbor_sdk", "pr_package_checker"],
        ),
        ("Mentorship and developer support", ["harbor_mentoring", "ibm_support", "pine_roadmap"]),
    ],
    "12-figma-5790627004": [
        ("Build/test speed and CI", ["pine_ci", "ibm_tests"]),
        ("Developer tools and reproducibility", ["ibm_docker", "harbor_sdk", "pr_package_checker"]),
        (
            "Infrastructure and reliability",
            ["pine_kubernetes", "harbor_delivery", "harbor_observability"],
        ),
        ("Cross-team technical direction", ["harbor_mentoring", "pine_roadmap", "harbor_sdk"]),
        ("Integration test infrastructure", ["pine_contracts", "ibm_tests", "pine_ci"]),
    ],
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def audit():
    summary = read(ROOT / "batch-summary.json")
    inventory = read(ROOT / "fixture/inventory.json")
    jobs = read(ROOT / "jobs.json")["jobs"]
    career = read(ROOT / "fixture/career.json")
    approved = {b["id"]: b for b in career["x_resume"]["bullets"]}
    reviewed = []
    event_times = []
    for job in jobs:
        slug = job["slug"]
        raw = read(ROOT / "reports" / f"{slug}.json")
        out = ROOT / "runs" / slug
        if not (out / "result.json").exists():
            reviewed.append(raw)
            continue
        result = read(out / "result.json")
        event_times.extend(
            datetime.fromisoformat(json.loads(line)["time"])
            for line in (out / "events.jsonl").read_text(encoding="utf-8").splitlines()
        )
        plan = read(out / "selection.json")
        layout = result["layout"]
        blocks = [
            p for p in layout["placed"] if p["block"]["kind"] in ("work_bullet", "project_bullet")
        ]
        pdf = next(out.glob("*.pdf"))
        reader = PdfReader(pdf)
        text = "\n".join(p.extract_text(extraction_mode="plain") for p in reader.pages)
        compact = "".join(text.split())
        source_ok = all(p["block"]["text"] == approved[p["block"]["id"]]["text"] for p in blocks)
        all_lines = [line["text"] for p in layout["placed"] for line in p["measurement"]["lines"]]
        page = read(out / "settings.json")["page"]
        top, right, bottom, left = page["margins"]
        geometry_ok = all(
            p["x"] >= left
            and p["y"] >= top
            and p["x"] + p["width"] <= page["width"] - right + 0.01
            and p["y"] + p["measurement"]["height"] <= page["height"] - bottom + 0.01
            for p in layout["placed"]
        )
        ordered_text = ["".join(x.split()) for x in all_lines if x.strip()]
        cursor = 0
        reading_order_ok = True
        for expected in ordered_text:
            at = compact.find(expected, cursor)
            if at < 0:
                reading_order_ok = False
                break
            cursor = at + len(expected)
        checks = dict(
            one_page=len(reader.pages) == 1,
            approved_source_text_only=source_ok,
            all_text_extracts=all("".join(line.split()) in compact for line in all_lines),
            single_column_reading_order=reading_order_ok,
            inside_page_margins=geometry_ok,
            fictional_disclosure="FICTIONAL BENCHMARK" in text,
            career_unchanged=hashlib.sha256((ROOT / "fixture/career.json").read_bytes()).hexdigest()
            == inventory["career_sha256"],
            job_text_unchanged=hashlib.sha256(
                (ROOT / job["job_path"]).read_text(encoding="utf-8").encode("utf-8")
            ).hexdigest()
            == job["job_sha256"],
        )
        summary_texts = {s["text"] for s in career["x_resume"]["summaries"]}
        skills = {s["id"]: s["name"] for s in career["x_resume"]["skills"]}
        checks["approved_summary_and_skills_only"] = all(
            p["block"]["text"] in summary_texts
            if p["block"]["kind"] == "summary"
            else p["block"]["text"] == ", ".join(skills[i] for i in p["block"]["source_ids"])
            for p in layout["placed"]
            if p["block"]["kind"] in ("summary", "skills")
        )
        prior = ROOT / "reports" / f"{slug}.first-attempt.json"
        prior_files = ([prior] if prior.exists() else []) + list(
            (ROOT / "reports").glob(f"{slug}.failed-attempt-*.json")
        )
        attempt_seconds = sum(read(p)["task_wall_s"] for p in prior_files)
        selected = [p["block"]["id"] for p in blocks]
        themes = []
        for theme, alternatives in RUBRIC.get(slug, []):
            hits = sorted(set(selected) & set(alternatives))
            direct = [i for i in hits if not i.startswith("pr_")]
            themes.append(
                dict(
                    theme=theme,
                    score=2 if direct else 1 if hits else 0,
                    matching_ids=hits,
                    alternatives=alternatives,
                )
            )
        report = dict(
            status="completed",
            job=job,
            task_wall_s=raw["task_wall_s"] + attempt_seconds,
            successful_attempt_s=raw["task_wall_s"],
            prior_failed_attempt_s=attempt_seconds,
            prior_failed_attempts=len(prior_files),
            timings=result["timings"],
            acp_timings=raw.get("acp_timings", {}),
            acp_session=raw.get("acp_session", {}),
            checks=checks,
            fill_warnings=layout["issues"],
            page_fill=layout["page_fill"],
            skills_line_fill=layout["skills_line_fill"],
            selected_bullet_ids=selected,
            ranked_bullet_ids=[r["candidate_id"] for r in plan["ranked"]],
            final_bullets=[
                dict(id=p["block"]["id"], text=p["block"]["text"], kind=p["block"]["kind"])
                for p in blocks
            ],
            selection=plan,
            pdf=f"resumes/{slug}.pdf",
            rubric=themes,
            reporting_note="Post-run audit recovered a successfully generated PDF"
            if raw["status"] != "completed"
            else None,
        )
        reviewed.append(report)
    good = [r for r in reviewed if r["status"] == "completed"]
    durations = [r["task_wall_s"] for r in good]
    observed_batch_wall = (max(event_times) - min(event_times)).total_seconds()
    retry_count = sum(r.get("prior_failed_attempt_s", 0) > 0 for r in good)
    extra_attempts = sum(r.get("prior_failed_attempts", 0) for r in good)
    theme_scores = [t["score"] for r in good for t in r["rubric"]]
    metrics = dict(
        attempted=30,
        generated=len(good),
        companies=len({j["company"] for j in jobs}),
        all_pdf_checks_pass=all(all(r["checks"].values()) for r in good) and len(good) == 30,
        median_task_s=median(durations),
        min_task_s=min(durations),
        max_task_s=max(durations),
        median_selection_s=median(r["timings"]["selection"] for r in good),
        median_layout_s=median(r["timings"]["layout"] for r in good),
        median_export_s=median(r["timings"]["export"] for r in good),
        batch_wall_s=observed_batch_wall,
        initial_batch_wall_s=summary["batch_wall_s"],
        inference_attempts=30 + extra_attempts,
        retried_jobs=retry_count,
        first_pass_generated=30 - retry_count,
        workers=summary["workers"],
        unique_final_bullet_sets=len({tuple(sorted(r["selected_bullet_ids"])) for r in good}),
        median_page_fill=median(r["page_fill"][0] for r in good),
        skills_fill_target_met=sum(r["skills_line_fill"] >= 0.95 for r in good),
        independent_rubric=dict(
            jobs=5,
            themes=len(theme_scores),
            themes_with_direct_work_evidence=sum(s == 2 for s in theme_scores),
            themes_with_project_evidence_only=sum(s == 1 for s in theme_scores),
            themes_without_evidence=sum(s == 0 for s in theme_scores),
            score=sum(theme_scores),
            maximum_score=2 * len(theme_scores),
            meaning="Predeclared reviewer themes with relevant evidence present, not a qualification, ATS, hiring or global optimality score.",
        ),
        reporting_only_errors=sum(
            r["status"] != "completed"
            and (ROOT / "runs" / r["job"]["slug"] / "result.json").exists()
            and not (ROOT / "reports" / f"{r['job']['slug']}.first-attempt.json").exists()
            for r in summary["reports"]
        ),
        manual_baseline_minutes_per_resume=20,
        manual_baseline_note="Assumed, not measured. Starts with ready profile and already collected job text, like the machine timer.",
        assumed_manual_batch_minutes=600,
        estimated_minutes_saved=600 - observed_batch_wall / 60,
        ratio_assumed_manual_to_median=1200 / median(durations),
        ratio_assumed_manual_batch_to_machine_batch=36000 / observed_batch_wall,
        timing_scope=f"Per-job time sums all its attempts. Batch time spans first selection start to final successful export, includes any retry and operator retry delay, and used up to {summary['workers']} concurrent workers. Excludes prior job collection/profile authoring and subsequent review; interpreter startup excluded.",
        cost_note=summary["cost_note"],
    )
    save(ROOT / "audit.json", dict(metrics=metrics, inventory=inventory, runs=reviewed))
    print(json.dumps(metrics, indent=2))
    return metrics, reviewed, inventory


def package(metrics, runs, inventory):
    share = ROOT / "share"
    for folder in ("resumes", "job_posts", "selections", "previews"):
        (share / folder).mkdir(parents=True, exist_ok=True)
    for run in runs:
        if run["status"] != "completed":
            continue
        slug = run["job"]["slug"]
        out = ROOT / "runs" / slug
        shutil.copy2(next(out.glob("*.pdf")), share / run["pdf"])
        shutil.copy2(out / "preview-1.png", share / "previews" / f"{slug}.png")
        shutil.copy2(ROOT / run["job"]["job_path"], share / "job_posts" / f"{slug}.txt")
        save(
            share / "selections" / f"{slug}.json",
            dict(
                selection=run["selection"],
                final_bullet_ids=run["selected_bullet_ids"],
                rubric=run["rubric"],
            ),
        )
    shutil.copy2(ROOT / "fixture/master.yaml", share / "fictional-master.yaml")
    shutil.copy2(ROOT / "jobs.json", share / "job-sources.json")
    save(share / "results.json", dict(metrics=metrics, inventory=inventory, runs=runs))
    with (share / "results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "company",
                "role",
                "job_id",
                "seconds",
                "selection_seconds",
                "layout_seconds",
                "pdf_checks_pass",
                "selected_ids",
                "source",
            ],
        )
        writer.writeheader()
        for r in runs:
            if r["status"] == "completed":
                writer.writerow(
                    dict(
                        company=r["job"]["company"],
                        role=r["job"]["role"],
                        job_id=r["job"]["id"],
                        seconds=round(r["task_wall_s"], 3),
                        selection_seconds=round(r["timings"]["selection"], 3),
                        layout_seconds=round(r["timings"]["layout"], 4),
                        pdf_checks_pass=all(r["checks"].values()),
                        selected_ids=";".join(r["selected_bullet_ids"]),
                        source=r["job"]["url"],
                    )
                )
    notes = f"""# One career. 30 real jobs. 30 tailored resumes.

Fictional Morgan Ellis: nine years, four employers, {inventory["work_bullets"]} work achievements,
{inventory["projects"]} side projects, and {inventory["skills"]} supported skills. All employment and
performance claims are invented for this benchmark, including IBM. No real candidate data.

30 distinct real employer postings across {metrics["companies"]} companies, retrieved October 20, 2026.
Jobs can close. This is a software-selection demonstration, not job applications or employer endorsement.

## Measured result

- {metrics["generated"]}/30 generated, {metrics["unique_final_bullet_sets"]} distinct final bullet sets.
- Median {metrics["median_task_s"]:.1f} seconds per resume; range {metrics["min_task_s"]:.1f}-{metrics["max_task_s"]:.1f} seconds.
- Whole batch {metrics["batch_wall_s"] / 60:.2f} minutes with {metrics["workers"]} concurrent workers.
- Median selection {metrics["median_selection_s"]:.2f}s; fitting {metrics["median_layout_s"] * 1000:.0f}ms; PDF export and previews {metrics["median_export_s"]:.2f}s.
- Every PDF checked for one page, exact approved bullet text, text extraction, ordered reading,
  margin bounds, and fictional disclosure. Passed: {metrics["all_pdf_checks_pass"]}.
- Five representative jobs were chosen for distinct requirements before results were inspected.
  A separate AI reviewer defined 25 themes before inspecting selection outputs. Direct work evidence appears for
  {metrics["independent_rubric"]["themes_with_direct_work_evidence"]}/25 themes in those rendered resumes.

## Fair comparison and limitations

The manual baseline is an explicit assumption of 20 minutes per tailored resume, not a timed human study.
That is 10 hours for 30. The observed batch was {metrics["batch_wall_s"] / 60:.2f} minutes, a modeled
{metrics["ratio_assumed_manual_batch_to_machine_batch"]:.1f}x throughput difference with three concurrent workers.
The per-resume comparison is {metrics["ratio_assumed_manual_to_median"]:.1f}x against the same assumption.
Timers start after profile and job collection; neither comparison includes writing the profile,
collecting jobs, subsequent visual review, or user edits. The batch includes the one rejected response,
the operator pause before its retry, and the retry itself. {metrics["inference_attempts"]} actual inference attempts;
{metrics["first_pass_generated"]}/30 generated on the first attempt. Interpreter startup excluded. No two-second AI claim.

Existing Codex subscription via codex-acp 2.2.2, gpt-6-sol, medium reasoning. No separate API key;
token usage and monetary inference cost were not measured. Subscription access is not free inference.

Theme coverage means relevant evidence was chosen. It does not mean all job qualifications are met,
all keywords match, the selection is globally optimal, or an employer will interview the candidate.
Figma's Bazel/monorepo experience, Apple's hyperscale, Google Distributed Cloud's GPU/hardware diagnostics,
and Prime Video's media/playback testing are genuine gaps. No invented specialist skills.
All confidence classes were neutral and no shorter variants were supplied, so those features were not tested.
Skills last-line 95% fill met in {metrics["skills_fill_target_met"]}/30 cases; the remaining aesthetic warnings
were preserved rather than adding irrelevant skills. This is a known fitting limitation.
There were {metrics["reporting_only_errors"]} benchmark-report path serialization errors after successful generation.
The saved PDFs were audited and recovered without repeating inference; these errors are retained in raw logs.

## Files

`fictional-master.yaml`: complete fixed source profile. `job-sources.json`: IDs, URLs and hashes.
`job_posts/`: saved employer text. `resumes/`: all 30 PDFs. `previews/`: all 30 page previews.
`selections/`: ranked candidates, reasons, requirement mapping, final IDs and five-job rubric.
`results.csv` and `results.json`: actual per-job timings and validation. Marketing image presents five
examples, not the five fastest runs. No personal files or machine paths are in this share folder.
"""
    (share / "README.md").write_text(notes, encoding="utf-8")
    return share


def image(share, metrics, runs, inventory):
    # Native vector text: editable, auditable and crisp. No generated bitmap text.
    import pymupdf
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen.canvas import Canvas

    pdf = share / "One career - 30 real jobs.pdf"
    width, height = 1200, 1660
    c = Canvas(str(pdf), pagesize=(width, height))
    c.setTitle("Sharp benchmark: one fictional career, 30 real jobs")

    def rect(x, y, w, h, color):
        c.setFillColor(HexColor(color))
        c.rect(x, height - y - h, w, h, stroke=0, fill=1)

    def text(x, y, value, size=20, color="#172332", font="Helvetica"):
        c.setFont(font, size)
        c.setFillColor(HexColor(color))
        c.drawString(x, height - y - size, value)

    def lines(x, y, value, size=19, chars=100, color="#435165", leading=26):
        chunks = textwrap.wrap(value, width=chars)
        for i, line in enumerate(chunks):
            text(x, y + i * leading, line, size, color)
        return len(chunks) * leading

    rect(0, 0, width, height, "#F3F6F9")
    rect(0, 0, width, 390, "#112638")
    text(58, 35, "SHARP / REAL-JOB BENCHMARK", 16, "#71DFC4", "Helvetica-Bold")
    text(58, 85, "One career. 30 real jobs.", 48, "#FFFFFF", "Helvetica-Bold")
    text(58, 144, "Different requirements. Different evidence.", 31, "#FFFFFF")
    for x, big, label in [
        (58, f"{metrics['median_task_s']:.0f}s", "median per resume"),
        (433, "30 / 30", "single-page PDFs checked"),
        (808, str(metrics["unique_final_bullet_sets"]), "distinct bullet selections"),
    ]:
        text(x, 225, big, 48, "#71DFC4", "Helvetica-Bold")
        text(x, 285, label, 18, "#E0E8EE")
    text(
        58,
        338,
        f"{metrics['companies']} companies | actual Codex ACP inference | one fixed fictional profile",
        18,
        "#BACBD8",
    )
    text(
        58,
        419,
        "Meet Morgan Ellis. Nine years building services, products and developer tools.",
        23,
        "#172332",
        "Helvetica-Bold",
    )
    lines(
        58,
        459,
        f"9 years. 4 employers. {inventory['work_bullets']} work achievements. {inventory['projects']} side projects. Payments, React interfaces, data pipelines, identity, cloud operations and developer tools.",
        20,
        99,
    )
    text(58, 533, "THE JOB ASKS FOR", 13, "#657387", "Helvetica-Bold")
    text(608, 533, "EVIDENCE SHARP CHOSE", 13, "#657387", "Helvetica-Bold")
    examples = [
        (
            "01-google-129511213234037446",
            "GOOGLE",
            "Senior SWE / Full Stack",
            "Java + TypeScript, accessible products, design leadership.",
            ["harbor_merchant_ui", "harbor_accessibility", "harbor_payments"],
        ),
        (
            "03-amazon-10556318",
            "AMAZON",
            "SDE II / Data Systems",
            "Data ingestion, distributed systems, AWS and operations.",
            ["pine_streaming", "pine_tracking", "pine_analytics"],
        ),
        (
            "05-apple-200684861",
            "APPLE",
            "SWE / Distributed Systems",
            "Java services, reliability, cloud-native operations.",
            ["harbor_payments", "harbor_observability", "pine_kubernetes"],
        ),
        (
            "06-stripe-7557899",
            "STRIPE",
            "Backend Engineer / Developer SDKs",
            "API libraries, compatibility, developer experience.",
            ["harbor_sdk", "pine_contracts", "pine_ci"],
        ),
        (
            "12-figma-5790627004",
            "FIGMA",
            "SWE / Developer Experience",
            "Build/test workflows, infrastructure and team tooling.",
            ["pine_ci", "pine_kubernetes", "harbor_sdk"],
        ),
    ]
    captions = {
        "harbor_merchant_ui": "Led React/TypeScript merchant-dashboard delivery",
        "harbor_accessibility": "Accessible onboarding + Playwright checks",
        "harbor_payments": "Java/Spring payment services + replay protection",
        "pine_streaming": "Kafka ingestion across 14 carrier feeds",
        "pine_tracking": "Go/gRPC tracking + backpressure and retries",
        "pine_analytics": "Python/SQL data-quality pipeline",
        "harbor_observability": "OpenTelemetry dashboards across six services",
        "pine_kubernetes": "Docker/Kubernetes + AWS/Terraform deployment",
        "harbor_sdk": "Versioned TypeScript SDK + compatibility tests",
        "pine_contracts": "REST/gRPC contract tests and partner fixtures",
        "pine_ci": "CI feedback cut from 18 to 7 minutes",
        "ibm_docker": "Reproducible Docker development environments",
    }
    by_slug = {r["job"]["slug"]: r for r in runs}
    for index, (slug, brand, role, wants, candidates) in enumerate(examples):
        y = 561 + index * 156
        rect(42, y, 1116, 144, "#FFFFFF")
        rect(42, y, 5, 144, "#12A98A")
        text(64, y + 13, brand, 16, "#007F6B", "Helvetica-Bold")
        text(64, y + 39, role, 20, "#172332", "Helvetica-Bold")
        lines(64, y + 76, wants, 18, 49, leading=24)
        chosen = by_slug[slug]["selected_bullet_ids"]
        candidates = [i for i in candidates if i in chosen][:3]
        for j, identifier in enumerate(candidates):
            text(609, y + 24 + j * 32, "+ " + captions[identifier], 17, "#172332")
    y = 1367
    rect(42, y, 1116, 134, "#E0F1EC")
    text(
        64,
        y + 17,
        f"30 resumes in {metrics['batch_wall_s'] / 60:.1f} minutes. Manual planning baseline: 10 hours.",
        26,
        "#123A31",
        "Helvetica-Bold",
    )
    lines(
        64,
        y + 61,
        "Manual baseline assumes 20 min/resume; not a human timing study. Three concurrent workers; one rejected response and retry included. Both start with ready career data and collected job text.",
        17,
        120,
        "#35594F",
        23,
    )
    text(
        58,
        1520,
        "Real postings. Fictional candidate. No invented experience added to fit a job.",
        19,
        "#172332",
        "Helvetica-Bold",
    )
    lines(
        58,
        1555,
        "Five varied example jobs chosen before inspecting outputs. Specialist gaps remain. Source links, all PDFs, selections, timings and limitations included. Existing Codex subscription; no separate API key. Timed from ready inputs through final PDF export; collection and profile authoring excluded.",
        14,
        143,
        "#657387",
        20,
    )
    c.save()
    with pymupdf.open(pdf) as doc:
        doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(
            str(share / "One career - 30 real jobs.png")
        )
    # Public archive deliberately excludes native runtime paths and session logs.
    with zipfile.ZipFile(
        ROOT / "Sharp - 30 real jobs benchmark.zip", "w", zipfile.ZIP_DEFLATED
    ) as z:
        for p in share.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(share))


if __name__ == "__main__":
    metrics, runs, inventory = audit()
    share = package(metrics, runs, inventory)
    image(share, metrics, runs, inventory)
