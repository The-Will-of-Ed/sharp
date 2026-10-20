"""Pure career validation and document preparation. No files or vendors."""

from __future__ import annotations

import hashlib
import json

from .contracts import (
    Block,
    Bullet,
    Career,
    ChoiceInput,
    ChoicePlan,
    ProposedChanges,
    Settings,
    Style,
)


def digest(value) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json", by_alias=True)
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def owners(career: Career):
    return [
        (kind, record)
        for kind in ("work", "projects", "volunteer")
        for record in getattr(career, kind)
    ]


def unique(values, label):
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {label}")


def validate_career(career: Career) -> Career:
    x = career.x_resume
    owner_ids = [o.get("x_id") for _, o in owners(career)]
    if any(not isinstance(i, str) or not i for i in owner_ids):
        raise ValueError("Work, project, and volunteer records need nonempty x_id")
    categories = [
        owner_ids,
        [b.id for b in x.bullets],
        [e.id for e in x.evidence],
        [s.id for s in x.skills],
        [s.id for s in x.summaries],
    ]
    unique([i for values in categories for i in values], "stable ID")
    unique([c.id for c in x.confidence_levels], "confidence class ID")
    unique([c.order for c in x.confidence_levels], "confidence class order")
    classes = {c.id for c in x.confidence_levels}
    if "unrated" not in classes:
        raise ValueError("Confidence catalog must retain the neutral unrated sentinel")
    evidence = {e.id for e in x.evidence}
    skills = {s.id for s in x.skills}
    for b in x.bullets:
        if not b.text.strip():
            raise ValueError(f"Empty bullet: {b.id}")
        if b.approval == "approved" and not b.evidence_ids:
            raise ValueError(f"Approved bullet needs supporting or user-attested evidence: {b.id}")
        if b.owner_id not in owner_ids:
            raise ValueError(f"Unknown owner for {b.id}: {b.owner_id}")
        if b.confidence.level not in classes:
            raise ValueError(f"Unknown confidence class on {b.id}")
        if not set(b.skill_ids) <= skills:
            raise ValueError(f"Unknown skill on {b.id}")
        unique([v.id for v in b.variants], f"variant ID on {b.id}")
        for text, qualifiers in [(b.text, b.qualifiers)] + [
            (v.text, v.qualifiers) for v in b.variants
        ]:
            if not set(b.qualifiers) <= set(qualifiers) or any(
                q.casefold() not in text.casefold() for q in qualifiers
            ):
                raise ValueError(f"Missing protected qualifier on {b.id}")
    for item in [*x.bullets, *x.skills, *x.summaries]:
        if not set(item.evidence_ids) <= evidence:
            raise ValueError(f"Unknown evidence on {item.id}")
    for summary in x.summaries:
        if summary.approval == "approved" and not summary.evidence_ids:
            raise ValueError(
                f"Approved summary needs supporting or user-attested evidence: {summary.id}"
            )
    if not career.basics.get("name"):
        raise ValueError("Career basics.name is required")
    return career


def confidence_hashes(career: Career, bullet: Bullet) -> tuple[str, str]:
    claim = {
        "text": " ".join(bullet.text.split()),
        "owner_id": bullet.owner_id,
        "qualifiers": bullet.qualifiers,
        "evidence_ids": bullet.evidence_ids,
        "variants": [
            {"id": v.id, "text": " ".join(v.text.split()), "qualifiers": v.qualifiers}
            for v in bullet.variants
        ],
    }
    definition = next(
        c.definition for c in career.x_resume.confidence_levels if c.id == bullet.confidence.level
    )
    return digest(claim), digest(definition)


def choice_input(career: Career, settings: Settings, job: str) -> ChoiceInput:
    validate_career(career)
    review = {}
    for b in career.x_resume.bullets:
        a, d = confidence_hashes(career, b)
        review[b.id] = b.confidence.level != "unrated" and (
            a != b.confidence.assessed_hash or d != b.confidence.definition_hash
        )
    return ChoiceInput(
        career=career,
        job=job,
        instructions=settings.selection_instructions,
        constraints=settings.constraints,
        confidence_review=review,
    )


def approve_changes(career: Career, proposal: ProposedChanges) -> Career:
    if proposal.base_hash != digest(career):
        raise ValueError("Stale career revision; inspect and propose again")
    result = career.model_copy(deep=True)
    by_id = {b.id: b for b in result.x_resume.bullets}
    unique([c.target_id for c in proposal.changes], "proposal target")
    for change in proposal.changes:
        if change.target_id not in by_id:
            raise ValueError(f"Unknown proposal target: {change.target_id}")
        bullet = by_id[change.target_id]
        if not set(bullet.qualifiers) <= set(change.qualifiers):
            raise ValueError(f"Cannot remove protected qualifiers on {bullet.id}")
        bullet.text, bullet.qualifiers, bullet.evidence_ids = (
            change.text,
            change.qualifiers,
            change.evidence_ids,
        )
        bullet.approval = "approved"
    return validate_career(result)


