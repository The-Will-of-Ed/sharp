# Sharp

Turn career evidence into a tailored resume, then make edits without asking AI to choose everything again.

Sharp is local-first. It keeps your facts, selection, formatting, and exports separate. Bring your current AI agent, an installed agent through ACP, or a model gateway. There is no required hosted service and no required application UI.

## Try it

From the Sharp folder, using Python 3.12 or newer:

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[test,preview]"
.venv\Scripts\python.exe -m sharp demo --output outputs/demo
```

The demo uses clearly fictional career data. It needs no AI, API key, Office installation, or custom-rule compiler. Open the resulting PDF or PNG. Low fill is reported honestly because the example contains only three bullets.

Sharp is an independent Python project with its own `.venv`. `uv.lock` pins its dependencies. With uv installed, run `uv sync --extra test --extra preview --extra office --extra mcp --extra agents --extra rules` from this folder to recreate development dependencies. Use this folder's `.venv/Scripts/python.exe`; no parent project is required. The development interpreter is pinned in `.python-version`; the package supports Python 3.12 and newer.

Real AI-inclusive execution has now been verified through Codex ACP 2.2.2 with the existing ChatGPT login and existing Codex executable. The reported model was gpt-6-sol, reasoning medium. The run took 12.35 seconds including startup and inference. See [the actual benchmark](docs/ACP_BENCHMARK.md). Rerun using:

```text
.venv\Scripts\python.exe scripts/benchmark_acp.py --adapter path/to/codex-acp/dist/index.js --codex path/to/existing/codex.exe --output outputs/acp-live
```

No CLI installation or update is performed by this script. The usual npm ACP package depends on Codex CLI; the tested local installation unpacked the adapter separately, installed only its other runtime dependencies, and pointed CODEX_PATH at the existing executable. That installation is under ignored `.cache/acp`.

For your own material:

```text
sharp init .
sharp intake path/to/resumes path/to/notes --output data/intake.json
```

Ask your agent to use the career-import skill to turn these sources and your context into a reviewed master. The initialized master is empty apart from a name placeholder. It does not claim the demo's achievements as yours.

## The whole flow

```text
Resumes + source documents + what you tell your agent
                         |
                   Extract and review
                         |
                         v
                  master.yaml                 settings.local.yaml
                  Facts and proof             Your complete local settings
                  Approved bullets            Layout and exceptions
                  User confidence             Selection instructions / functions
                         |                              |
Job text or URL ---------+-------------+----------------+
                                       |
                              Choose relevant evidence
                              once, through an adapter
                                       |
                              Format before fitting
                                       |
                              Measure / fit / inspect
                                       |
                              Paint final placement
                                       |
                         PDF + preview + saved checkpoints
                                       |
                           PPTX / DOCX only if requested
