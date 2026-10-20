"""Download public official source snapshots, without a browser or credentials.

IDs are fixtures, not permanent openings. Failures must be replaced with real
available postings and new IDs; never silently substitute or synthesize a job.
"""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1] / "outputs/real-jobs-30/sources"
BOARDS = [
    "stripe",
    "airbnb",
    "figma",
    "cloudflare",
    "reddit",
    "discord",
    "datadog",
    "pinterest",
    "dropbox",
]
PAGES = {
    "google-fullstack.html": "https://www.google.com/about/careers/applications/jobs/results/129511213234037446-senior-software-engineer-full-stack-core",
    "google-cloud.html": "https://www.google.com/about/careers/applications/jobs/results/76443197546341062-software-engineer-iii-google-distributed-cloud",
    "amazon-data.html": "https://www.amazon.jobs/en/jobs/10556318/software-development-engineer-ii",
    "amazon-video.html": "https://www.amazon.jobs/en/jobs/10432755/software-development-engineer-ii-amazon-prime-video",
    "apple-distributed.html": "https://jobs.apple.com/en-us/details/200684861/software-engineer-distributed-systems",
}


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    urls = {
        **{
            f"{b}.json": f"https://boards-api.greenhouse.io/v1/boards/{b}/jobs?content=true"
            for b in BOARDS
        },
        **PAGES,
    }

    def fetch(item):
        name, url = item
        with urlopen(
            Request(url, headers={"User-Agent": "SharpResumeBenchmark/0.1 (public job snapshots)"}),
            timeout=45,
        ) as response:
            raw = response.read()
            encoding = response.headers.get_content_charset() or "utf-8"
            text = raw.decode(encoding, errors="strict")
            if name.endswith(".json"):
                json.loads(text)
        (ROOT / name).write_text(text, encoding="utf-8")
        return dict(
            file=name,
            url=url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            raw_sha256=hashlib.sha256(raw).hexdigest(),
            raw_encoding=encoding,
        )

    with ThreadPoolExecutor(max_workers=5) as pool:
        manifest = list(pool.map(fetch, urls.items()))
    (ROOT / "retrieval.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved {len(manifest)} official source snapshots")


if __name__ == "__main__":
    main()
