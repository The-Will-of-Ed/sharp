"""Standard PDF structure tags, isolated from composition and layout.

Marks every text block and groups adjacent bullet blocks into L/LI/Lbl/LBody.
Does not claim PDF/UA certification or change text/geometry. PDF role names are
standard semantic identifiers, not typography or layout defaults.
"""

from collections import defaultdict
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, BooleanObject, DictionaryObject, NameObject, NumberObject
from reportlab.pdfbase import pdfmetrics


class TaggedContent:
    def __init__(self):
        self.counts = defaultdict(int)
        self.blocks = []

    def add(self, page, kind, marker):
        is_list = kind.endswith("_bullet") or marker
        role = "LBody" if is_list else {"name": "H1", "heading": "H2"}.get(kind, "P")
        label = self.counts[page] if marker else None
        self.counts[page] += bool(marker)
        body = self.counts[page]
        self.counts[page] += 1
        self.blocks.append((page, is_list, label, role, body))
        return label, (role, body)

    def attach(self, path):
        writer = PdfWriter()
        writer.clone_document_from_reader(PdfReader(BytesIO(path.read_bytes())))
        # ReportLab's Type1 vector includes glyph assignments that differ from
        # a reader's default WinAnsi lookup. Preserve the actual vector so list
        # labels (and other glyphs) remain Unicode text during extraction.
        seen = set()
        for page in writer.pages:
            for ref in page["/Resources"].get("/Font", {}).values():
                font = ref.get_object()
                base = str(font.get("/BaseFont", "")).lstrip("/")
                if (
                    base in seen
                    or font.get("/Subtype") != "/Type1"
                    or font.get("/Encoding") != "/WinAnsiEncoding"
                ):
                    continue
                seen.add(base)
                vector = pdfmetrics.getFont(base).encoding.vector
                differences = ArrayObject()
                for code, glyph in enumerate(vector):
                    if glyph:
                        differences.extend([NumberObject(code), NameObject("/" + glyph)])
                font[NameObject("/Encoding")] = DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/Encoding"),
                        NameObject("/BaseEncoding"): NameObject("/WinAnsiEncoding"),
                        NameObject("/Differences"): differences,
                    }
                )
        structure = DictionaryObject({NameObject("/Type"): NameObject("/StructTreeRoot")})
        structure_ref = writer._add_object(structure)
        structure[NameObject("/K")] = ArrayObject()

        def element(role, parent, page=None, mcid=None):
            obj = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/StructElem"),
                    NameObject("/S"): NameObject("/" + role),
                    NameObject("/P"): parent,
                }
            )
            obj[NameObject("/K")] = ArrayObject() if mcid is None else NumberObject(mcid)
            if page is not None:
                obj[NameObject("/Pg")] = writer.pages[page].indirect_reference
            ref = writer._add_object(obj)
            parent.get_object()["/K"].append(ref)
            return ref

        document = element("Document", structure_ref)
        parents = {i: ArrayObject([None] * count) for i, count in self.counts.items()}
        current_list = None
        previous_page = None
        for page, is_list, label, role, body in self.blocks:
            if is_list:
                if current_list is None or page != previous_page:
                    current_list = element("L", document)
                item = element("LI", current_list, page)
                if label is not None:
                    parents[page][label] = element("Lbl", item, page, label)
                parents[page][body] = element("LBody", item, page, body)
            else:
                current_list = None
                parents[page][body] = element(role, document, page, body)
            previous_page = page
        nums = ArrayObject()
        for page, items in sorted(parents.items()):
            assert all(item is not None for item in items)
            writer.pages[page][NameObject("/StructParents")] = NumberObject(page)
            nums.extend([NumberObject(page), items])
        structure[NameObject("/ParentTree")] = writer._add_object(
            DictionaryObject({NameObject("/Nums"): nums})
        )
        structure[NameObject("/ParentTreeNextKey")] = NumberObject(len(writer.pages))
        writer.root_object[NameObject("/StructTreeRoot")] = structure_ref
        writer.root_object[NameObject("/MarkInfo")] = DictionaryObject(
            {NameObject("/Marked"): BooleanObject(True)}
        )
        with path.open("wb") as stream:
            writer.write(stream)
