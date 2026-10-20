import json
import sys
import yaml
from pypdf import PdfReader
from sharp.contracts import CreateRequest
from sharp.workflow import create, reopen_run
from sharp.adapters.pdf import PdfRenderer


def test_pdf_links_reading_order_and_saved_run(tmp_path, career, settings, plan):
    master = tmp_path / "master.yaml"
    config = tmp_path / "settings.local.yaml"
    master.write_text(yaml.safe_dump(career.model_dump()), encoding="utf-8")
    config.write_text(yaml.safe_dump(settings.model_dump()), encoding="utf-8")
    before = master.read_bytes()
    def fail_choose(_): raise AssertionError("Selection should not be called")
    result = create(CreateRequest(career_path=str(master), settings_path=str(config), output_dir=str(tmp_path / "out")),
                    chooser=fail_choose, renderer=PdfRenderer(), supplied_plan=plan)
    pdf = next(a for a in result.artifacts if a.format == "pdf")
    reader = PdfReader(pdf.path)
    text = "\n".join(p.extract_text() for p in reader.pages)
    assert len(reader.pages) == 1
    assert text.index("Alex Example") < text.index("EXPERIENCE") < text.index("PROJECTS")
    assert "not realized" in text
    assert any("https://github.com/example" == a.get_object().get("/A", {}).get("/URI") for a in reader.pages[0].get("/Annots", []))
    assert master.read_bytes() == before
    reopened = reopen_run(tmp_path / "out", renderer=PdfRenderer(), changes={"styles.body.size": 9.5})
    assert reopened.layout.pages == 1
    assert json.loads((tmp_path / "out" / "selection.json").read_text())["provider"] == "user"


def test_package_import_has_no_optional_dependencies():
    import subprocess
    result = subprocess.run([sys.executable, "-c", "import sharp; import sys; assert not any(x in sys.modules for x in ['extism','pptx','docx','acp','mcp','litellm'])"], check=False)
    assert result.returncode == 0
