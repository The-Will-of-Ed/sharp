# Using Sharp

Turn career evidence into a tailored resume, then make edits without asking AI to choose everything again.

Sharp is local-first. It keeps your facts, selection, formatting, and exports separate. Bring your current AI agent, an installed agent through ACP, or a model gateway. There is no required hosted service and no required application UI.

## Browse the sample gallery

Open [30 sample resumes and saved job postings](../samples/roran-stronghammer/index.html). The gallery includes previews, PDFs, the full career inventory, job snapshots and a ZIP download. [Publishing instructions](../samples/roran-stronghammer/README.md) explain GitHub Pages setup for The-Will-of-Ed/sharp.

## Let your agent set it up

Open this folder in Codex or Claude Code and ask it to follow [the complete setup guide](SETUP.md). It installs a local environment, registers the MCP server, verifies tool access, and follows the import skill to turn one or several resumes/folders into a reviewed master. The guide includes Windows and macOS/Linux commands; no separate model/API key is required for that route.

## Try it

From the Sharp folder, using Python 3.12 or newer:

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[test,preview]"
.venv\Scripts\python.exe -m sharp document_demo
```

The demo uses clearly fictional career data. It needs no AI, API key, Office installation, or custom-rule compiler. Open the resulting PDF or PNG. Low fill is reported honestly because the example contains only three bullets.

Sharp is an independent Python project with its own `.venv`. `uv.lock` pins its dependencies. With uv installed, run `uv sync --extra test --extra preview --extra office --extra mcp --extra agents --extra rules` from this folder to recreate development dependencies. Use this folder's `.venv/Scripts/python.exe`; no parent project is required. The development interpreter is pinned in `.python-version`; the package supports Python 3.12 and newer.

For your own material:

```text
sharp workspace_initialize --root data/career
sharp material_extract --root data/career --args @sources.json
```

Ask your agent to use the career-import skill to turn these sources and your context into a reviewed master. The initialized master is empty apart from a name placeholder. It does not claim the demo's achievements as yours.

## One interface, two transports

Every operation has identical names, typed arguments, validation, workspace boundaries, and returned data in CLI and MCP. `sharp --help` lists operations; `sharp <operation> --schema` prints the input contract. CLI accepts `--args` as JSON or `@file` for JSON/YAML. Argument files resolve from the shell directory; operation paths resolve inside `--root` (default: current directory). CLI prints UTF-8 JSON. `mcp` only starts the transport. The shared catalog is `src/sharp/operations.py`; adding an operation there exposes it through both transports.

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

See [the visual architecture](architecture.svg), [its PNG](architecture.png), [every contract field with its meaning](CONTRACTS.md), and [current validation checks](VALIDATION.md).

## What exists by default

- One basic, single-column ATS-oriented layout with selectable text and actual link destinations.
- Bold name, target role, section/employer headings and education rows. Bullet text stays regular unless explicit text ranges request emphasis.
- Charcoal body (#1A1A1A), orange section/role headings (#C44B12), and blue employer/project headings (#1F5A8A), all controlled by semantic styles.
- Visible list markers with hanging indentation, plus PDF list structure tags. Marker text and geometry live in `styles.bullet`.
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
sharp choice_context --root data/career --args @context.json
sharp document_create --root data/career --args @create.yaml
```

`context.json` contains `career_path`, `settings_path`, and `job` (posting text or URL).
`create.yaml` wraps the request below under `request:`. Optional `choice_plan` and
`provider` are sibling keys. `sources.json` contains `{"paths":["sources/resumes","sources/notes"]}`.

Example request (inside `request:`):

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

Optional provider configuration (the `provider` field in `create.yaml`):

```yaml
# Gateway routes generative models, Jev, or other decision models.
kind: litellm
base_url: http://localhost:4000
model: your-configured-model
mode: chat   # or decisions
```

```text
sharp document_create --root data/career --args @create.yaml
```

Credentials stay in environment variables, not career/settings files. Gateway inference may cost money. Missing provider cost is recorded as unknown, not zero. Decision models rank existing evidence; they do not write a summary or cover letter. The current decision route batches up to 128 bullet/skill/summary questions.

For installed agents, install the agents extra and configure `kind: acp`, `command`, `args`, and `cwd`. Use the maintained `@agentclientprotocol/codex-acp` or `@agentclientprotocol/claude-agent-acp` adapter, not terminal-output parsing. Agent startup and inference are outside Sharp's local-render budget. Existing subscriptions remain subject to their own availability and limits.

Profile links default to separate lines. Set `profile_separator: " | "` in local settings to place them together with natural wrapping; spaces, tabs, or another separator also work. Tabs expand to spaces. Each URL keeps its own click target in PDF, DOCX, and PPTX. Set it to `"\n"` to restore separate lines. This also works through `settings_update`.

## Change things directly or through your agent

There are two user-owned files:

