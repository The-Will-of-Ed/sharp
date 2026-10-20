import pytest
from sharp.contracts import ChoicePlan, Decision, Constraints, Block, Style
from sharp.career import prepare_document
from sharp.layout import fit
from sharp.adapters.pdf import PdfRenderer


def test_optional_dependency_missing_from_provider_is_added(career, settings, plan):
    plan.ranked = [Decision(candidate_id="w1")]
    settings.constraints.requires = {"w1": ["w2"]}
    result = fit(prepare_document(career, settings, plan), settings, plan, PdfRenderer())
    assert {"w1", "w2"} <= set(result.selected_ids)


def test_large_heading_spacing_does_not_orphan():
    from sharp.contracts import Settings
    settings = Settings()
    settings.page.height = 250
    settings.page.margins = [10, 10, 10, 10]
    document = [Block(id="prefix", kind="summary", text="A", style=Style(leading=150)),
                Block(id="heading", kind="heading", text="B", style=Style(leading=10, after=50)),
                Block(id="body", kind="summary", text="C", style=Style(leading=30))]
    with pytest.raises(ValueError, match="fit"):
        fit(document, settings, ChoicePlan(ranked=[]), PdfRenderer())


def test_custom_confidence_catalog_is_passed_not_inferred(career, settings):
    from sharp.contracts import ConfidenceLevel
    from sharp.career import choice_input
    career.x_resume.confidence_levels = [ConfidenceLevel(id="expert", label="My strongest", definition="I can defend every detail and prefer this", order=0), career.x_resume.confidence_levels[-1]]
    career.x_resume.bullets[0].confidence.level = "expert"
    payload = choice_input(career, settings, "Python")
    assert payload.career.x_resume.confidence_levels[0].id == "expert"
    assert payload.career.x_resume.bullets[1].confidence.level == "unrated"
