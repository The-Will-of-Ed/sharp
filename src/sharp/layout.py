"""Deterministic fitting and validated formatting. No renderer SDK imports."""

from .contracts import Block, Changes, Decorations, Layout, PlacedBlock, Settings, Style
from .selection import required_closure


class DoesNotFit(ValueError):
    """Only insufficient geometry is a reason to try another candidate."""


def _runs(block, runs, paint_only=False):
    for run in runs:
        if not 0 <= run.start < run.end <= len(block.text):
            raise ValueError(f"Text range outside {block.id}")
        allowed = {"color"} if paint_only else set(Style.model_fields)
        if not set(run.style) <= allowed:
            raise ValueError(
                f"Unsupported {'after-layout ' if paint_only else ''}style on {block.id}"
            )
        Style.model_validate({**block.style.model_dump(), **run.style})
        if set(run.style) & {"before", "after", "indent", "leading", "marker", "marker_offset"}:
            raise ValueError("Line spacing and indentation belong on blocks, not text ranges")


def apply_changes(document: list[Block], changes: Changes) -> list[Block]:
    result = [b.model_copy(deep=True) for b in document]
    by_id = {b.id: b for b in result}
    if not (set(changes.patches) | set(changes.runs)) <= by_id.keys():
        raise ValueError("Formatting references a missing block")
    for id, patch in changes.patches.items():
        by_id[id].style = Style.model_validate({**by_id[id].style.model_dump(), **patch})
    for id, runs in changes.runs.items():
        _runs(by_id[id], runs)
        by_id[id].runs = runs
    return result


def apply_decorations(layout: Layout, decorations: Decorations) -> Layout:
    result = layout.model_copy(deep=True)
    by_id = {p.block.id: p.block for p in result.placed}
    if not (set(decorations.colors) | set(decorations.runs)) <= by_id.keys():
        raise ValueError("Decoration references a missing placed block")
    for id, color in decorations.colors.items():
        by_id[id].style = Style.model_validate({**by_id[id].style.model_dump(), "color": color})
    for id, runs in decorations.runs.items():
        _runs(by_id[id], runs, paint_only=True)
        by_id[id].runs.extend(runs)
    return result


def _active(document, selected):
    active = []
    selected_owners = {
        b.source_ids[1] for b in document if b.id in selected and b.kind.endswith("_bullet")
    }
    has_work = any(b.id in selected and b.kind == "work_bullet" for b in document)
    has_projects = any(b.id in selected and b.kind == "project_bullet" for b in document)
    for b in document:
        if b.kind.endswith("_bullet") and b.id not in selected:
            continue
        if b.kind == "owner" and b.source_ids[0] not in selected_owners:
            continue
        if b.id == "heading:work" and not has_work:
            continue
        if b.id == "heading:projects" and not has_projects:
            continue
        active.append(b)
    return active


def _place(document, settings, measurer):
    page = settings.page
    top, right, bottom, left = page.margins
    width, available = page.width - left - right, page.height - top - bottom
    placed, used, number, y = [], [0.0], 1, top
    measured = [(b, measurer.measure(b, width - b.style.indent)) for b in document]
    for i, (b, m) in enumerate(measured):
        need = b.style.before + m.height
        # Keep headings with at least the following owner + first bullet.
        if b.kind in ("heading", "owner"):
            need += b.style.after
            j = i + 1
            while j < len(measured):
                next_b, next_m = measured[j]
                need += next_b.style.before + next_m.height + next_b.style.after
                j += 1
                if next_b.kind not in ("heading", "owner"):
                    break
        if need > available + 0.01:
            raise DoesNotFit(f"Block cannot fit: {b.id}")
        if y + need > page.height - bottom + 0.01:
            number += 1
            if number > page.max_pages:
                raise DoesNotFit("Content does not fit page limit")
            used.append(0.0)
            y = top
        y += b.style.before
        placed.append(
            PlacedBlock(
                block=b,
                page=number,
                x=left + b.style.indent,
                y=y,
                width=width - b.style.indent,
                measurement=m,
            )
        )
        y += m.height + b.style.after
        used[-1] = y - top
    return placed, used