```

See [the visual architecture](docs/architecture.svg), [its PNG](docs/architecture.png), [every contract field with its meaning](docs/CONTRACTS.md), and [the validation record](docs/VALIDATION.md).

## What exists by default

- One basic, single-column ATS-oriented layout with selectable text and actual link destinations.
- No bold text, including the name, headings, and metrics. Hierarchy comes from size and spacing.
- One-page output; choose one or two pages in settings.
- Relevant work experience gets space before projects. This preference is editable; display order is separate.
- A 96% page-fill target and 95% final skills-line target. These are goals, not fabricated-content instructions.
- PDF export and an SVG preview. Install the preview extra for PNGs rendered from the actual PDF.
- Explicit warnings if supported content cannot meet fill targets. No artificial word spacing or invented keywords.
- Saved career, choice, document, settings, geometry, decision report, and stage events for every successful run.

The default supports Summary, Experience, Projects (including service/teaching), Education, and Skills. Other JSON Resume fields are retained for interchange; v1 does not automatically display every optional standard field.

## Choose without an extra AI process

Your existing agent can call `choice_context`, select approved bullet IDs, and pass its `ChoicePlan` directly to `document_create`. No nested Codex or Claude process is necessary.

For file-based use:

```text
sharp context --career master.yaml --settings settings.local.yaml --job-file job.txt
sharp create --request request.yaml
```

Example request:

```yaml
document_type: resume
career_path: master.yaml
settings_path: settings.local.yaml
selection_path: selection.yaml
job: "Paste the posting here, or use its URL."
output_dir: outputs/my-application
title: AI Engineer
formats: [pdf]
```

Selection contains IDs, not copied career facts. Ask for relevant reserves as well as the strongest points: fitting can use the next point without another model request. URLs are cached; JavaScript-only or blocked pages may require pasting the posting.

### Output folders

`output_dir` is explicit in the request; Sharp does not currently add dates or
candidate folders automatically. For normal agent-created applications, use:

```text
outputs/YYYY-MM-DD/person-name/company-role/
```

That folder contains the PDF, optional requested formats, previews, selection,
settings and checks. Reuse its path for edits. The demo and benchmark scripts
use their own explicit paths. Outputs and local career/settings files remain
Git-ignored; source, tests, defaults, documentation and fictional examples are
versioned. Keep local ACP installations and the virtual environment ignored too.

Optional provider configuration:

```yaml
# Gateway routes generative models, Jev, or other decision models.
kind: litellm
base_url: http://localhost:4000
model: your-configured-model
mode: chat   # or decisions
```

```text
sharp create --request request.yaml --provider provider.local.yaml
```

Credentials stay in environment variables, not career/settings files. Gateway inference may cost money. Missing provider cost is recorded as unknown, not zero. Decision models rank existing evidence; they do not write a summary or cover letter. The current decision route batches up to 128 bullet/skill/summary questions.

For installed agents, install the agents extra and configure `kind: acp`, `command`, `args`, and `cwd`. Use the maintained `@agentclientprotocol/codex-acp` or `@agentclientprotocol/claude-agent-acp` adapter, not terminal-output parsing. Agent startup and inference are outside Sharp's local-render budget. Existing subscriptions remain subject to their own availability and limits.

## Change things directly or through your agent

There are two user-owned files:

| File | Change here |
|---|---|
| `master.yaml` | Career facts, approved wording, proof, variants, supported skills, user confidence. |
| `settings.local.yaml` | Fonts, colors, spacing, page limits, fill targets, section order, required/excluded points, item exceptions, selection instructions, custom functions. |

`settings.example.yaml` initializes settings once. It is not merged again at runtime. Updating Sharp does not silently replace your local choices. Both personal files are ignored by Git.

Settings examples:

```yaml
page:
  width: 612
  height: 792
  margins: [36, 40, 36, 40]  # top, right, bottom, left; points
  max_pages: 2
  fill_targets: [0.96, 0.90]
constraints:
  required: [my_strongest_point]
  excluded: [old_project]
  requires:
    my_strongest_point: [supporting_point]
