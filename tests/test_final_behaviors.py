import json
import os
from pathlib import Path
import pytest
from sharp.contracts import ChoicePlan, Decision, Customization, ProposedChanges, CreateRequest, WriteInput
from sharp.adapters.files import save
from sharp.adapters.pdf import PdfRenderer
from sharp.adapters.providers import AgentWriter
from sharp.career import digest, prepare_document
from sharp.layout import fit
from sharp.workflow import create, reopen_run


def test_later_employer_strong_point_wins_inclusion(career, settings):
    settings.page.height = 270  # 198pt usable: enough for one owner + point, not both.
    career.education = []
    for b in career.x_resume.bullets:
        if b.id in ("w1", "w3"): b.text = "Important evidence and implementation result. " * 3
    plan = ChoicePlan(ranked=[Decision(candidate_id="w3"), Decision(candidate_id="w1")])
    result = fit(prepare_document(career, settings, plan), settings, plan, PdfRenderer())
    assert "w3" in result.selected_ids
    assert "w1" not in result.selected_ids


def test_user_can_prioritize_project_instead(career, settings):
    settings.experience_first = False
    settings.page.height = 280
    career.education = []
    career.x_resume.bullets[0].text = "Useful substantial implementation evidence and ownership. " * 3
    career.x_resume.bullets[3].text = "A critically relevant project and substantial validation. " * 3
    plan = ChoicePlan(ranked=[Decision(candidate_id="p1"), Decision(candidate_id="w1")])
    result = fit(prepare_document(career, settings, plan), settings, plan, PdfRenderer())
    assert "p1" in result.selected_ids
    assert "w1" not in result.selected_ids


def test_no_compiler_needed_to_run_installed_rule(tmp_path):
    from sharp.adapters.rules import RestrictedRules
    compiler = os.environ.get("SHARP_RULE_COMPILER")
    if not compiler: pytest.skip("Set SHARP_RULE_COMPILER for real restricted-runtime tests")
    rule = Customization(id="ok", name="OK", purpose="Installed cache", stage="before_layout", source="function rule(input) {return {};}")
    RestrictedRules(tmp_path, compiler=compiler).install(rule)
    fresh = RestrictedRules(tmp_path, compiler="this-compiler-does-not-exist")
    assert fresh.run(rule, {}) == {}


def test_writer_cannot_change_unrequested_ids(career):
    from sharp.contracts import Proposal
    payload = ProposedChanges(base_hash=digest(career), changes=[Proposal(target_id="w3", text="Changed", evidence_ids=["e1"], qualifiers=[])])
    writer = AgentWriter(lambda _: payload.model_dump_json())
    with pytest.raises(ValueError, match="unrequested"):
        writer.write(WriteInput(career=career, instruction="Improve w1", target_ids=["w1"]))


def test_cover_letter_is_opt_in_and_uses_same_pdf_path(tmp_path, career, settings):
    c, s = tmp_path / "c.json", tmp_path / "s.json"
    save(c, career)
    save(s, settings)
    request = CreateRequest(document_type="cover_letter", career_path=str(c), settings_path=str(s), output_dir=str(tmp_path / "letter"),
                            letter_text="Dear hiring team,\n\nI build reliable software.\n\nAlex Example", title="Cover Letter")
    result = create(request, chooser=None, renderer=PdfRenderer())
    assert result.layout.pages == 1
    assert any("Dear hiring team" in p.block.text for p in result.layout.placed)
    assert not any(p.block.kind == "work_bullet" for p in result.layout.placed)
