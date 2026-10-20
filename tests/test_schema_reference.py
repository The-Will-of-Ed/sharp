import pytest
from jsonschema import Draft202012Validator, ValidationError
from sharp.service import contracts
from sharp.career import choice_input


def test_discovered_career_schema_contains_standard_core_fields():
    schemas = contracts()
    work = schemas["Career"]["properties"]["work"]["items"]
    assert work["properties"]["position"]["type"] == "string"
    assert "x_id" in work["required"]
    assert schemas["Career"]["properties"]["x_resume"]["description"]


def test_nested_choice_schema_enforces_standard_core_types(career, settings):
    data = choice_input(career, settings, "Python").model_dump(by_alias=True)
    data["career"]["basics"]["email"] = 1234
    with pytest.raises(ValidationError):
        Draft202012Validator(contracts()["ChoiceInput"]).validate(data)
