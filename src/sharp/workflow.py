"""Application orchestration. Domain operations receive external capabilities."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import yaml

from .career import choice_input, prepare_document, validate_career
from .contracts import (
    Block,
    Career,
    Changes,
    ChoicePlan,
    CreateRequest,
    Decorations,
    RunResult,
    Settings,
)
from .layout import apply_changes, apply_decorations, fit
from .selection import validate_plan


def read_record(path, model):
    return model.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def save_record(path, value):
    data = value.model_dump(mode="json", by_alias=True) if hasattr(value, "model_dump") else value
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)


def _hooks(stage, settings, career, payload, runner):
    valid = {b.id for b in career.x_resume.bullets}
    for customization in settings.customizations:
        if not customization.enabled or customization.stage != stage:
            continue
        if not set(customization.references) <= valid:
            raise ValueError(f"Rule {customization.id}: missing career references")
        if runner is None:
            raise ValueError(f"Rule {customization.id} requires the optional restricted runtime")
        try:
            from .contracts import AfterInput, BeforeInput, SelectionPolicyInput

            input_model = {
                "selection": SelectionPolicyInput,
                "before_layout": BeforeInput,
                "after_layout": AfterInput,
            }[stage]
            current = input_model.model_validate(payload() if callable(payload) else payload)
            yield (
                customization.id,
                runner.run(customization, current.model_dump(mode="json", by_alias=True)),
            )
        except Exception as exc:
            raise ValueError(f"Rule {customization.id} failed: {exc}") from exc


def _create(
    request: CreateRequest,
    *,
    chooser,
    renderer,
    supplied_plan=None,
    exporters=None,
    rule_runner=None,
    skip_selection_rules=False,
    supplied_settings=None,
) -> RunResult:
    """One planning call at most. Formatting, fitting and export never call AI."""
    started, timings = perf_counter(), {}
    out = Path(request.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex

    def event(stage, status, elapsed=None, **extra):
        entry = {
            "run_id": run_id,
            "stage": stage,
            "status": status,
            "elapsed_s": elapsed,
            "time": datetime.now(timezone.utc).isoformat(),
            **extra,
        }
        with (out / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    try:
        career = validate_career(read_record(request.career_path, Career))
        settings = (
            supplied_settings.model_copy(deep=True)
            if supplied_settings is not None
            else read_record(request.settings_path, Settings)
        )
        save_record(out / "settings.base.json", settings)
        event("selection", "started")
        start = perf_counter()
        if supplied_plan is not None:
            plan = supplied_plan
        elif request.selection_path:
            plan = read_record(request.selection_path, ChoicePlan)
        elif request.document_type == "cover_letter":
            plan = ChoicePlan(ranked=[])
        else:
            payload = choice_input(career, settings, request.job)
            plan = chooser.choose(payload) if hasattr(chooser, "choose") else chooser(payload)
        for id, output in _hooks(
            "selection" if not skip_selection_rules else "skip",
            settings,
            career,
            lambda: {
                "input": choice_input(career, settings, request.job).model_dump(),
                "plan": plan.model_dump(),
            },
            rule_runner,
        ):
            try:
                plan = ChoicePlan.model_validate(output)
            except Exception as exc:
                raise ValueError(f"Rule {id}: invalid choice plan: {exc}") from exc
        validate_plan(plan, career, settings)
        timings["selection"] = perf_counter() - start
        event(
            "selection",
            "completed",
            timings["selection"],
            provider=plan.provider,
            model=plan.model,
            usage=plan.usage,
        )
        save_record(out / "career.json", career)
        save_record(out / "selection.json", plan)
        save_record(out / "request.json", request)
        document = prepare_document(career, settings, plan)
        if request.document_type == "cover_letter":
            if not request.letter_text:
                raise ValueError(
                    "Cover letter requires agent-supplied letter_text; no template fabricates claims"
                )
            document = [b for b in document if b.kind in ("name", "label", "contact")]
            document.extend(
                Block(
                    id=f"letter:{i}",
                    kind="paragraph",
                    text=t,
                    style=settings.styles["body"],
                )
                for i, t in enumerate(request.letter_text.split("\n\n"))
                if t.strip()
            )
        save_record(out / "base_document.json", [b.model_dump() for b in document])
        start = perf_counter()
        for id, output in _hooks(
            "before_layout",
            settings,
            career,
            lambda: {
                "document": [b.model_dump() for b in document],
                "settings": settings.model_dump(),
                "career": career.model_dump(by_alias=True),
                "job": request.job,
                "measurements": [
                    renderer.measure(
                        b,
                        settings.page.width
                        - settings.page.margins[1]
                        - settings.page.margins[3]
                        - b.style.indent,
                    ).model_dump()
                    for b in document
                ],
            },
            rule_runner,
        ):
            try:
                changes = Changes.model_validate(output)
                document = apply_changes(document, changes)
                if changes.constraints:
                    from .contracts import Constraints

                    old, new = settings.constraints, changes.constraints
                    settings.constraints = Constraints(
                        required=list(dict.fromkeys(old.required + new.required)),
                        excluded=list(dict.fromkeys(old.excluded + new.excluded)),
                        requires={
                            k: list(
                                dict.fromkeys(old.requires.get(k, []) + new.requires.get(k, []))
                            )
                            for k in old.requires.keys() | new.requires.keys()
                        },
                    )
                    validate_plan(plan, career, settings)
            except Exception as exc:
                raise ValueError(f"Rule {id}: {exc}") from exc
            event("before_layout", "completed", rule_id=id)
        layout = fit(document, settings, plan, renderer)
        for id, output in _hooks(
            "after_layout",
            settings,
            career,
            lambda: {
                "layout": layout.model_dump(),
                "settings": settings.model_dump(),
                "career": career.model_dump(by_alias=True),
                "job": request.job,
            },
            rule_runner,
        ):
            try:
                layout = apply_decorations(layout, Decorations.model_validate(output))
            except Exception as exc:
                raise ValueError(f"Rule {id}: {exc}") from exc
            event("after_layout", "completed", rule_id=id)
        timings["layout"] = perf_counter() - start
        save_record(out / "settings.json", settings)
        save_record(out / "document.json", [b.model_dump() for b in document])
        save_record(out / "layout.json", layout)
        selected = set(layout.selected_ids)
        ranked = {d.candidate_id: d for d in plan.ranked}
        save_record(
            out / "decisions.json",
            [
                {
                    "candidate_id": b.id,
                    "selected": b.id in selected,
                    "provider_reason": ranked[b.id].reason if b.id in ranked else None,
                    "application_reason": "included"
                    if b.id in selected
                    else "excluded_by_user"
                    if b.id in settings.constraints.excluded
                    else "not_ranked_relevant"
                    if b.id not in ranked
                    else "does_not_fit_or_target_reached",
                    "evidence_ids": b.evidence_ids,
                }
                for b in career.x_resume.bullets
            ],
        )
        event("layout", "completed", timings["layout"], pages=layout.pages)
        start, artifacts = perf_counter(), []
        title = "".join(c for c in request.title if c not in '<>:"/\\|?*').strip() or "Resume"
        filename = f"{career.basics['name']} - {title}"
        filename = "".join(c for c in filename if c not in '<>:"/\\|?*')
        for format in dict.fromkeys(request.formats):
            exporter = renderer if format == "pdf" else (exporters or {}).get(format)
            if exporter is None:
                raise ValueError(f"Format {format} not configured; install its optional adapter")
            artifacts.append(exporter.export(layout, settings, str(out / f"{filename}.{format}")))
        if hasattr(renderer, "preview"):
            artifacts.extend(renderer.preview(layout, settings, str(out / "preview")))
        pdf = next((a for a in artifacts if a.format == "pdf"), None)
        if pdf and hasattr(renderer, "png_preview"):
            artifacts.extend(renderer.png_preview(pdf.path, str(out / "preview")))
        timings["export"] = perf_counter() - start
        timings["total"] = perf_counter() - started
        result = RunResult(
            run_id=run_id,
            output_dir=str(out),
            artifacts=artifacts,
            layout=layout,
            timings=timings,
        )
        save_record(out / "result.json", result)
        event("export", "completed", timings["export"], artifact_count=len(artifacts))
        return result
    except Exception as exc:
        event("run", "failed", perf_counter() - started, error_type=type(exc).__name__)
        raise


def create(request: CreateRequest, **dependencies) -> RunResult:
    """Stage a complete run; failed generation leaves prior artifacts consistent."""
    import shutil
    import tempfile

    final = Path(request.output_dir).resolve()
    final.parent.mkdir(parents=True, exist_ok=True)
    if final.exists() and any(final.iterdir()) and not (final / ".sharp-run").exists():
        allowed = {"career.json", "selection.json", "settings.local.yaml"}
        if not {p.name for p in final.iterdir()} <= allowed:
            raise ValueError("Output folder is not a Sharp run; choose an empty output folder")
    stage = Path(tempfile.mkdtemp(prefix=f".sharp-{final.name}-", dir=final.parent)).resolve()
    backup = final.with_name(f".sharp-backup-{uuid.uuid4().hex}")

    def cleanup(folder):
        folder = folder.resolve()
        if folder.parent != final.parent or not folder.name.startswith(".sharp-"):
            raise ValueError("Refusing cleanup outside the run staging directory")
        if folder.exists():
            shutil.rmtree(folder)

    try:
        if final.exists():
            shutil.copytree(final, stage, dirs_exist_ok=True)
        previous = stage / "result.json"
        if previous.exists():
            for artifact in json.loads(previous.read_text(encoding="utf-8")).get("artifacts", []):
                old_path = Path(artifact["path"])
                if old_path.is_relative_to(final):
                    (stage / old_path.relative_to(final)).unlink(missing_ok=True)
        result = _create(request.model_copy(update={"output_dir": str(stage)}), **dependencies)

        def remap(value):
            if isinstance(value, str) and value.startswith(str(stage)):
                return str(final) + value[len(str(stage)) :]
            if isinstance(value, list):
                return [remap(v) for v in value]
            if isinstance(value, dict):
                return {k: remap(v) for k, v in value.items()}
            return value

        for record in stage.glob("*.json"):
            save_record(record, remap(json.loads(record.read_text(encoding="utf-8"))))
        (stage / ".sharp-run").write_text("1", encoding="ascii")
        result = RunResult.model_validate(remap(result.model_dump()))
        if final.exists():
            final.rename(backup)
        try:
            stage.rename(final)
        except OSError:
            if backup.exists():
                backup.rename(final)
            raise
        if backup.exists():
            cleanup(backup)
        return result
    finally:
        if stage.exists():
            cleanup(stage)


def reopen_run(output_dir, *, renderer, changes=None, exporters=None, rule_runner=None):
    """Refit a saved snapshot without inference or touching the user's career file."""
    out = Path(output_dir)
    request = read_record(out / "request.json", CreateRequest)
    settings_source = out / "settings.base.json"
    settings = read_record(
        settings_source if settings_source.exists() else out / "settings.json", Settings
    ).model_dump()
    for key, value in (changes or {}).items():
        parts, target = key.split("."), settings
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    # Store a revised run configuration, never the original local settings.
    validated = Settings.model_validate(settings)
    request.career_path = str(out / "career.json")
    request.selection_path = str(out / "selection.json")
    request.output_dir = str(out)
    return create(
        request,
        chooser=None,
        renderer=renderer,
        exporters=exporters,
        rule_runner=rule_runner,
        skip_selection_rules=True,
        supplied_settings=validated,
    )