def prepare_document(career: Career, settings: Settings, plan: ChoicePlan) -> list[Block]:
    """Compose all ranked approved candidates. The fitter owns final inclusion."""
    from .selection import validate_plan

    validate_plan(plan, career, settings)
    doc = []

    def add(id, kind, text, style="body", source_ids=None, url=None):
        s = settings.styles.get(style, settings.styles["body"]).model_copy(deep=True)
        s = Style.model_validate({**s.model_dump(), **settings.exceptions.get(id, {})})
        doc.append(
            Block(
                id=id,
                kind=kind,
                text=text,
                style=s,
                source_ids=source_ids or [],
                url=url,
            )
        )

    basics = career.basics
    add("name", "name", basics["name"], "name")
    if basics.get("label"):
        add("label", "label", basics["label"], "label" if "label" in settings.styles else "owner")
    location = basics.get("location") or {}
    location_text = ", ".join(
        str(location[k]) for k in ("city", "region", "countryCode") if location.get(k)
    )
    contact = " | ".join(
        str(value) for value in (basics.get("email"), basics.get("phone"), location_text) if value
    )
    if contact:
        add("contact", "contact", contact, "contact")
    for i, profile in enumerate(basics.get("profiles", [])):
        url = profile.get("url", "")
        if url:
            add(f"profile:{i}", "contact", url, "contact", url=url)
    ranked = {d.candidate_id: i for i, d in enumerate(plan.ranked)}
    # A complete approved pool lets before-layout rules require an unranked point.
    # fit() still admits only ranked candidates and explicit supporting requirements.
    selected = {b.id for b in career.x_resume.bullets if b.approval == "approved"}
    variant = {d.candidate_id: d.variant_id for d in plan.ranked}
    summary = next((s for s in career.x_resume.summaries if s.id == plan.summary_id), None)
    for section in settings.section_order:
        if section == "summary" and summary:
            add("heading:summary", "heading", "SUMMARY", "heading")
            add("summary", "summary", summary.text, source_ids=[summary.id])
        if section in ("work", "projects"):
            group_owners = [
                (k, o) for k, o in owners(career) if (k == "work") == (section == "work")
            ]
            relevant = [
                (
                    o,
                    [
                        b
                        for b in career.x_resume.bullets
                        if b.owner_id == o["x_id"]
                        and b.id in selected
                        and b.id not in settings.constraints.excluded
                    ],
                )
                for _, o in group_owners
            ]
            relevant = [(o, bs) for o, bs in relevant if bs]
            if not relevant:
                continue
            add(
                f"heading:{section}",
                "heading",
                "EXPERIENCE" if section == "work" else "PROJECTS",
                "heading",
            )
            for o, bs in relevant:
                owner = o["x_id"]
                title = " | ".join(
                    str(v) for v in (o.get("name") or o.get("organization"), o.get("position")) if v
                )
                dates = " - ".join(str(o[k]) for k in ("startDate", "endDate") if o.get(k))
                add(
                    f"owner:{owner}",
                    "owner",
                    title + (f" | {dates}" if dates else ""),
                    "owner",
                    [owner],
                )
                for b in sorted(bs, key=lambda b: ranked.get(b.id, -1)):
                    text = next(
                        (v.text for v in b.variants if v.id == variant.get(b.id)),
                        b.text,
                    )
                    add(
                        b.id,
                        "work_bullet" if section == "work" else "project_bullet",
                        text,
                        style="bullet",
                        source_ids=[b.id, owner],
                    )
        if section == "education" and career.education:
            add("heading:education", "heading", "EDUCATION", "heading")
            for i, e in enumerate(career.education):
                add(
                    f"education:{i}",
                    "education",
                    " | ".join(
                        str(e[k])
                        for k in ("institution", "studyType", "area", "endDate")
                        if e.get(k)
                    ),
                    style="education",
                )
        if section == "skills" and plan.skill_ids:
            skills = {s.id: s.name for s in career.x_resume.skills}
            add("heading:skills", "heading", "SKILLS", "heading")
            add(
                "skills",
                "skills",
                ", ".join(skills[i] for i in plan.skill_ids),
                source_ids=plan.skill_ids,
            )
    known = {b.id for b in doc} | {b.id for b in career.x_resume.bullets}
    missing = set(settings.exceptions) - known
    if missing:
        raise ValueError(f"Settings exceptions reference absent document blocks: {sorted(missing)}")
    unique([b.id for b in doc], "document block ID; rename the conflicting career ID")
    return doc
