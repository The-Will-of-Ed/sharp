"""Cache a job once. No browser automation or model call for ordinary HTML."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sharp.career import digest


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.hidden += 1
        if tag in ("p", "div", "li", "h1", "h2", "h3", "br"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def job_text(source: str, cache: str | Path) -> str:
    if not source.startswith(("https://", "http://")):
        return source
    url = urlparse(source)
    if url.username or url.password:
        raise ValueError("Job URLs must not embed credentials")
    folder = Path(cache)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (digest(source) + ".txt")
    if target.exists():
        return target.read_text(encoding="utf-8")
    request = Request(source, headers={"User-Agent": "SharpResume/0.1 (job text import)"})
    with urlopen(request, timeout=10) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Job page exceeds 2 MB; paste the posting instead")
        content_type = response.headers.get_content_type()
        text = raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    if content_type == "text/html":
        parser = TextParser()
        parser.feed(text)
        text = "\n".join(
            " ".join(line.split()) for line in "".join(parser.parts).splitlines() if line.strip()
        )
    if len(text.strip()) < 80:
        raise ValueError(
            "Job page has too little readable text; paste the posting from your browser"
        )
    target.write_text(text, encoding="utf-8")
    target.with_suffix(".url").write_text(source, encoding="utf-8")
    return text
