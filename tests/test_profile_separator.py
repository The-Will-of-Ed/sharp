"""Configurable link grouping must preserve each destination through wrapping/exports."""

import zipfile
from xml.etree import ElementTree as ET

import pytest
from pypdf import PdfReader

from sharp.adapters.office import OfficeExporter
from sharp.adapters.pdf import PdfRenderer
from sharp.career import prepare_document
from sharp.contracts import Settings
from sharp.layout import fit


def add_profiles(career):
    urls = [
        "https://github.com/alex-public",
        "https://linkedin.com/in/alex-public",
        "https://alex-public.dev",
    ]
    career.basics["profiles"] = [{"url": url} for url in urls]
    return urls


def test_default_preserves_separate_link_blocks(career, plan):
    urls = add_profiles(career)
    blocks = [b for b in prepare_document(career, Settings(), plan) if b.id.startswith("profile:")]
    assert [b.url for b in blocks] == urls
    assert [b.text for b in blocks] == urls


@pytest.mark.parametrize("separator", [" | ", " ", "\t", " / ", ""])
def test_custom_separator_and_destinations(career, settings, plan, separator):
    urls = add_profiles(career)
    settings.profile_separator = separator
    blocks = prepare_document(career, settings, plan)
    block = next(b for b in blocks if b.id == "profiles")
    assert block.text == separator.expandtabs().join(urls)
    assert [block.text[link.start : link.end] for link in block.links] == urls
    assert [link.url for link in block.links] == urls
    assert not [b for b in blocks if b.id.startswith("profile:")]


@pytest.mark.parametrize("width", [532, 130])
def test_wrapped_links_remain_separate_in_pdf_and_office(career, settings, plan, tmp_path, width):
    urls = add_profiles(career)
    settings.profile_separator = " | "
    settings.page.width = width + settings.page.margins[1] + settings.page.margins[3]
    # Only the header is needed to exercise link wrapping, independent of evidence fitting.
    blocks = [b for b in prepare_document(career, settings, plan) if b.kind == "contact"]
    renderer = PdfRenderer()
    layout = fit(blocks, settings, plan.model_copy(update={"ranked": []}), renderer)
    pdf = tmp_path / "links.pdf"
    renderer.export(layout, settings, str(pdf))
    page = PdfReader(pdf).pages[0]
    annotations = [a.get_object() for a in page.get("/Annots", [])]
    assert {a["/A"]["/URI"] for a in annotations} == set(urls)
    for annotation in annotations:
        assert annotation["/Rect"][2] > annotation["/Rect"][0]
    if width == 130:
        assert len(next(p for p in layout.placed if p.block.id == "profiles").measurement.lines) > 1
        assert len(annotations) > len(urls)
    for format in ["docx", "pptx"]:
        target = tmp_path / ("links." + format)
        OfficeExporter(format).export(layout, settings, str(target))
        with zipfile.ZipFile(target) as archive:
            links = {
                r.attrib["Target"]
                for name in archive.namelist()
                if name.endswith(".rels")
                for r in ET.fromstring(archive.read(name))
                if r.attrib["Type"].endswith("/hyperlink")
            }
        assert links == set(urls)


def test_empty_profiles_do_not_emit_a_block(career, settings, plan):
    career.basics["profiles"] = [{"url": ""}, {}]
    settings.profile_separator = " | "
    assert not any(b.id == "profiles" for b in prepare_document(career, settings, plan))


@pytest.mark.parametrize("start,end", [(2, 1), (0, 20)])
def test_invalid_inline_link_ranges_are_rejected(start, end):
    from sharp.contracts import Block

    with pytest.raises(ValueError, match="Link range outside"):
        Block(
            id="link",
            kind="contact",
            text="short",
            links=[{"start": start, "end": end, "url": "https://alex-public.dev"}],
        )
