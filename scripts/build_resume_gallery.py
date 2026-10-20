"""Build a portable static gallery from completed runs and saved job snapshots."""
import argparse
import hashlib
import html
import json
import shutil
import zipfile
from pathlib import Path


def build(root):
    root = Path(root).resolve()
    read = lambda path: json.loads(path.read_text(encoding="utf-8"))
    esc = html.escape
    jobs = read(root / "jobs.json")
    career = read(root / "fixture/career.json")
    cards = []
    snapshots = root / "postings"
    snapshots.mkdir(exist_ok=True)
    style = "body{font:16px system-ui;background:#f4f5f7;color:#1a1a1a;margin:32px}h1{margin-bottom:8px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px}article,details{background:white;padding:20px;border:1px solid #ddd;border-radius:8px;margin-bottom:16px}img{width:100%;border:1px solid #eee}h2{margin:0;font-size:20px}p{margin:10px 0}a{color:#1f5a8a}pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5}summary{cursor:pointer}li{margin-bottom:8px}"
    for job in jobs["jobs"]:
        slug = job["slug"]
        posting = root / job["job_path"]
        text = posting.read_text(encoding="utf-8")
        assert hashlib.sha256(text.encode()).hexdigest() == job["job_sha256"], slug
        source = esc(job["url"], quote=True)
        snapshot = f'<meta charset="utf-8"><title>{esc(job["role"])}</title><style>{style}</style><h1>{esc(job["company"])}</h1><h2>{esc(job["role"])}</h2><p>Saved {esc(jobs["retrieved_at"])}. Historical snapshot; current availability may differ.</p><p><a href="{source}">Original source</a></p><pre>{esc(text)}</pre><p>SHA-256: {job["job_sha256"]}</p>'
        (snapshots / f"{slug}.html").write_text(snapshot, encoding="utf-8")
        out = root / "runs" / slug
        result = read(out / "result.json")
        assert result["layout"]["pages"] == 1, slug
        pdf = next(out.glob("*.pdf"))
        dest = root / "resumes" / slug
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf, dest / pdf.name)
        shutil.copy2(out / "preview-1.png", dest / "preview.png")
        href = esc(f"resumes/{slug}/{pdf.name}", quote=True)
        cards.append(f'<article><h2>{esc(job["company"])}</h2><p>{esc(job["role"])}</p><a href="{href}"><img src="resumes/{slug}/preview.png" alt="Resume preview" loading="lazy"></a><p><a href="{href}">Open PDF</a> | <a href="postings/{slug}.html">Saved posting</a> | <a href="{source}">Original source</a></p></article>')
    inventory = []
    for key in ("work", "projects"):
        for owner in career[key]:
            bullets = [b["text"] for b in career["x_resume"]["bullets"] if b["owner_id"] == owner["x_id"]]
            inventory.append(f'<details><summary>{esc(owner["name"])}'+(f' | {esc(owner["position"])}' if owner.get("position") else '')+'</summary><ul>'+''.join(f'<li>{esc(b)}</li>' for b in bullets)+'</ul></details>')
    name = career["basics"]["name"]
    page = f'<!doctype html><meta charset="utf-8"><title>{esc(name)} - 30 Resumes</title><style>{style}</style><h1>{esc(name)} - 30 tailored resumes</h1><p>Single page. Default styling. Click a preview to open its PDF. Saved postings remain readable when employer links disappear.</p><details><summary>Full career inventory: {len(career["work"])} experiences and {len(career["projects"])} projects</summary><p>Resumes select from this inventory; they do not include every record. These PDFs reuse the previous job-specific selections. The two newly added internships are available for future tailoring.</p>'+''.join(inventory)+'</details><p><a href="fixture/master.yaml">Master YAML</a> | <a href="refresh-timing.json">Edit timing report</a></p><div class="grid">'+''.join(cards)+'</div>'
    (root / "index.html").write_text(page, encoding="utf-8")
    with zipfile.ZipFile(root / f"{name} - 30 Resumes.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for folder in ("resumes", "fixture", "job_posts", "postings"):
            for path in (root / folder).rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(root))
        for file in ("index.html", "jobs.json", "refresh-timing.json"):
            archive.write(root / file, file)
    print(root / "index.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    build(parser.parse_args().root)
