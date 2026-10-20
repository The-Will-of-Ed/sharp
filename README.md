<p align="center">
  <img src="assets/SHARP-FULL-SIGNATURE.svg" alt="Sharp" width="560">
</p>

# Show every employer why you're right for their job.

**A custom resume in ~27 seconds. 8+ per minute in parallel.** [Measured with AI inference included.](#the-numbers)

Already using Claude Code or Codex? **Keep them.** Sharp handles the fitting, checks, and preferences you would otherwise have to manage yourself.

**FREE SOFTWARE | OPEN SOURCE | ATS-FRIENDLY | CUSTOMIZABLE**

[**See 30 real-job examples**](https://the-will-of-ed.github.io/sharp/) | [**Get Sharp free on GitHub**](https://github.com/The-Will-of-Ed/sharp) | [**Download the examples**](samples/roran-stronghammer/Roran%20StrongHammer%20-%2030%20Resumes.zip)

## Your best points. For that specific job.

You've done a lot. One resume cannot show all of it. Sharp gives your agent a reusable inventory of your experience, projects, and skills so it can choose the strongest relevant evidence for each application.

- **No AI-invented achievements in selection.** Only approved career evidence can be selected. New wording is proposed separately for review, so tailoring does not quietly rewrite your history. You should never have to explain an achievement the AI made up.
- **The page limit is enforced. The space is measured.** Choose one or two pages. Sharp fits ranked evidence within your margins and reports actual fill. Our 30-resume sample reached **96-98.9% page fill**. Fill targets are measured goals; missing space is reported rather than padded with invented content.
- **Your choices stay.** Required achievements, exclusions, supporting-point dependencies, approved wording, margins, and formatting exceptions persist across applications. The harness enforces saved constraints during generation instead of relying on the agent to remember a prompt.
- **Edit without starting over.** Change formatting without changing approved content or rerunning AI. Recent one-page formatting edits took **0.44 seconds median** locally.
- **Multiple resumes in parallel.** The ten-worker benchmark completed **30 in 3m40s**, including retries: **8.2 per minute**, equivalent to about **7.35 seconds of batch time per completed resume**. Individual resumes still took about 28 seconds median.
- **Checked PDFs, editable when needed.** Single-column, selectable text, reading-order checks, real bullet markers, and clickable links. PDF is the checked default; request editable Word or PowerPoint only when you need them.
- **Your agent. Your files.** Use the current agent through MCP, the matching CLI, or an optional provider adapter. Career data, preferences, and generated runs stay in local Git-ignored files by default. Connected inference providers still receive the inputs needed for their work.

## Start with the agent you already use

Clone or download this repository and open it in Claude Code or Codex. Then say:

> Follow AGENTS.md and docs/SETUP.md. Set up Sharp in its own environment, connect its MCP tools, and verify them. Read the resumes and notes I point you to, consolidate them into one proposed career master, and show me before applying changes. Keep my originals unchanged and my data out of Git.

Then paste a posting or give its URL:

> Make a one-page resume for this job from my approved career evidence. Keep my saved preferences, inspect the fit and PDF preview, and give me the finished file.

For edits:

> Increase the section spacing and put my profile links on one line with a bar between them. Keep the selected content unchanged. Refit and check the PDF.

**Needs:** Git, Python 3.12+, and your installed, signed-in agent. No separate model API key is required when your current agent makes the choices. Host permissions or an MCP restart may be needed during setup.

[Full setup: Windows, macOS, and Linux](docs/SETUP.md) | [CLI, editing, settings, and exports](docs/USAGE.md) | [Try the no-AI demo](docs/USAGE.md#try-it)

## Explore before installing

[**Open the gallery**](https://the-will-of-ed.github.io/sharp/)

Browse **30 single-page resumes for real postings across 12 companies**: Google, Amazon, Apple, Stripe, Airbnb, Figma, Cloudflare, Reddit, Discord, Datadog, Pinterest, and Dropbox.

Each example links to its PDF, preview, saved posting, and original employer source. The gallery includes the full sample career inventory. Saved postings stay readable after jobs close.

- [Download all 30 resumes, previews, postings, selections, and sample data](samples/roran-stronghammer/Roran%20StrongHammer%20-%2030%20Resumes.zip).
- [Inspect the sample master](samples/roran-stronghammer/fixture/master.yaml), [settings](samples/roran-stronghammer/fixture/settings.json), and [job-specific selections](samples/roran-stronghammer/selections).
- [Learn how to edit and regenerate a saved run](docs/USAGE.md#edit-resume-export), [change preferences](docs/USAGE.md#change-things-directly-or-through-your-agent), or [add custom behavior](docs/USAGE.md#add-behavior-without-touching-core-code).

The sample person is invented; the job postings are saved employer-published descriptions. The gallery opens locally at `samples/roran-stronghammer/index.html`. The hosted link becomes available after GitHub Pages deployment; [publishing instructions](samples/roran-stronghammer/README.md) are included.

## The numbers

[Recorded AI-inclusive benchmark summary](samples/roran-stronghammer/benchmark-summary.json).

| Measured result | Observation |
|---|---:|
| AI-inclusive median per resume, three-worker run | 27.04s |
| AI-inclusive median per resume, ten-worker run | 27.77s |
| Ten-worker batch, all 30 completed including retries/operator pauses | 220.43s |
| Ten-worker completed throughput | 8.2 resumes/minute |
| Final PDFs passing recorded content/geometry checks | 30/30 in each run |
| Page fill in the current 30-resume sample | 96-98.9% |
| Recent local one-page formatting edit, median of five runs | 0.44s, no AI call |
| Passing functionality tests | 89 |
| Matching CLI/MCP operations | 21 |

The AI measurements are recorded historical runs using Codex ACP 2.2.2, `gpt-6-sol`, medium reasoning, and an existing Codex login. They include process/session startup, AI selection, fitting, PDF export, and automated checks. They start with ready career data and saved postings; collection, profile authoring, and human review are excluded. Ten workers made 33 inference attempts for 30 completed resumes. These are observations, not latency guarantees or measured human comparisons. Batch throughput is not individual response time.

The current gallery reuses earlier selections with an expanded sample profile; it was not freshly AI-tailored. Its [12.29-second refresh](samples/roran-stronghammer/refresh-timing.json) used **zero inference calls** and is not the basis for the headline. The 95% final skills-line target is not consistently achieved.

Sharp is free MIT-licensed software. Agent subscriptions, usage limits, and optional API charges still apply. ATS-friendly means structured, checked output; no universal ATS score or hiring outcome is promised.

## Under the hood

Approved career evidence + job -> agent choice -> validated constraints -> measured fit -> checked PDF + saved checkpoints.

Selection, facts, and formatting stay separate. Formatting edits reuse the saved choice; exports reuse the saved layout. Failed regeneration preserves the previous successful run. CLI and MCP expose the same typed operations.

[Architecture](docs/architecture.svg) | [Contracts](docs/CONTRACTS.md) | [Validation](docs/VALIDATION.md) | [Custom rules](docs/RULES.md) | [Agent skills](skills/) | [Developer and usage guide](docs/USAGE.md)
