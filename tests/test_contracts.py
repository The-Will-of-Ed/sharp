import pytest

from sharp.career import approve_changes, choice_input, confidence_hashes, validate_career
from sharp.contracts import Confidence, Settings
from sharp.selection import validate_plan


def test_default_typography_matches_user_approved_styles():
    styles = Settings().styles
    assert {key for key, style in styles.items() if style.bold} == {
        "name",
        "label",
        "heading",
        "owner",
        "education",
    }
    assert styles["body"].color == "#1A1A1A"
    assert styles["heading"].color == styles["label"].color == "#C44B12"
    assert styles["owner"].color == "#1F5A8A"
    assert styles["bullet"].marker == "•"
    assert styles["bullet"].indent == styles["bullet"].marker_offset == 12


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


@pytest.mark.parametrize(
    "mutation", ["duplicate", "owner", "confidence", "evidence", "qualifier", "variant"]
)
def test_career_reference_validation(career, mutation):
    b = career.x_resume.bullets[0]
    if mutation == "duplicate":
        career.x_resume.bullets.append(b.model_copy())
    if mutation == "owner":
        b.owner_id = "missing"
    if mutation == "confidence":
        b.confidence.level = "made_up"
    if mutation == "evidence":
        b.evidence_ids = ["missing"]
    if mutation == "qualifier":
        career.x_resume.bullets[1].text = "Realized $5M."
    if mutation == "variant":
        from sharp.contracts import Variant

        career.x_resume.bullets[1].variants = [Variant(id="short", text="Realized $5M")]
    with pytest.raises(ValueError):
        validate_career(career)


def test_plan_cannot_invent_or_select_unapproved(career, plan, settings):
    from sharp.contracts import Decision

    plan.ranked.append(Decision(candidate_id="fake"))
    with pytest.raises(ValueError):
        validate_plan(plan, career, settings)
    plan.ranked.pop()
    career.x_resume.bullets[0].approval = "proposed"
    with pytest.raises(ValueError):
        validate_plan(plan, career, settings)


def test_proposal_needs_current_revision_and_preserves_qualifiers(career):
    from sharp.career import digest
    from sharp.contracts import Proposal, ProposedChanges

    proposal = ProposedChanges(
        base_hash=digest(career),
        changes=[Proposal(target_id="w2", text="Realized $5M", evidence_ids=["e1"], qualifiers=[])],
    )
    with pytest.raises(ValueError):
        approve_changes(career, proposal)
    assert "not realized" in career.x_resume.bullets[1].text
    proposal.base_hash = "stale"
    with pytest.raises(ValueError):
        approve_changes(career, proposal)
