# One career. Thirty real jobs.

This document records the original historical run with Morgan Ellis. The current generator and reusable fixture now use Roran StrongHammer with six employment records and two education records. Rerunning the current scripts therefore uses different input. Older generated output folders were intentionally removed; their raw run artifacts are not distributed with this repository. The current portable gallery, saved jobs, selections and no-inference refresh timings are under `samples/roran-stronghammer/`.

This is a selection and generation demonstration with a wholly invented person,
not a candidate success story. No personal resume data is used. Morgan Ellis has
nine years across four fictional employment records, including an explicitly
fictional IBM role. Smaller employers and the educational institution are made
up. The source contains 31 work achievements, 14 projects, 49 skills and four
approved summaries. The current successor sample is in
`examples/fictional-senior-engineer/master.yaml`; it differs from this original fixture.

Thirty distinct employer-published jobs were collected on October 20, 2026 from
Google, Amazon, Apple, Stripe, Airbnb, Figma, Cloudflare, Reddit, Discord,
Datadog, Pinterest and Dropbox. Full descriptions were obtained from official
career pages and official Greenhouse feeds. Removed search results were excluded.
Jobs may later close; saved descriptions, IDs, URLs and normalized-text hashes
remain in the local benchmark package.

## Observed results

| Measure | Result |
|---|---:|
| Final single-page resumes | 30 |
| Different final bullet sets | 30 |
| Median generation per job | 27.04 seconds |
| Range, including all attempts per job | 18.29-46.44 seconds |
| Batch elapsed, up to three concurrent workers | 348.03 seconds |
| First-attempt generation successes | 29/30 |
| Total model calls, including retry | 31 |
| Median layout computation | 38.6 milliseconds |
| Median PDF export and preview | 133.1 milliseconds |
| Final PDFs passing content/geometry checks | 30/30 |

Each job used actual Codex inference through codex-acp 2.2.2, the existing
authenticated Codex installation, gpt-6-sol and medium reasoning. No new Codex
CLI was installed. Existing subscription access is not free inference; token
usage and monetary costs were not measured.

The career was frozen before inference and its SHA-256 remained unchanged.
One response contained an undefined requirement ID. Validation rejected it;
the original attempt and a successful retry are both included in timing.
An unrelated Windows extended-path error affected one benchmark report after
successful generation. Its PDF was recovered and audited without a model call.
The raw records retain both incidents.

Generation timing starts with ready career data and a collected posting. It
includes ACP process/session startup, model choice, fit, PDF export and artifact
checks. The batch spans first selection start to final export, including the
operator pause before the retry. Profile authoring, job collection, subsequent
visual review, marketing-image creation and interpreter startup are excluded.

## What the evidence demonstrates

A separate AI reviewer defined five themes per example job from its posting and
the fixed fixture before looking at selections. The five example jobs cover
Google full-stack, Amazon data systems, Apple distributed systems, Stripe SDKs
and Figma developer experience. All 25 themes have direct work evidence in the
final PDFs. This is a limited relevance check, not an ATS score, complete
qualification assessment, human study, global optimality proof or hiring claim.

All 30 PDFs were checked for one page, exact approved bullet wording, approved
summary and skills, text extraction, single-column reading order, margin bounds,
fictional disclosure and unchanged career source. Five full-size previews and
an overview of all 30 were reviewed visually. The marketing image presents five
varied examples rather than the five fastest cases.

Gaps remain visible: Figma's Bazel/monorepo experience, Apple's hyperscale,
Google Distributed Cloud's hardware/GPU diagnostics, and Prime Video's media
testing are not present in this profile. No such experience was invented.
All confidence assessments are neutral, and there are no shorter bullet
variants, so those features were not evaluated. The skills-line 95% target was
met in only 4/30 outputs; aesthetic fill warnings are retained separately from
correctness checks. Relevant work is prioritized over side projects.

## Manual comparison

Assume **20 minutes per tailored resume**, starting with ready profile/job text.
That is **10 hours for 30**, versus the observed **5 minutes 48 seconds** with
up to three concurrent workers. This is a modeled 103.4x batch throughput
comparison, not a measured human result. The per-resume comparison against the
27.04-second median is 44.4x. Always present the assumption with the number.

## Reproduce without changing production code

Use Sharp's own `.venv` and an existing authenticated native Codex executable.
The ACP adapter is installed separately; do not install a new Codex CLI.

1. `python scripts/fetch_real_job_sources.py` downloads official source snapshots.
2. `python scripts/prepare_real_jobs_benchmark.py` creates the fictional fixture
   and 30 job files. It fails on missing/removed jobs; update genuine job IDs
   rather than replacing a real posting with invented text.
3. Run `scripts/run_real_jobs_benchmark.py --help`, supplying `--root
   outputs/real-jobs-30`, `--adapter`, `--codex`, `--node` and `--workers 3`.
   Native Codex needs access to its existing local session-state directory.
4. If a response fails validation, preserve its report as
   `<slug>.first-attempt.json`, then retry with `--only <slug>`. The audit counts
   the failed attempt rather than discarding it.
5. `python scripts/audit_real_jobs_benchmark.py` audits existing outputs and
   creates the share folder, sales image/PDF and ZIP. It does not call AI or
   regenerate resumes.

Outputs are under `outputs/real-jobs-30/` and remain Git-ignored. The share folder
excludes machine paths and private agent logs. A new run produces local records for diagnostics; the original historical records are not shipped. The benchmark scripts are outside the production
domain, layout and adapter layers.