def fit(document, settings: Settings, plan, measurer) -> Layout:
    document = [b.model_copy(deep=True) for b in document]
    for block in document:
        if block.kind != "skills":
            continue
        options = block.text.split(", ")
        chosen = []
        chosen_ids = []
        for index, name in enumerate(options):
            trial = block.model_copy(update={"text": ", ".join([*chosen, name])})
            if (
                len(
                    measurer.measure(
                        trial,
                        settings.page.width
                        - settings.page.margins[1]
                        - settings.page.margins[3]
                        - block.style.indent,
                    ).lines
                )
                <= settings.skills_max_lines
            ):
                chosen.append(name)
                if index < len(block.source_ids):
                    chosen_ids.append(block.source_ids[index])
        block.text = ", ".join(chosen)
        block.source_ids = chosen_ids
    candidate_ids = [b.id for b in document if b.kind.endswith("_bullet")]
    required = required_closure(settings.constraints)
    excluded = set(settings.constraints.excluded)

    # Conditional dependencies apply whenever a candidate is considered.
    def bundle(id):
        todo = {id}
        while True:
            more = todo | {x for a in todo for x in settings.constraints.requires.get(a, [])}
            if more == todo:
                break
            todo = more
        if todo & excluded:
            raise ValueError("Excluded supporting point conflicts with selection")
        if not todo <= set(candidate_ids):
            raise ValueError("Supporting point is absent from choice plan")
        return todo

    selected = set(required)
    if selected & excluded:
        raise ValueError("Conflicting required/excluded points")
    if not selected <= set(candidate_ids):
        raise ValueError("Required point is absent")
    try:
        placed, used = _place(_active(document, selected), settings, measurer)
    except DoesNotFit as exc:
        raise ValueError(f"Required content does not fit: {exc}") from exc
    ranks = {d.candidate_id: i for i, d in enumerate(plan.ranked)}
    kinds = {b.id: b.kind for b in document}
    eligible = set(ranks) | required
    while True:
        expanded = eligible | {
            b for a in eligible for b in settings.constraints.requires.get(a, [])
        }
        if expanded == eligible:
            break
        eligible = expanded
    inclusion_order = sorted(
        [id for id in candidate_ids if id in eligible],
        key=lambda id: (
            settings.experience_first and kinds[id] != "work_bullet",
            ranks.get(id, len(ranks)),
        ),
    )
    for id in inclusion_order:
        if id in selected or id in excluded:
            continue
        if not (
            required_closure(settings.constraints.model_copy(update={"required": [id]})) & excluded
        ):
            extra = bundle(id)
        else:
            continue
        try:
            new_placed, new_used = _place(_active(document, selected | extra), settings, measurer)
        except DoesNotFit:
            continue
        available = settings.page.height - settings.page.margins[0] - settings.page.margins[2]
        target = settings.page.fill_targets or [0.96]
        # Stop adding to an already filled last page; do not start a new page merely to hit a target.
        if (
            len(used) == settings.page.max_pages
            and used[-1] / available >= target[min(len(used) - 1, len(target) - 1)]
        ):
            continue
        selected |= extra
        placed, used = new_placed, new_used
    issues = []
    available = settings.page.height - settings.page.margins[0] - settings.page.margins[2]
    skill = next((p for p in placed if p.block.kind == "skills"), None)
    skill_fill = (
        skill.measurement.lines[-1].width / skill.width if skill and skill.measurement.lines else 0
    )
    if skill and len(skill.measurement.lines) > settings.skills_max_lines:
        raise ValueError("Selected skills exceed skills_max_lines; shorten the skill selection")
    if skill_fill < settings.skills_fill_target:
        issues.append(
            f"Skills final-line fill {skill_fill:.1%} is below target {settings.skills_fill_target:.1%}; no unsupported filler added"
        )
    fills = [min(u / available, 1.0) for u in used]
    for i, fill in enumerate(fills):
        target = (
            settings.page.fill_targets[min(i, len(settings.page.fill_targets) - 1)]
            if settings.page.fill_targets
            else 0.96
        )
        if fill < target:
            issues.append(f"Page {i + 1} fill {fill:.1%} below target {target:.1%}")
    return Layout(
        placed=placed,
        pages=len(used),
        selected_ids=[id for id in candidate_ids if id in selected],
        omitted_ids=[id for id in candidate_ids if id not in selected],
        page_fill=fills,
        remaining_height=[max(0, available - u) for u in used],
        skills_line_fill=skill_fill,
        issues=issues,
    )
