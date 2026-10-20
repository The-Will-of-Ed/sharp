"""Cold/warm local timings, excluding provider inference. No personal data."""

import json
import subprocess
import sys
from pathlib import Path
from statistics import median
from time import perf_counter

from sharp.adapters.files import save
from sharp.contracts import Career, ChoicePlan, CreateRequest, Decision, Settings
from sharp.service import export_saved, generate, refit


def fixture(directory, pages):
    from importlib.resources import files

    import yaml

    directory.mkdir(parents=True, exist_ok=True)
    career = Career.model_validate(
        yaml.safe_load(
            files("sharp").joinpath("defaults/career.example.yaml").read_text(encoding="utf-8")
        )
    )
    original = career.x_resume.bullets[0]
    career.x_resume.bullets = [
        original.model_copy(
            update={"id": f"point_{i}", "text": f"Initiative {i + 1}: " + original.text}
        )
        for i in range(80)
    ]
    settings = Settings()
    settings.page.max_pages = pages
    settings.page.fill_targets = [0.96] * pages
    plan = ChoicePlan(
        ranked=[Decision(candidate_id=b.id) for b in career.x_resume.bullets],
        summary_id="example_summary",
        skill_ids=[s.id for s in career.x_resume.skills],
    )
    for filename, value in (
        ("career.json", career),
        ("settings.json", settings),
        ("selection.json", plan),
    ):
        save(directory / filename, value)
    return CreateRequest(
        career_path=str((directory / "career.json").resolve()),
        settings_path=str((directory / "settings.json").resolve()),
        selection_path=str((directory / "selection.json").resolve()),
        output_dir=str((directory / "run").resolve()),
        title="Software Engineer",
    )


def main():
    root = Path(__file__).resolve().parents[1] / "outputs/benchmark"
    report = {
        "units": "seconds",
        "provider": "none; supplied choice plan",
        "runs_per_case": 5,
        "cases": {},
    }
    for pages in (1, 2):
        request = fixture(root / f"{pages}-page", pages)
        request_path = root / f"{pages}-page/request.json"
        save(request_path, request)
        start = perf_counter()
        subprocess.run(
            [
                sys.executable,
                "-m",
                "sharp",
                "document_create",
                "--root",
                str(root),
                "--args",
                json.dumps({"request": request.model_dump()}),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        cold = perf_counter() - start
        warm, edits = [], []
        for i in range(5):
            start = perf_counter()
            result = generate(request)
            warm.append(perf_counter() - start)
            start = perf_counter()
            refit(result.output_dir, {"styles.body.size": 9.7 if i % 2 else 10})
            edits.append(perf_counter() - start)
        start = perf_counter()
        export_saved(result.output_dir, "pptx")
        pptx = perf_counter() - start
        start = perf_counter()
        export_saved(result.output_dir, "docx")
        docx = perf_counter() - start
        report["cases"][f"{pages}-page"] = {
            "candidate_bullets": 80,
            "rendered_pages": result.layout.pages,
            "cold_cli": cold,
            "warm_pdf_median": median(warm),
            "warm_pdf_max": max(warm),
            "warm_edit_median": median(edits),
            "warm_edit_max": max(edits),
            "pptx_export": pptx,
            "docx_export": docx,
            "local_two_second_target_met": max(warm + edits) < 2,
        }
    report["manual_baseline"] = {
        "minutes": 30,
        "status": "assumed, not measured",
        "explanation": "Manual selection, formatting, export and review; not a like-for-like quality benchmark.",
    }
    root.mkdir(parents=True, exist_ok=True)
    save(root / "report.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
