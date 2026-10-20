import pytest

from sharp.adapters.files import save
from sharp.adapters.pdf import PdfRenderer
from sharp.career import choice_input, confidence_hashes, prepare_document, validate_career
from sharp.contracts import Confidence, CreateRequest, Variant
from sharp.layout import fit
from sharp.workflow import create, reopen_run


def test_invalid_font_is_not_hidden_as_does_not_fit(career, settings, plan):
    settings.exceptions = {"w1": {"font": "DOES_NOT_EXIST"}}
    with pytest.raises(ValueError, match="Font unavailable"):
        fit(prepare_document(career, settings, plan), settings, plan, PdfRenderer())


def test_approved_summary_requires_source(career):
    career.x_resume.summaries[0].evidence_ids = []
    with pytest.raises(ValueError, match="evidence"):
        validate_career(career)


def test_variant_edit_requires_confidence_reassessment(career, settings):
    b = career.x_resume.bullets[0]
    b.variants = [Variant(id="short", text="Delivered a Python service.")]
    a, d = confidence_hashes(career, b)
    b.confidence = Confidence(level="high", assessed_hash=a, definition_hash=d)
    assert not choice_input(career, settings, "").confidence_review[b.id]
    b.variants[0].text = "Led an entirely different system."
    assert choice_input(career, settings, "").confidence_review[b.id]


def test_refit_recomposes_structure_and_preserves_exceptions(tmp_path, career, settings, plan):
    settings.exceptions = {"w1": {"size": 12}}
    settings.constraints.excluded = ["p1"]
    c, s = tmp_path / "c.json", tmp_path / "s.json"
    save(c, career)
    save(s, settings)
    request = CreateRequest(
        career_path=str(c), settings_path=str(s), output_dir=str(tmp_path / "out")
    )
    first = create(request, chooser=None, renderer=PdfRenderer(), supplied_plan=plan)
    second = reopen_run(
        first.output_dir,
        renderer=PdfRenderer(),
        changes={
            "styles.bullet.size": 9,
            "section_order": ["summary", "projects", "work", "education", "skills"],
            "constraints.excluded": [],
        },
    )
    blocks = [p.block for p in second.layout.placed]
    assert next(b for b in blocks if b.id == "w1").style.size == 12
    ids = [b.id for b in blocks]
    assert ids.index("heading:projects") < ids.index("heading:work")
    assert "p1" in second.layout.selected_ids
    third = reopen_run(first.output_dir, renderer=PdfRenderer(), changes={"exceptions": {}})
    assert next(p.block for p in third.layout.placed if p.block.id == "w1").style.size == 9
