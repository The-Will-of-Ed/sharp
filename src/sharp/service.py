"""Composition for CLI/MCP. Optional adapters are imported only when needed."""

import os
from pathlib import Path

from .adapters.files import SettingsFile, load, save, validate_standard
from .adapters.jobs import job_text
from .career import approve_changes, digest
from .contracts import Career, CreateRequest, Settings


def contracts():
    import json
    from copy import deepcopy
    from importlib.resources import files

    from pydantic import BaseModel

    from . import contracts as definitions

    schemas = {
        name: cls.model_json_schema(by_alias=True)
        for name, cls in vars(definitions).items()
        if isinstance(cls, type)
        and issubclass(cls, BaseModel)
        and cls.__module__ == definitions.__name__
        and name != "Record"
    }
    upstream = json.loads(
        files("sharp").joinpath("defaults/jsonresume.schema.json").read_text(encoding="utf-8")
    )
    for schema in schemas.values():
        career_schema = (
            schema if schema.get("title") == "Career" else schema.get("$defs", {}).get("Career")
        )
        if career_schema is None:
            continue
        for name, standard in upstream["properties"].items():
            if name in career_schema["properties"]:
                career_schema["properties"][name] = deepcopy(standard)
        for group in ("work", "projects", "volunteer"):
            item = career_schema["properties"][group]["items"]
            item["properties"]["x_id"] = {
                "type": "string",
                "description": "Stable owner identity for bullet attribution and rules.",
            }
            item["required"] = list(dict.fromkeys(item.get("required", []) + ["x_id"]))
        schema["definitions"] = deepcopy(upstream.get("definitions", {}))
    meanings_file = files("sharp").joinpath("defaults/contract.meanings.json")
    meanings = (
        json.loads(meanings_file.read_text(encoding="utf-8")) if meanings_file.is_file() else {}
    )

    def explain(schema):
        for name, value in schema.get("properties", {}).items():
            if name in meanings:
                value["description"] = meanings[name]
        for value in schema.get("$defs", {}).values():
            explain(value)

    for schema in schemas.values():
        explain(schema)
    return schemas


def summarize(result):
    from .contracts import RunSummary

    return RunSummary(
        run_id=result.run_id,
        output_dir=result.output_dir,
        artifacts=result.artifacts,
        pages=result.layout.pages,
        selected_ids=result.layout.selected_ids,
        omitted_ids=result.layout.omitted_ids,
        page_fill=result.layout.page_fill,
        skills_line_fill=result.layout.skills_line_fill,
        remaining_height=result.layout.remaining_height,
        issues=result.layout.issues,
        timings=result.timings,
    )


def initialize(directory):

    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    SettingsFile(root / "settings.local.yaml").initialize()
    target = root / "master.yaml"
    if not target.exists():
        save(target, Career(basics={"name": "Your Name"}))
    return {
        "career": str(target.resolve()),
        "settings": str((root / "settings.local.yaml").resolve()),
    }


def runner_for(settings, cache):
    if not any(r.enabled for r in settings.customizations):
        return None
    from .adapters.rules import RestrictedRules

    return RestrictedRules(cache, compiler=os.environ.get("SHARP_RULE_COMPILER", "extism-js"))


def generate(request: CreateRequest, *, supplied_plan=None, provider=None, scope_root=None):
    from .adapters.office import OfficeExporter
    from .adapters.pdf import PdfRenderer
    from .workflow import create

    validate_standard(load(request.career_path, Career))
    settings = load(request.settings_path, Settings)
    cache = Path(request.settings_path).parent / ".cache"
    request = request.model_copy(update={"job": job_text(request.job, cache / "jobs")})
    if provider and not supplied_plan:
        from .adapters.providers import ACPChooser, LiteLLMChooser

        provider = dict(provider)
        kind = provider.pop("kind")
        if kind == "litellm":
            provider = LiteLLMChooser(**provider)
        elif kind == "acp":
            provider = ACPChooser(**provider)
        else:
            raise ValueError("Provider kind must be litellm or acp")

    def missing(_):
        raise ValueError(
            "Supply selection_path, an agent choice plan, or a configured provider. Sharp never silently selects by keywords."
        )

    return create(
        request,
        chooser=provider or missing,
        renderer=PdfRenderer(allowed_font_root=scope_root),
        supplied_plan=supplied_plan,
        exporters={f: OfficeExporter(f) for f in request.formats if f != "pdf"},
        rule_runner=runner_for(settings, cache / "rules"),
    )


def refit(directory, changes, *, scope_root=None):
    from .adapters.office import OfficeExporter
    from .adapters.pdf import PdfRenderer
    from .workflow import reopen_run

    request = load(Path(directory) / "request.json", CreateRequest)
    settings = load(Path(directory) / "settings.json", Settings)
    return reopen_run(
        directory,
        renderer=PdfRenderer(allowed_font_root=scope_root),
        changes=changes,
        exporters={f: OfficeExporter(f) for f in request.formats if f != "pdf"},
        rule_runner=runner_for(settings, Path(request.settings_path).parent / ".cache/rules"),
    )


def inspect_run(directory):
    import json

    root = Path(directory)
    return {
        name: json.loads((root / f"{name}.json").read_text(encoding="utf-8"))
        for name in ("result", "selection", "settings")
    }


def apply_career(path, proposal):
    from .adapters.files import lock

    with lock(path):
        result = approve_changes(load(path, Career), proposal)
        save(path, result)
    return {
        "career_hash": digest(result),
        "changed_ids": [c.target_id for c in proposal.changes],
    }


def export_saved(directory, format, *, scope_root=None):
    from .contracts import Layout

    root = Path(directory)
    layout = load(root / "layout.json", Layout)
    settings = load(root / "settings.json", Settings)
    if format == "pdf":
        from .adapters.pdf import PdfRenderer

        exporter = PdfRenderer(allowed_font_root=scope_root)
        for placed in layout.placed:
            exporter.measure(placed.block, placed.width)
    else:
        from .adapters.office import OfficeExporter

        exporter = OfficeExporter(format)
    request = load(root / "request.json", CreateRequest)
    career = load(root / "career.json", Career)
    name = "".join(c for c in f"{career.basics['name']} - {request.title}" if c not in '<>:"/\\|?*')
    return exporter.export(layout, settings, str(root / f"{name}.{format}"))
