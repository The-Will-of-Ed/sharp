import pytest

from sharp.adapters.pdf import PdfRenderer
from sharp.career import prepare_document
from sharp.contracts import Changes, Constraints, Decorations, TextRun
from sharp.layout import apply_changes, apply_decorations, fit


def render_layout(career, settings, plan):
    return fit(prepare_document(career, settings, plan), settings, plan, PdfRenderer())


def test_experience_before_projects_and_master_order(career, settings, plan):
    layout = render_layout(career, settings, plan)
    assert (
        layout.selected_ids.index("w1")
        < layout.selected_ids.index("w3")
        < layout.selected_ids.index("p1")
    )
    assert layout.pages == 1
    assert all(not p.block.style.bold for p in layout.placed if p.block.kind.endswith("_bullet"))
    assert all(
        p.block.style.bold
        for p in layout.placed
        if p.block.kind in {"name", "label", "heading", "owner", "education"}
    )
    assert not any("Bold" in r.style.get("font", "") for p in layout.placed for r in p.block.runs)


def test_dependency_exclusion_and_contradiction(career, settings, plan):
    settings.constraints = Constraints(required=["w1"], requires={"w1": ["w2"]}, excluded=["p1"])
    layout = render_layout(career, settings, plan)
    assert {"w1", "w2"} <= set(layout.selected_ids)
    assert "p1" not in layout.selected_ids
    settings.constraints.excluded = ["w2"]
    with pytest.raises(ValueError, match="[Cc]onflict|[Ee]xcluded"):
        render_layout(career, settings, plan)


def test_required_point_that_does_not_fit_is_error(career, settings, plan):
    career.x_resume.bullets[0].text = "Extremely long mandatory text. " * 1000
    settings.constraints.required = ["w1"]
    with pytest.raises(ValueError, match="fit"):
        render_layout(career, settings, plan)


def test_two_pages_and_no_overflow(career, settings, plan):
    for b in career.x_resume.bullets:
        b.text *= 15
    settings.page.max_pages = 2
    settings.page.fill_targets = [0.99, 0.95]
    layout = render_layout(career, settings, plan)
    assert 1 <= layout.pages <= 2
    for p in layout.placed:
        assert p.y + p.measurement.height <= settings.page.height - settings.page.margins[2] + 0.01


def test_format_changes_are_atomic_and_after_cannot_resize(career, settings, plan):
    doc = prepare_document(career, settings, plan)
    original = doc[0].model_dump()
    with pytest.raises(ValueError):
        apply_changes(doc, Changes(patches={doc[0].id: {"size": 14}, "missing": {"bold": True}}))
    assert doc[0].model_dump() == original
    layout = render_layout(career, settings, plan)
    with pytest.raises(ValueError):
        apply_decorations(
            layout,
            Decorations(
                runs={layout.placed[0].block.id: [TextRun(start=0, end=1, style={"bold": True})]}
            ),
        )


def test_word_color_and_bold_ranges_measure(career, settings, plan):
    doc = prepare_document(career, settings, plan)
    target = next(b for b in doc if b.id == "w1")
    updated = apply_changes(
        doc,
        Changes(runs={"w1": [TextRun(start=0, end=9, style={"bold": True, "color": "#0000ff"})]}),
    )
    result = fit(updated, settings, plan, PdfRenderer())
    assert next(p for p in result.placed if p.block.id == target.id).block.runs[0].style["bold"]


def test_final_line_width_and_shortfall_are_reported(career, settings, plan):
    layout = render_layout(career, settings, plan)
    assert 0 <= layout.skills_line_fill <= 1
    assert any("skills" in x.lower() for x in layout.issues)
    assert all(0 <= x <= 1 for x in layout.page_fill)
