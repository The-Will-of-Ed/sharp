import pytest
from sharp.contracts import Career, Settings, ChoicePlan, Decision


@pytest.fixture
def career():
    return Career.model_validate({
        "basics": {"name": "Alex Example", "label": "Software Engineer", "email": "alex@example.com",
                   "profiles": [{"network": "GitHub", "url": "https://github.com/example"}]},
        "work": [{"x_id": "work1", "name": "Example Systems", "position": "Engineer", "startDate": "2022-01"},
                 {"x_id": "work2", "name": "Earlier Systems", "position": "Developer"}],
        "projects": [{"x_id": "project1", "name": "Search prototype"}],
        "education": [{"institution": "Example University", "studyType": "BS", "area": "Computer Science"}],
        "x_resume": {
            "evidence": [{"id": "e1", "source": "User account"}],
            "skills": [{"id": "python", "name": "Python", "evidence_ids": ["e1"]},
                       {"id": "sql", "name": "SQL", "evidence_ids": ["e1"]}],
            "summaries": [{"id": "s1", "text": "I build reliable software.", "approval": "approved", "evidence_ids": ["e1"]}],
            "bullets": [
                {"id": "w1", "owner_id": "work1", "text": "Delivered a Python service that reduced manual review by 70%.",
                 "approval": "approved", "evidence_ids": ["e1"], "skill_ids": ["python"], "confidence": {"level": "high"}},
                {"id": "w2", "owner_id": "work1", "text": "Estimated 10-year value: $5M potential revenue; not realized.",
                 "approval": "approved", "qualifiers": ["Estimated", "10-year", "potential", "not realized"], "evidence_ids": ["e1"]},
                {"id": "w3", "owner_id": "work2", "text": "Built SQL validation for recurring data imports.",
                 "approval": "approved", "evidence_ids": ["e1"], "skill_ids": ["sql"]},
                {"id": "p1", "owner_id": "project1", "text": "Developed a search prototype for technical documentation.",
                 "approval": "approved", "evidence_ids": ["e1"]},
            ]}})


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def plan():
    return ChoicePlan(ranked=[Decision(candidate_id=x) for x in ["p1", "w3", "w1", "w2"]],
                      summary_id="s1", skill_ids=["python", "sql"])
