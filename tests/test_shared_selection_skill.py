from pathlib import Path

from sharp.adapters.providers import ACPChooser, AgentChooser, LiteLLMChooser, choice_prompt
from sharp.career import choice_input


def test_every_generative_selector_receives_the_host_resume_skill(
    career, settings, plan, monkeypatch
):
    skill = (Path(__file__).parents[1] / "skills/sharp-resume-create/SKILL.md").read_text(
        encoding="utf-8"
    )
    settings.selection_instructions = "User-specific selection guidance."
    request = choice_input(career, settings, "Target posting text")
    prompts = []

    def ask(prompt):
        prompts.append(prompt)
        return plan.model_dump_json()

    AgentChooser(ask).choose(request)

    async def acp_ask(self, prompt):
        return ask(prompt)

    monkeypatch.setattr(ACPChooser, "_ask", acp_ask)
    ACPChooser("unused").choose(request)

    def transport(route, data):
        prompts.append(data["messages"][1]["content"])
        return {"choices": [{"message": {"content": plan.model_dump_json()}}]}

    LiteLLMChooser("http://localhost", "test", transport=transport).choose(request)
    assert len(prompts) == 3
    for prompt in prompts:
        assert skill in prompt
        assert settings.selection_instructions in prompt
        assert request.job in prompt
        assert "ChoicePlan" in prompt
    assert prompts[0] == prompts[1] == prompts[2] == choice_prompt(request)
