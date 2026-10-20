import json
from pathlib import Path
import pytest
import yaml
from sharp.contracts import (ChoicePlan, Decision, Constraints, Customization, Settings, CreateRequest,
                             ProposedChanges, Proposal, Career)
from sharp.career import prepare_document, validate_career, approve_changes, digest
from sharp.layout import fit
from sharp.adapters.pdf import PdfRenderer
from sharp.adapters.files import save, validate_standard
from sharp.workflow import create, reopen_run


def write_inputs(tmp_path, career, settings):
    c, s = tmp_path / "career.json", tmp_path / "settings.json"
    save(c, career)
    save(s, settings)
    return CreateRequest(career_path=str(c), settings_path=str(s), output_dir=str(tmp_path / "out"))


def test_before_hook_can_require_unranked_approved_point(career, settings):
    plan = ChoicePlan(ranked=[Decision(candidate_id="w1")])
    document = prepare_document(career, settings, plan)
    settings.constraints.required = ["w3"]
    result = fit(document, settings, plan, PdfRenderer())
    assert "w3" in result.selected_ids
    assert "p1" not in result.selected_ids


def test_duplicate_document_ids_are_rejected(career, settings):
    career.x_resume.bullets[0].id = "name"
    with pytest.raises(ValueError, match="Duplicate document"):
        prepare_document(career, settings, ChoicePlan(ranked=[Decision(candidate_id="name")]))


def test_approved_text_requires_at_least_user_attestation(career):
    proposal = ProposedChanges(base_hash=digest(career), changes=[Proposal(target_id="w1", text="Improved service.", qualifiers=[], evidence_ids=[])])
    with pytest.raises(ValueError, match="evidence"): approve_changes(career, proposal)


def test_volunteer_organization_is_preserved(career, settings):
    career.volunteer = [{"x_id": "school", "organization": "Community School", "position": "Teacher"}]
    career.x_resume.bullets[3].owner_id = "school"
    document = prepare_document(career, settings, ChoicePlan(ranked=[Decision(candidate_id="p1")]))
    assert any(b.kind == "owner" and "Community School" in b.text for b in document)


def test_failed_regeneration_preserves_previous_complete_run(tmp_path, career, settings, plan):
    request = write_inputs(tmp_path, career, settings)
    first = create(request, chooser=None, renderer=PdfRenderer(), supplied_plan=plan)
    snapshot = (Path(first.output_dir) / "result.json").read_bytes()
    career.x_resume.bullets[0].text *= 1000
    settings.constraints.required = ["w1"]
    save(request.career_path, career)
    save(request.settings_path, settings)
    with pytest.raises(ValueError, match="fit"): create(request, chooser=None, renderer=PdfRenderer(), supplied_plan=plan)
    assert (Path(first.output_dir) / "result.json").read_bytes() == snapshot


def test_refit_does_not_repeat_selection_hook(tmp_path, career, settings, plan):
    settings.customizations = [Customization(id="reverse", name="Reverse", purpose="Test state reuse", stage="selection", source="function rule(input) {return input.plan;}")]
    class Runner:
        def __init__(self): self.calls = 0
        def run(self, rule, payload):
            self.calls += 1
            result = payload["plan"]
            result["ranked"] = list(reversed(result["ranked"]))
            return result
    runner = Runner()
    request = write_inputs(tmp_path, career, settings)
    first = create(request, chooser=None, renderer=PdfRenderer(), supplied_plan=plan, rule_runner=runner)
    previous = (Path(first.output_dir) / "selection.json").read_bytes()
    reopen_run(first.output_dir, renderer=PdfRenderer(), changes={"styles.body.size": 9.5}, rule_runner=runner)
    assert runner.calls == 1
    assert (Path(first.output_dir) / "selection.json").read_bytes() == previous


def test_hooks_receive_latest_state(tmp_path, career, settings, plan):
    settings.customizations = [Customization(id=f"r{i}", name=f"Rule {i}", purpose="Fresh inputs", stage="before_layout", source="function rule(input) {return {};}") for i in range(2)]
    class Runner:
        def run(self, rule, payload):
            name = next(b for b in payload["document"] if b["id"] == "name")
            if rule.id == "r1": assert name["style"]["color"] == "#0000ff"
            return {"patches": {"name": {"color": "#0000ff"}}}
    create(write_inputs(tmp_path, career, settings), chooser=None, renderer=PdfRenderer(), supplied_plan=plan, rule_runner=Runner())


def test_standard_core_rejects_invalid_types(career):
    career.basics["email"] = 1234
    with pytest.raises(ValueError, match="JSON Resume"): validate_standard(career)


def test_excluded_high_confidence_never_bypasses_constraint(career, settings, plan):
    career.x_resume.bullets[3].confidence.level = "very_high"
    settings.constraints.excluded = ["p1"]
    result = fit(prepare_document(career, settings, plan), settings, plan, PdfRenderer())
    assert "p1" not in result.selected_ids
