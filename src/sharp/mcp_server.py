"""Thin MCP interface. Local workspace scope applies to every file operation."""

from pathlib import Path

from .career import choice_input, confidence_hashes, digest, validate_career
from .contracts import (
    Career,
    ChoicePlan,
    CreateRequest,
    Customization,
    ProposedChanges,
    Settings,
)


def build_server(root):
    import os

    from mcp.server.mcpserver import MCPServer

    from . import service
    from .adapters.files import (
        SettingsFile,
        import_material,
        load,
        lock,
        save,
        validate_standard,
    )
    from .adapters.rules import RestrictedRules

    base = Path(root).resolve()

    def path(value):
        p = (base / value).resolve()
        if not p.is_relative_to(base):
            raise ValueError("Path is outside the configured Sharp workspace")
        return p

    def runner():
        return RestrictedRules(
            base / ".cache/rules",
            compiler=os.environ.get("SHARP_RULE_COMPILER", "extism-js"),
        )

    server = MCPServer(
        "Sharp",
        instructions="Use contracts_describe. Never infer user confidence or silently approve facts. Custom rules use customization_manage, not core source edits.",
    )

    @server.tool()
    def contracts_describe(names: list[str] | None = None):
        """Discover all versioned inputs and outputs before composing changes."""
        schemas = service.contracts()
        return (
            {name: schemas[name] for name in names}
            if names
            else {"available_contracts": list(schemas)}
        )

    @server.tool()
    def workspace_initialize():
        """Create empty local career/settings files once. Existing files are never overwritten."""
        return service.initialize(base)

    @server.tool()
    def career_inspect(career_path: str = "master.yaml"):
        """Read career, current revision, and user confidence reassessment status."""
        career = load(path(career_path), Career)
        return {
            "career": career.model_dump(by_alias=True),
            "hash": digest(career),
            "confidence_review": choice_input(career, Settings(), "").confidence_review,
        }

    @server.tool()
    def material_extract(paths: list[str]):
        """Extract resume/source text. For visual meaning, also inspect original pages/slides."""
        return import_material([str(path(p)) for p in paths], allowed_root=base)

    @server.tool()
    def career_propose(career_path: str, changes: list[dict]):
        """Create a reviewable wording proposal; does not modify career facts."""
        return ProposedChanges(
            base_hash=digest(load(path(career_path), Career)), changes=changes
        ).model_dump()

    @server.tool()
    def career_apply(career_path: str, proposal: dict):
        """Apply a user-approved wording proposal, requiring its current revision hash."""
        return service.apply_career(path(career_path), ProposedChanges.model_validate(proposal))

    @server.tool()
    def career_replace(career_path: str, proposed_career: dict, expected_hash: str):
        """Approve a complete reviewed career revision, including new/deduplicated records."""
        target = path(career_path)
        candidate = validate_standard(validate_career(Career.model_validate(proposed_career)))
        with lock(target):
            old = load(target, Career)
            if digest(old) != expected_hash:
                raise ValueError("Career revision changed")
            save(target, candidate)
        return {"hash": digest(candidate)}

    @server.tool()
    def career_assess(
        career_path: str,
        bullet_id: str,
        level: str,
        expected_hash: str,
        note: str | None = None,
    ):
        """Record an explicitly user-supplied confidence assessment. Never infer a rating."""
        target = path(career_path)
        with lock(target):
            career = load(target, Career)
            if digest(career) != expected_hash:
                raise ValueError("Career revision changed")
            bullet = next((b for b in career.x_resume.bullets if b.id == bullet_id), None)
            if bullet is None:
                raise ValueError("Unknown bullet ID")
            bullet.confidence.level, bullet.confidence.note = level, note
            validate_career(career)
            bullet.confidence.assessed_hash, bullet.confidence.definition_hash = confidence_hashes(
                career, bullet
            )
            save(target, career)
        return {"hash": digest(career)}

    @server.tool()
    def choice_context(career_path: str, settings_path: str, job: str):
        """Prepare inputs for this agent to choose directly, without a nested model call."""
        from .adapters.jobs import job_text

        return choice_input(
            load(path(career_path), Career),
            load(path(settings_path), Settings),
            job_text(job, base / ".cache/jobs"),
        ).model_dump(by_alias=True)

    @server.tool()
    def document_create(request: dict, choice_plan: dict | None = None):
        """Create from an agent-supplied choice plan or saved selection. PDF is default."""
        request = CreateRequest.model_validate(request)
        request.career_path, request.settings_path, request.output_dir = map(
            lambda p: str(path(p)),
            [request.career_path, request.settings_path, request.output_dir],
        )
        if request.selection_path:
            request.selection_path = str(path(request.selection_path))
        return service.summarize(
            service.generate(
                request,
                supplied_plan=ChoicePlan.model_validate(choice_plan) if choice_plan else None,
                scope_root=base,
            )
        ).model_dump()

    @server.tool()
    def run_inspect(directory: str):
        """Inspect decisions, page/line fill, remaining space, and timings."""
        return service.inspect_run(path(directory))

    @server.tool()
    def run_edit(directory: str, settings_changes: dict):
        """Refit existing evidence with changed formatting; zero AI calls."""
        return service.summarize(
            service.refit(path(directory), settings_changes, scope_root=base)
        ).model_dump()

    @server.tool()
    def run_export(directory: str, format: str):
        """Export a saved layout as PDF, PPTX, or DOCX without inference."""
        return service.export_saved(path(directory), format, scope_root=base).model_dump()

    @server.tool()
    def settings_inspect(settings_path: str = "settings.local.yaml"):
        """Read the one local settings authority and revision hash."""
        settings = SettingsFile(path(settings_path)).read()
        return {"settings": settings.model_dump(), "hash": digest(settings)}

    @server.tool()
    def settings_update(
        settings_path: str,
        changes: dict,
        expected_hash: str,
        apply_everywhere: bool = False,
    ):
        """Update settings atomically; preserve item exceptions unless explicitly cleared."""
        result = SettingsFile(path(settings_path)).update(
            changes, expected_hash=expected_hash, apply_everywhere=apply_everywhere
        )
        return {"settings": result.model_dump(), "hash": digest(result)}

    @server.tool()
    def customization_manage(
        settings_path: str,
        action: str,
        expected_hash: str,
        customization: dict | None = None,
        id: str | None = None,
        preview_payload: dict | None = None,
    ):
        """List/install/update/remove named user rules without changing application source."""
        file = SettingsFile(path(settings_path))
        if action == "list":
            return [r.model_dump() for r in file.read().customizations]
        result = file.customize(
            action,
            expected_hash=expected_hash,
            customization=customization,
            id=id,
            runner=runner() if action in ("install", "update") else None,
            preview_payload=preview_payload,
        )
        return {"settings": result.model_dump(), "hash": digest(result)}

    @server.tool()
    def customization_preview(customization: dict, payload: dict):
        """Compile/run a proposed rule without activating it; validate returned contract."""
        from .contracts import Changes, Decorations

        rule = Customization.model_validate(customization)
        runtime = runner()
        runtime.install(rule)
        result = runtime.run(rule, payload)
        model = {
            "selection": ChoicePlan,
            "before_layout": Changes,
            "after_layout": Decorations,
        }[rule.stage]
        return model.model_validate(result).model_dump()

    @server.tool()
    def settings_share(settings_path: str, destination: str):
        """Export a portable settings copy; refuse machine-specific font paths."""
        value = SettingsFile(path(settings_path)).portable()
        target = path(destination)
        if target.exists():
            raise ValueError("Destination exists")
        save(target, value)
        return {"path": str(target)}

    @server.tool()
    def settings_import(settings_path: str, source: str, expected_hash: str):
        """Replace local settings with a reviewed portable copy; creates no runtime overlay."""
        incoming = SettingsFile(path(source)).portable()
        return (
            SettingsFile(path(settings_path))
            .update(incoming, expected_hash=expected_hash)
            .model_dump()
        )

    return server


def serve(root):
    build_server(root).run(transport="stdio")
