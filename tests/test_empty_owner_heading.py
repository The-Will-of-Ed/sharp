import pytest

from sharp.career import prepare_document


@pytest.mark.parametrize("name", ["", "   ", "Search prototype"])
def test_project_heading_only_exists_for_nonempty_display_text(career, settings, plan, name):
    career.projects[0]["name"] = name
    blocks = prepare_document(career, settings, plan)
    assert any(b.id == "owner:project1" for b in blocks) == bool(name.strip())
    assert any(b.id == "p1" for b in blocks)
    assert any(b.id == "heading:projects" and b.text == "PROJECTS" for b in blocks)
    assert any(b.id == "owner:work1" for b in blocks)