```

These are fragments to apply to the complete settings file, not extra configuration layers. Keep the rest of your initialized file.

Global style edits preserve bullet exceptions. Your agent can explicitly apply a property everywhere, including exceptions, or remove one exception. IDs survive wording edits; missing references are reported. An impossible mandatory combination fails clearly rather than quietly dropping a point.

## Add behavior without touching core code

Tell your agent the outcome you want. It uses the MCP customization interface to add a named function with its purpose/comment, version, declared references, stage, and source. Functions live beside your settings and can be shared.

| Stage | Receives | May return |
|---|---|---|
| Selection | Choice input and current plan | A revised choice plan using existing approved IDs. |
| Before layout | Candidate blocks, settings, career, job, probe measurements | Style/range changes and additional content constraints. |
| After layout | Final pages, positioned blocks and lines, settings, career, job | Text colors on placed blocks or ranges. |

There is no special built-in “first line bold” option. Functions can work with general text ranges and measured lines. Formatting that changes dimensions belongs before fitting. Probe line ranges are not promises about final lines after changing fonts or weight. After-layout formatting cannot change dimensions; Sharp rejects it rather than entering a correction loop.

Functions run once in stored order, each seeing the previous result. Later style changes win. Mandatory constraint contradictions fail. Errors name the function. Output validation is atomic.

Restricted functions use JavaScript inside Extism, with no allowed filesystem paths, hosts, or privileged application callbacks. Install the rules extra plus `extism-js` and Binaryen only if you need functions. See [rules setup](docs/RULES.md). Compilation is an install/update step, not a render step. An enabled function requires a representative preview before activation; that is a smoke test, not proof for all possible inputs.

Custom functions can compute within these contracts. A new exporter or a new layout capability requires an adapter/contract implementation. Sharp does not pretend a function signature makes every imaginable feature available.

## User confidence, not fabricated certainty

Each bullet may have `confidence: {level: high, note: "..."}`. This combines your firsthand depth/defendability and how prominently you want the work featured.

The initial classes are very high, high, medium, low, and neutral/unrated. Definitions and order live in the master and are supplied verbatim to the chooser. You can define your own classes. An omitted assessment is unrated; neither import nor AI invents one.

Relevance and explicit constraints come first. A very-high assessment does not make an unrelated project relevant. Factual support, wording approval, and provider confidence are separate. Meaningful claim or class-definition edits flag reassessment without silently changing your rating.

## Edit, resume, export

```text
sharp inspect outputs/my-application
sharp edit outputs/my-application --changes '{"styles.body.size":9.5}'
sharp export outputs/my-application --format pptx
sharp export outputs/my-application --format docx
```

Formatting edits reuse the saved career and choice, rebuilding presentation from the revised settings. They do not run selection again. The base document is also saved for inspection. Exports reuse saved layout. Dedicated output folders are staged and replaced only after success, so failed regeneration preserves the previous complete run.

PowerPoint has editable text at explicit line positions. Word is editable flow layout and can paginate differently; check it in Word before submitting. Fonts can differ across machines. PDF is the authoritative checked layout, not a guarantee about every ATS product.

For a cover letter, use `document_type: cover_letter` and provide a grounded `letter_text` draft. It uses the same output pipeline. Nothing creates an unsolicited second document.

## Connect your agent through MCP

```text
python -m pip install -e ".[mcp]"
sharp mcp --root path/to/your/career-workspace
```

Configure that command as a stdio MCP server in your agent. Start with `contracts_describe` for an index, then request only the contracts needed. The server can initialize a workspace, extract material, inspect/propose/apply career revisions, record explicit user assessments, create/edit/export documents, and manage/share settings and functions. File operations are scoped to its configured workspace. Customization runtime restrictions apply separately from MCP's trusted local file tools.

The three [skills](skills/) explain career import/update, resume creation, and cover-letter creation. They are deliberately short. Your agent can create both documents by invoking the two document workflows; there is no separate pair framework.

## Develop and test

```text
python -m pip install -e ".[test,preview,office,mcp,rules,agents]"
python -m pytest
python scripts/build_docs.py
python scripts/benchmark.py
```

Set `SHARP_RULE_COMPILER` to the installed compiler and put Binaryen's executables on PATH to include real sandbox tests. Without that opt-in those tests explicitly skip; the basic suite never silently treats a fake runtime as real isolation.

Contracts and functionality tests come first. Keep core career/selection/layout independent of vendors; `workflow.py` is outer file/run orchestration and `service.py` composes adapters. No imports from the old resume applications. Tests must not be weakened to accommodate broken implementation.

Benchmarks report local work separately from inference. The final 80-candidate benchmark on the implementation machine measured:

| Local operation | One page | Two pages |
|---|---:|---:|
| Cold CLI generation | 1.73 s | 1.85 s |
| Warm PDF generation, median of five | 0.78 s | 1.01 s |
| Warm formatting edit, median of five | 0.62 s | 0.81 s |

These include fitting, export, previews and checks. They exclude model inference. They are measurements, not cross-machine or model-latency guarantees. The benchmark script saves actual results under ignored outputs, alongside an explicitly assumed 30-minute manual baseline; that baseline is not a measured like-for-like quality comparison.

Sharp's software is open source. Your master, settings, evidence, credentials, run folders, and caches are local and ignored. Review a portable settings copy before sharing: custom source and comments are user-authored text and can themselves contain private information.
