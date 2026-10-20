import pytest
from sharp.contracts import Career, Settings, Confidence
from sharp.career import validate_career, choice_input, approve_changes, confidence_hashes
from sharp.selection import validate_plan


def test_all_default_styles_are_regular():
    assert all(not x.bold for x in Settings().styles.values())


def test_neutral_unrated(career, settings):
    validate_career(career)
    assert career.x_resume.bullets[1].confidence.level == "unrated"
    payload = choice_input(career, settings, "Python role")
    assert payload.career.x_resume.confidence_levels[-1].id == "unrated"
    assert payload.career.x_resume.bullets[0].confidence.level == "high"
    assert payload.confidence_review["w1"] is True  # imported, not yet revision-attested


def test_review_detects_claim_or_definition_change(career, settings):
    bullet = career.x_resume.bullets[0]
    a, d = confidence_hashes(career, bullet)
    bullet.confidence = Confidence(level="high", assessed_hash=a, definition_hash=d)
    assert choice_input(career, settings, "").confidence_review["w1"] is False
    bullet.text += " With additional scope."
    assert choice_input(career, settings, "").confidence_review["w1"] is True
    bullet.text = bullet.text.removesuffix(" With additional scope.")
    career.x_resume.confidence_levels[1].definition += " Changed meaning."
    assert choice_input(career, settings, "").confidence_review["w1"] is True
    assert bullet.confidence.level == "high"


@pytest.mark.parametrize("mutation", ["duplicate", "owner", "confidence", "evidence", "qualifier", "variant"])
def test_career_reference_validation(career, mutation):
    b = career.x_resume.bullets[0]
    if mutation == "duplicate": career.x_resume.bullets.append(b.model_copy())
    if mutation == "owner": b.owner_id = "missing"
    if mutation == "confidence": b.confidence.level = "made_up"
    if mutation == "evidence": b.evidence_ids = ["missing"]
    if mutation == "qualifier": career.x_resume.bullets[1].text = "Realized $5M."
    if mutation == "variant":
        from sharp.contracts import Variant
        career.x_resume.bullets[1].variants = [Variant(id="short", text="Realized $5M")]
    with pytest.raises(ValueError): validate_career(career)


def test_plan_cannot_invent_or_select_unapproved(career, plan, settings):
    from sharp.contracts import Decision
    plan.ranked.append(Decision(candidate_id="fake"))
    with pytest.raises(ValueError): validate_plan(plan, career, settings)
    plan.ranked.pop()
    career.x_resume.bullets[0].approval = "proposed"
    with pytest.raises(ValueError): validate_plan(plan, career, settings)


def test_proposal_needs_current_revision_and_preserves_qualifiers(career):
    from sharp.contracts import ProposedChanges, Proposal
    from sharp.career import digest
    proposal = ProposedChanges(base_hash=digest(career), changes=[Proposal(target_id="w2", text="Realized $5M", evidence_ids=["e1"], qualifiers=[])])
    with pytest.raises(ValueError): approve_changes(career, proposal)
    assert "not realized" in career.x_resume.bullets[1].text
    proposal.base_hash = "stale"
    with pytest.raises(ValueError): approve_changes(career, proposal)
