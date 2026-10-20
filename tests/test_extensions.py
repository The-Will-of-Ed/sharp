import json
import os
from pathlib import Path
import pytest
from sharp.contracts import Customization, ChoicePlan
from sharp.adapters.rules import RestrictedRules
from sharp.adapters.files import SettingsFile, import_material, export_json_resume
from sharp.career import digest


def test_settings_atomic_revision_and_exceptions(tmp_path, settings):
    file = SettingsFile(tmp_path / "settings.local.yaml")
    file.initialize(settings)
    before = file.read()
    file.update({"exceptions.w1": {"bold": True}}, expected_hash=digest(before))
    with pytest.raises(ValueError, match="revision"): file.update({"skills_fill_target": 0.8}, expected_hash=digest(before))
    current = file.read()
    changed = file.update({"styles.body.bold": False}, expected_hash=digest(current))
    assert changed.exceptions["w1"]["bold"] is True
    changed = file.update({"styles.body.bold": False}, expected_hash=digest(changed), apply_everywhere=True)
    assert "bold" not in changed.exceptions.get("w1", {})


def test_portable_settings_do_not_export_private_paths(tmp_path, settings):
    settings.styles["body"].font = "C:/private/fonts/font.ttf"
    file = SettingsFile(tmp_path / "settings.local.yaml")
    file.initialize(settings)
    with pytest.raises(ValueError, match="portable|font"): file.portable()


def test_import_material_reads_documents_not_fabricates_career(tmp_path):
    p = tmp_path / "notes.txt"
    p.write_text("I built a Python prototype.", encoding="utf-8")
    records = import_material([str(p)])
    assert records[0]["text"] == "I built a Python prototype."
    assert records[0]["content_hash"]
    assert "confidence" not in records[0]


def test_standard_export_materializes_highlights_once(career, plan):
    exported = export_json_resume(career, plan)
    assert "x_resume" not in exported
    assert "Delivered a Python" in exported["work"][0]["highlights"][0]
    assert not any("x_id" in w for w in exported["work"])


def compiler():
    path = os.environ.get("SHARP_RULE_COMPILER")
    if not path: pytest.skip("Set SHARP_RULE_COMPILER for real restricted-runtime tests")
    return path


def test_real_restricted_rule_and_compilation_cache(tmp_path):
    runner = RestrictedRules(tmp_path, compiler=compiler())
    rule = Customization(id="blue", name="Blue", purpose="Color name", stage="after_layout",
                         source='function rule(input) { return {colors:{name:"#0000ff"}}; }')
    runner.install(rule)
    artifact = runner.artifact(rule)
    timestamp = artifact.stat().st_mtime_ns
    assert runner.run(rule, {}) == {"colors": {"name": "#0000ff"}}
    runner.install(rule)
    assert artifact.stat().st_mtime_ns == timestamp


@pytest.mark.parametrize("source", [
    'function rule(input) { return require("fs").readFileSync("master.yaml"); }',
    'function rule(input) { return Http.request({url:"https://example.com"}); }',
    'function rule(input) { while(true) {} }',
    'function rule(input) { return {x:"x".repeat(2000000)}; }',
])
def test_restricted_rule_rejects_io_hangs_and_oversize(tmp_path, source):
    runner = RestrictedRules(tmp_path, compiler=compiler(), timeout_ms=100, max_output=10000)
    rule = Customization(id="bad", name="Bad", purpose="Boundary test", stage="before_layout", source=source)
    runner.install(rule)
    with pytest.raises(ValueError): runner.run(rule, {})


def test_rules_do_not_retain_cross_run_state(tmp_path):
    runner = RestrictedRules(tmp_path, compiler=compiler())
    rule = Customization(id="state", name="State", purpose="Isolation test", stage="before_layout",
                         source='function rule(input) { const old=Var.getString("n"); Var.set("n","yes"); return {reason:old || "empty"}; }')
    runner.install(rule)
    assert runner.run(rule, {}) == runner.run(rule, {}) == {"reason": "empty"}
