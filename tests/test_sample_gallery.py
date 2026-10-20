from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.targets.append(value)


def test_public_gallery_links_resolve_without_outputs_or_runtime():
    root = Path(__file__).resolve().parents[1] / "samples/roran-stronghammer"
    for source in [root / "index.html", *sorted((root / "postings").glob("*.html"))]:
        parser = Links()
        parser.feed(source.read_text(encoding="utf-8"))
        for value in parser.targets:
            if urlsplit(value).scheme or value.startswith("#"):
                continue
            target = (source.parent / unquote(urlsplit(value).path)).resolve()
            assert target.is_relative_to(root.resolve()), (source, value)
            assert target.is_file(), (source, value)
            assert "runs" not in target.relative_to(root).parts


def test_public_demo_contains_all_thirty_pairs():
    root = Path(__file__).resolve().parents[1] / "samples/roran-stronghammer"
    assert len(list((root / "resumes").glob("*/*.pdf"))) == 30
    assert len(list((root / "postings").glob("*.html"))) == 30
    assert len(list((root / "job_posts").glob("*.txt"))) == 30
    assert len(list((root / "selections").glob("*.json"))) == 30