| File | Change here |
|---|---|
| `master.yaml` | Career facts, approved wording, proof, variants, supported skills, user confidence. |
| `settings.local.yaml` | Fonts, colors, spacing, page limits, fill targets, section order, required/excluded points, item exceptions, selection instructions, custom functions. |

`settings.example.yaml` initializes settings once. It is not merged again at runtime. Updating Sharp does not silently replace your local choices. Both personal files are ignored by Git.

List settings are ordinary styles, not renderer constants:

```yaml
styles:
  bullet:
    marker: "•"
    indent: 12          # Body text starts 12 points inside the margin.
    marker_offset: 12   # Marker starts 12 points before the body text.
    after: 4
    bold: false
    color: "#1A1A1A"
```

Wrapped lines align with the bullet body. To remove a marker, set it to an empty
string; indentation is separately editable. Per-bullet exceptions use the same
style fields. A marker that cannot fit its allotted offset produces an error.
PDF output includes selectable marker text and L/LI/Lbl/LBody list tags; this is
not a PDF/UA certification or a guarantee of interpretation by every ATS.
Existing saved local settings are not silently upgraded to new defaults.

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

Restricted functions use JavaScript inside Extism, with no allowed filesystem paths, hosts, or privileged application callbacks. Install the rules extra plus `extism-js` and Binaryen only if you need functions. See [rules setup](RULES.md). Compilation is an install/update step, not a render step. An enabled function requires a representative preview before activation; that is a smoke test, not proof for all possible inputs.

Custom functions can compute within these contracts. A new exporter or a new layout capability requires an adapter/contract implementation. Sharp does not pretend a function signature makes every imaginable feature available.

## User confidence, not fabricated certainty

Each bullet may have `confidence: {level: high, note: "..."}`. This combines your firsthand depth/defendability and how prominently you want the work featured.

The initial classes are very high, high, medium, low, and neutral/unrated. Definitions and order live in the master and are supplied verbatim to the chooser. You can define your own classes. An omitted assessment is unrated; neither import nor AI invents one.

Relevance and explicit constraints come first. A very-high assessment does not make an unrelated project relevant. Factual support, wording approval, and provider confidence are separate. Meaningful claim or class-definition edits flag reassessment without silently changing your rating.

## Edit, resume, export

```text
sharp run_inspect --args '{"directory":"outputs/my-application"}'
sharp run_edit --args '{"directory":"outputs/my-application","settings_changes":{"styles.body.size":9.5}}'
sharp run_export --args '{"directory":"outputs/my-application","format":"pptx"}'
sharp run_export --args '{"directory":"outputs/my-application","format":"docx"}'
```

Formatting edits reuse the saved career and choice, rebuilding presentation from the revised settings. They do not run selection again. The base document is also saved for inspection. Exports reuse saved layout. Dedicated output folders are staged and replaced only after success, so failed regeneration preserves the previous complete run.

PowerPoint has editable text at explicit line positions. Word is editable flow layout and can paginate differently; check it in Word before submitting. Fonts can differ across machines. PDF is the authoritative checked layout, not a guarantee about every ATS product.

For a cover letter, use `document_type: cover_letter` and provide a grounded `letter_text` draft. It uses the same output pipeline. Nothing creates an unsolicited second document.

## Connect your agent through MCP

```text
python -m pip install -e ".[mcp]"
sharp mcp --root path/to/your/career-workspace
```

See [complete Codex and Claude Code registration commands](SETUP.md#3-register-the-stdio-server-with-the-current-agent). Configure that command as a stdio MCP server in your agent. Start with `contracts_describe` for an index, then request only the contracts needed. The server can initialize a workspace, extract material, inspect/propose/apply career revisions, record explicit user assessments, create/edit/export documents, and manage/share settings and functions. File operations are scoped to its configured workspace. Customization runtime restrictions apply separately from MCP's trusted local file tools.

The three [skills](../skills/) explain career import/update, resume creation, and cover-letter creation. They are deliberately short. Your agent can create both documents by invoking the two document workflows; there is no separate pair framework.

## Develop and test

```text
python -m pip install -e ".[test,preview,office,mcp,rules,agents]"
python -m pytest
python scripts/build_docs.py
python scripts/benchmark.py
```

Set `SHARP_RULE_COMPILER` to the installed compiler and put Binaryen's executables on PATH to include real sandbox tests. Without that opt-in those tests explicitly skip; the basic suite never silently treats a fake runtime as real isolation.

Contracts and functionality tests come first. Keep core career/selection/layout independent of vendors; `workflow.py` is outer file/run orchestration and `service.py` composes adapters. No imports from the old resume applications. Tests must not be weakened to accommodate broken implementation.

Run `scripts/benchmark.py` to measure local fitting, generation and edits on your machine. Local measurements exclude model inference; report those stages separately.

Sharp's software is open source. Your master, settings, evidence, credentials, run folders, and caches are local and ignored. Review a portable settings copy before sharing: custom source and comments are user-authored text and can themselves contain private information.
