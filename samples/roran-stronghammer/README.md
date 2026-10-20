# Roran StrongHammer sample gallery

Open `index.html` locally. It works without a server. All resume, preview, saved-posting, profile, selection and download links use relative paths.

This checked-in sample is the public demonstration, not a user output directory. New user documents continue to go into ignored `outputs/`.

The current PDFs reuse the earlier 30 job-specific AI selections. The two added internships are present in the master inventory but were not part of that selection run. `refresh-timing.json` measures the subsequent no-inference edit/export pass, not AI tailoring.

## Publish

Push this repository as `The-Will-of-Ed/sharp`. In repository Settings > Pages, choose GitHub Actions as the source. The Pages workflow publishes only this sample folder. The intended public gallery URL is:

https://the-will-of-ed.github.io/sharp/

It is not live until the repository is pushed and deployment succeeds. Source repository:

https://github.com/The-Will-of-Ed/sharp

Saved job postings include retrieval timestamps, original source URLs and content hashes. They are historical snapshots, not claims that roles remain open. External sources and candidate profile URLs can change; local saved postings and resumes are self-contained.

`runs/` contains optional local execution checkpoints and is ignored. Public `selections/` retains the chosen IDs without requiring those checkpoints. The ZIP contains the same public gallery assets and does not include execution checkpoints.
