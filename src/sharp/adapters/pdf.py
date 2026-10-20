"""PDF measurement and export share exact text runs and font metrics."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from sharp.career import digest
from sharp.contracts import Artifact, Block, Line, Measurement, Style


def font_name(style: Style) -> str:
    variants = {
        "Helvetica": {
            (False, False): "Helvetica",
            (True, False): "Helvetica-Bold",
            (False, True): "Helvetica-Oblique",
            (True, True): "Helvetica-BoldOblique",
        },
        "Times-Roman": {
            (False, False): "Times-Roman",
            (True, False): "Times-Bold",
            (False, True): "Times-Italic",
            (True, True): "Times-BoldItalic",
        },
        "Courier": {
            (False, False): "Courier",
            (True, False): "Courier-Bold",
            (False, True): "Courier-Oblique",
            (True, True): "Courier-BoldOblique",
        },
    }
    if style.font in variants:
        return variants[style.font][style.bold, style.italic]
    path = Path(style.font)
    if path.is_file():
        if style.bold or style.italic:
            raise ValueError(
                "For custom fonts, supply the actual regular/bold/italic font file in the corresponding range"
            )
        name = "sharp_" + digest(str(path.resolve()))[:12]
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(path)))
        return name
    raise ValueError(f"Font unavailable: {style.font}; choose a PDF standard font or a TTF path")


def style_at(block: Block, index: int) -> Style:
    values = block.style.model_dump()
    for run in block.runs:
        if run.start <= index < run.end:
            values.update(run.style)
    return Style.model_validate(values)


def segments(block, start, end):
    current, begin = None, start
    for i in range(start, end):
        style = style_at(block, i)
        if current is not None and style != current:
            yield block.text[begin:i], current
            begin = i
        current = style
    if current is not None:
        yield block.text[begin:end], current


@lru_cache(maxsize=4096)
def _measure(serialized: str, width: float) -> Measurement:
    block = Block.model_validate_json(serialized)
    if width <= 0:
        raise ValueError(f"No usable width for {block.id}")
    # Each character uses its effective range style; long words split safely.
    if not block.runs:
        font = font_name(block.style)
        advances = [pdfmetrics.stringWidth(c, font, block.style.size) for c in block.text]
        tallest = block.style.size
    else:
        advances = []
        tallest = block.style.size
        for i, c in enumerate(block.text):
            s = style_at(block, i)
            tallest = max(tallest, s.size)
            advances.append(pdfmetrics.stringWidth(c, font_name(s), s.size))
    lines, start, n = [], 0, len(block.text)
    while start < n:
        cursor, used, last_space = start, 0.0, None
        while cursor < n and block.text[cursor] != "\n":
            step = advances[cursor]
            if used + step > width + 0.001:
                break
            used += step
            if block.text[cursor].isspace():
                last_space = cursor
            cursor += 1
        if cursor == start and block.text[cursor] != "\n":
            raise ValueError(f"A glyph cannot fit in {block.id}")
        end = cursor
        if (
            cursor < n
            and block.text[cursor] != "\n"
            and last_space is not None
            and last_space > start
        ):
            end = last_space
        visible_end = end
        while visible_end > start and block.text[visible_end - 1].isspace():
            visible_end -= 1
        lines.append(
            Line(
                text=block.text[start:visible_end],
                start=start,
                end=visible_end,
                width=sum(advances[start:visible_end]),
                available_width=width,
            )
        )
        start = end
        if start < n and block.text[start] == "\n":
            start += 1
        else:
            while start < n and block.text[start].isspace() and block.text[start] != "\n":
                start += 1
    if not lines:
        lines = [Line(text="", start=0, end=0, width=0, available_width=width)]
    leading = max(block.style.leading, tallest * 1.15)
    return Measurement(
        block_id=block.id,
        lines=lines,
        height=leading * len(lines),
        fingerprint=digest(
            {"block": json.loads(serialized), "width": width, "backend": "reportlab-v1"}
        ),
    )


class PdfRenderer:
    backend = "reportlab-v1"

    def __init__(self, allowed_font_root=None):
        self.allowed_font_root = (
            Path(allowed_font_root).resolve() if allowed_font_root is not None else None
        )

    def measure(self, block: Block, width: float) -> Measurement:
        if self.allowed_font_root is not None:
            fonts = [block.style.font] + [r.style["font"] for r in block.runs if "font" in r.style]
            for font in fonts:
                if any(c in font for c in ("/", "\\", ":")) and not Path(
                    font
                ).resolve().is_relative_to(self.allowed_font_root):
                    raise ValueError(
                        f"Font path for {block.id} is outside the configured workspace"
                    )
        return _measure(block.model_dump_json(), round(width, 6)).model_copy(deep=True)

    def export(self, layout, settings, destination: str) -> Artifact:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        page = settings.page
        canvas = Canvas(str(path), pagesize=(page.width, page.height), pageCompression=1)
        canvas.setTitle(
            next(
                (p.block.text for p in layout.placed if p.block.kind == "name"),
                "Resume",
            )
        )
        for number in range(1, layout.pages + 1):
            for placed in (p for p in layout.placed if p.page == number):
                b, m = placed.block, placed.measurement
                leading = m.height / len(m.lines)
                for i, line in enumerate(m.lines):
                    x = placed.x
                    baseline = page.height - placed.y - leading * i - leading * 0.8
                    for text, style in segments(b, line.start, line.end):
                        canvas.setFillColor(HexColor(style.color))
                        text_obj = canvas.beginText(x, baseline)
                        name = font_name(style)
                        text_obj.setFont(name, style.size)
                        text_obj.textOut(text)
                        canvas.drawText(text_obj)
                        x += pdfmetrics.stringWidth(text, name, style.size)
                if b.url:
                    canvas.linkURL(
                        b.url,
                        (
                            placed.x,
                            page.height - placed.y - m.height,
                            placed.x + placed.width,
                            page.height - placed.y,
                        ),
                        relative=0,
                    )
            canvas.showPage()
        canvas.save()
        reader = PdfReader(path)
        if len(reader.pages) != layout.pages:
            raise ValueError("Exported page count differs from layout")
        normalized = " ".join(" ".join(p.extract_text() for p in reader.pages).split())
        # Check per measured line, allowing extractor spacing around adjacent styled runs.
        expected_lines = [line.text for p in layout.placed for line in p.measurement.lines]
        compact = "".join(normalized.split())
        if any("".join(line.split()) not in compact for line in expected_lines):
            raise ValueError("PDF text extraction lost or changed content")
        return Artifact(
            path=str(path.resolve()),
            format="pdf",
            checks={
                "pages": len(reader.pages),
                "text": "passed",
                "reading_order": "single-column content order",
            },
        )

    def preview(self, layout, settings, destination: str) -> list[Artifact]:
        output = []
        prefix = Path(destination)
        for number in range(1, layout.pages + 1):
            svg = [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{settings.page.width}" height="{settings.page.height}" viewBox="0 0 {settings.page.width} {settings.page.height}"><rect width="100%" height="100%" fill="white"/>'
            ]
            for p in (p for p in layout.placed if p.page == number):
                for i, line in enumerate(p.measurement.lines):
                    y = p.y + p.measurement.height / len(p.measurement.lines) * (i + 0.8)
                    svg.append(
                        f'<text x="{p.x}" y="{y}" font-family="sans-serif" font-size="{p.block.style.size}" fill="{p.block.style.color}">{escape(line.text)}</text>'
                    )
            svg.append("</svg>")
            target = prefix.with_name(prefix.name + f"-{number}.svg")
            target.write_text("".join(svg), encoding="utf-8")
            output.append(
                Artifact(
                    path=str(target.resolve()),
                    format="svg",
                    checks={"purpose": "approximate lightweight preview; PDF is authoritative"},
                )
            )
        return output

    def png_preview(self, pdf_path: str, destination: str) -> list[Artifact]:
        try:
            import pymupdf as fitz
        except ImportError:
            return []
        result = []
        with fitz.open(pdf_path) as pdf:
            for i, page in enumerate(pdf):
                target = Path(destination).with_name(Path(destination).name + f"-{i + 1}.png")
                page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(str(target))
                result.append(Artifact(path=str(target.resolve()), format="png"))
        return result
