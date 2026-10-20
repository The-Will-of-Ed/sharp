"""Selection policy validation. Providers never own factual or geometry rules."""

from .career import unique, validate_career
from .contracts import Career, ChoicePlan, Constraints, Settings


def required_closure(constraints: Constraints) -> set[str]:
    required = set(constraints.required)
    while True:
        expanded = required | {b for a in required for b in constraints.requires.get(a, [])}
        if expanded == required:
            return required
        required = expanded


def validate_plan(plan: ChoicePlan, career: Career, settings: Settings) -> ChoicePlan:
    validate_career(career)
    bullets = {b.id: b for b in career.x_resume.bullets}
    ids = [d.candidate_id for d in plan.ranked]
    unique(ids, "selected candidate")
    refs = set(settings.constraints.required + settings.constraints.excluded)
    refs |= set(settings.constraints.requires)
    refs |= {i for values in settings.constraints.requires.values() for i in values}
    if not refs <= bullets.keys():
        raise ValueError(f"Unknown constraint IDs: {sorted(refs - bullets.keys())}")
    if required_closure(settings.constraints) & set(settings.constraints.excluded):
        raise ValueError("Conflicting required and excluded points")
    potential = set(ids) | required_closure(settings.constraints)
    while True:
        more = potential | {b for a in potential for b in settings.constraints.requires.get(a, [])}
        if more == potential:
            break
        potential = more
    for id in potential:
        if id not in bullets:
            raise ValueError(f"Unknown candidate: {id}")
        if bullets[id].approval != "approved":
            raise ValueError(f"Candidate is unapproved: {id}")
    for d in plan.ranked:
        if d.variant_id and d.variant_id not in {v.id for v in bullets[d.candidate_id].variants}:
            raise ValueError(f"Unknown variant for {d.candidate_id}")
        if not set(d.requirement_ids) <= plan.requirements.keys():
            raise ValueError(f"Unknown requirement on {d.candidate_id}")
    supported = {s.id for s in career.x_resume.skills if s.evidence_ids}
    if not set(plan.skill_ids) <= supported:
        raise ValueError("Unknown or unsupported selected skill")
    unique(plan.skill_ids, "selected skill")
    if plan.summary_id and plan.summary_id not in {
        s.id for s in career.x_resume.summaries if s.approval == "approved"
    }:
        raise ValueError("Unknown or unapproved summary")
    return plan
