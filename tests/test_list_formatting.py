"""Visible list markers, hanging geometry and PDF list semantics are one contract."""

import pytest
from pypdf import PdfReader

from sharp.adapters.pdf import PdfRenderer
from sharp.career import prepare_document
from sharp.contracts import Changes, Style, TextRun
from sharp.layout import apply_changes, fit


def test_list_contract_rejects_ambiguous_marker_geometry():
    with pytest.raises(ValueError, match="marker_offset"):
        Style(marker="•", indent=6, marker_offset=12)
    with pytest.raises(ValueError, match="single line"):
        Style(marker="x\ny", indent=12, marker_offset=12)


def test_marker_is_formatting_not_career_wording(career, settings, plan):
    original = career.x_resume.bullets[0].text
    doc = prepare_document(career, settings, plan)
    point = next(b for b in doc if b.id == "w1")
    assert point.text == original and point.style.marker == "•"
    assert not point.style.bold and not point.runs
    settings.styles["bullet"].marker = "-"
    changed = prepare_document(career, settings, plan)
    assert next(b for b in changed if b.id == "w1").style.marker == "-"
    assert career.x_resume.bullets[0].text == original


def test_wrapped_bullet_uses_hanging_indent_and_real_pdf_list(tmp_path, career, settings, plan):
    career.x_resume.bullets[0].text *= 4
    renderer = PdfRenderer()
    layout = fit(prepare_document(career, settings, plan), settings, plan, renderer)
    point = next(p for p in layout.placed if p.block.id == "w1")
    assert len(point.measurement.lines) >= 2
    assert point.x == settings.page.margins[3] + 12
    assert all(line.available_width == point.width for line in point.measurement.lines)
    target = tmp_path / "lists.pdf"
    artifact = renderer.export(layout, settings, str(target))
    assert artifact.checks["list_structure"] == "L/LI/Lbl/LBody"
    pdf = PdfReader(target)
    root = pdf.trailer["/Root"]["/StructTreeRoot"]
    tags = []

    def walk(node):
        if hasattr(node, "get_object"):
            node = node.get_object()
        if isinstance(node, dict):
            if "/S" in node:
                tags.append(str(node["/S"]))
            walk(node.get("/K", []))
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(root)
    count = sum(p.block.kind.endswith("_bullet") for p in layout.placed)
    assert tags.count("/LI") == tags.count("/Lbl") == tags.count("/LBody") == count
    assert "•" in pdf.pages[0].extract_text()
    assert any(
        line.split()[:2] == ["•", "Delivered"] for line in pdf.pages[0].extract_text().splitlines()
    )
    assert "/StructParents" in pdf.pages[0]


def test_explicit_phrase_bold_and_plain_override_still_work(career, settings, plan):
    doc = prepare_document(career, settings, plan)
    changed = apply_changes(
        doc, Changes(runs={"w1": [TextRun(start=0, end=9, style={"bold": True})]})
    )
    assert next(b for b in changed if b.id == "w1").runs[0].style == {"bold": True}
    settings.exceptions["w1"] = {"marker": "", "indent": 0, "marker_offset": 0}
    point = next(b for b in prepare_document(career, settings, plan) if b.id == "w1")
    assert point.style.marker == "" and point.style.indent == 0


@pytest.mark.parametrize("format", ["docx", "pptx"])
def test_optional_exports_have_native_list_metadata(tmp_path, career, settings, plan, format):
    from zipfile import ZipFile

    from sharp.adapters.office import OfficeExporter

    layout = fit(prepare_document(career, settings, plan), settings, plan, PdfRenderer())
    path = tmp_path / f"resume.{format}"
    OfficeExporter(format).export(layout, settings, str(path))
    with ZipFile(path) as z:
        if format == "docx":
            assert b"w:numPr" in z.read("word/document.xml")
            assert "•" in z.read("word/numbering.xml").decode("utf8")
        else:
            assert b"a:buChar" in z.read("ppt/slides/slide1.xml")


def test_list_format_and_palette_are_settings_not_renderer_constants(
    tmp_path, career, settings, plan
):
    from pypdf.generic import ContentStream

    settings.styles["bullet"] = Style(marker="-", indent=20, marker_offset=16, color="#123456")
    settings.styles["heading"].color = "#654321"
    renderer = PdfRenderer()
    layout = fit(prepare_document(career, settings, plan), settings, plan, renderer)
    point = next(p for p in layout.placed if p.block.id == "w1")
    assert point.x == settings.page.margins[3] + 20
    target = tmp_path / "custom.pdf"
    renderer.export(layout, settings, str(target))
    pdf = PdfReader(target)
    assert "-" in pdf.pages[0].extract_text()
    colors = [
        tuple(float(v) for v in args)
        for args, op in ContentStream(pdf.pages[0].get_contents(), pdf).operations
        if op == b"rg"
    ]
    assert any(
        all(abs(a - b) < 1e-5 for a, b in zip(c, (0x12 / 255, 0x34 / 255, 0x56 / 255)))
        for c in colors
    )
    assert any(
        all(abs(a - b) < 1e-5 for a, b in zip(c, (0x65 / 255, 0x43 / 255, 0x21 / 255)))
        for c in colors
    )


def test_two_page_marked_content_resolves_to_the_correct_list_items(
    tmp_path, career, settings, plan
):
    from pypdf.generic import ContentStream

    for bullet in career.x_resume.bullets:
        bullet.text *= 15
    settings.page.max_pages = 2
    settings.constraints.required = [b.id for b in career.x_resume.bullets]
    renderer = PdfRenderer()
    layout = fit(prepare_document(career, settings, plan), settings, plan, renderer)
    assert layout.pages == 2
    path = tmp_path / "two-page-lists.pdf"
    renderer.export(layout, settings, str(path))
    pdf = PdfReader(path)
    nums = pdf.trailer["/Root"]["/StructTreeRoot"]["/ParentTree"]["/Nums"]
    parents = {int(nums[i]): nums[i + 1] for i in range(0, len(nums), 2)}
    for page in pdf.pages:
        mapping = parents[int(page["/StructParents"])]
        marked = []
        for args, op in ContentStream(page.get_contents(), pdf).operations:
            if op == b"BDC":
                role, properties = args
                mcid = int(properties["/MCID"])
                element = mapping[mcid].get_object()
                assert element["/S"] == role and element["/K"] == mcid
                assert element.raw_get("/Pg") == page.indirect_reference
                marked.append(mcid)
        assert sorted(marked) == list(range(len(mapping)))
