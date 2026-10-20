"""Optional Office list metadata; no vendor dependency loads before export."""


def pptx_list(paragraph, style):
    from pptx.oxml.xmlchemy import OxmlElement
    from pptx.util import Pt

    props = paragraph._p.get_or_add_pPr()
    props.set("marL", str(Pt(style.marker_offset)))
    props.set("indent", str(-Pt(style.marker_offset)))
    marker = OxmlElement("a:buChar")
    marker.set("char", style.marker)
    props.append(marker)


def docx_list(doc, paragraph, style, cache):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt

    key = (style.marker, style.indent, style.marker_offset)
    root = doc.part.numbering_part.element

    def node(name, **attrs):
        result = OxmlElement("w:" + name)
        for k, v in attrs.items():
            result.set(qn("w:" + k), str(v))
        return result

    if key not in cache:
        abstract_id = (
            max(
                (int(x.get(qn("w:abstractNumId"))) for x in root.findall(qn("w:abstractNum"))),
                default=-1,
            )
            + 1
        )
        num_id = max((int(x.get(qn("w:numId"))) for x in root.findall(qn("w:num"))), default=0) + 1
        abstract = node("abstractNum", abstractNumId=abstract_id)
        abstract.append(node("multiLevelType", val="singleLevel"))
        level = node("lvl", ilvl=0)
        level.extend(
            [
                node("start", val=1),
                node("numFmt", val="bullet"),
                node("lvlText", val=style.marker),
                node("lvlJc", val="left"),
            ]
        )
        abstract.append(level)
        root.insert(0, abstract)
        number = node("num", numId=num_id)
        number.append(node("abstractNumId", val=abstract_id))
        root.append(number)
        cache[key] = num_id
    numbering = node("numPr")
    numbering.extend([node("ilvl", val=0), node("numId", val=cache[key])])
    paragraph._p.get_or_add_pPr().append(numbering)
    paragraph.paragraph_format.first_line_indent = -Pt(style.marker_offset)
