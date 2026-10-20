# Set up Sharp with your existing agent

Open this repository in Codex or Claude Code and say:

> Read AGENTS.md and docs/SETUP.md. Set up Sharp in its own environment, connect it to this agent, and verify the tools. Import the resumes and notes I specify into one proposed master, consolidate duplicate claims, and show it to me before approval. Keep my originals unchanged and my data out of Git.

The agent can run the setup below. Its normal terminal/install permissions and any host-required MCP trust or session restart still apply. This guide does not require a new API key, a hosted service, a nested model, or an ACP installation. The current agent does the reasoning; Sharp performs validated file operations and rendering.

## 1. Install the local package

Prerequisites: Git, Python 3.12 or newer, and an installed, signed-in Codex or Claude Code with terminal access. Work from the cloned Sharp repository. Do not reuse someone else's virtual environment.

If uv is installed, use the committed lockfile:

```text
uv sync --frozen --extra preview --extra office --extra mcp
```

Alternatively, Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[preview,office,mcp]"
```

macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[preview,office,mcp]"
```

The pip route resolves the supported dependency ranges; the uv route uses exact locked versions. `preview` supplies PDF PNG previews, `office` supplies DOCX/PPTX readers and optional exports, and `mcp` supplies the local server. PDF generation is included in the base package. Install `agents` only for a separate ACP process; install `rules` and its documented compiler/runtime prerequisites only for custom functions. Neither is needed for basic use through the current agent.

## 2. Create a private career workspace

From the repository root, Windows PowerShell:

```powershell
$sharpPython = (Resolve-Path .venv\Scripts\python.exe).Path
& $sharpPython -m sharp --help
& $sharpPython -m sharp workspace_initialize --root data/career
$sharpWorkspace = (Resolve-Path data/career).Path
```

macOS/Linux:

```sh
sharp_python="$(pwd)/.venv/bin/python"
"$sharp_python" -m sharp --help
"$sharp_python" -m sharp workspace_initialize --root data/career
sharp_workspace="$(pwd)/data/career"
```

Initialization creates an empty `master.yaml` and complete `settings.local.yaml`. If the workspace already exists, inspect and reuse it; do not reinitialize or overwrite it. The default workspace lives inside ignored `data/`. Another workspace is possible, but the user must keep it private and decide its own ignore rules.

Copy supplied files or folders into separate subfolders under `data/career/sources/`. Preserve originals and avoid overwriting files with the same basename. MCP intentionally cannot read outside its configured workspace, including through symlinks. Do not widen it to the entire home directory merely to import a resume.

## 3. Register the stdio server with the current agent

Use the absolute interpreter and workspace paths calculated above. Inspect existing registrations first and reuse a matching one; do not overwrite an unrelated server with the same name. Run only the instructions for the user's current host. These commands configure that host on the user's machine, not the repository.

Windows PowerShell, Codex:

```powershell
codex mcp list
codex mcp add sharp -- $sharpPython -m sharp mcp --root $sharpWorkspace
codex mcp get sharp
```

Windows PowerShell, Claude Code:

```powershell
claude mcp list
claude mcp add --transport stdio --scope local sharp -- $sharpPython -m sharp mcp --root $sharpWorkspace
claude mcp get sharp
```

macOS/Linux, Codex:

```sh
codex mcp list
codex mcp add sharp -- "$sharp_python" -m sharp mcp --root "$sharp_workspace"
codex mcp get sharp
```

macOS/Linux, Claude Code:

```sh
claude mcp list
claude mcp add --transport stdio --scope local sharp -- "$sharp_python" -m sharp mcp --root "$sharp_workspace"
claude mcp get sharp
```

The host launches the local server over stdio when connecting. There is no browser login to Sharp, listening HTTP port, or background service to maintain. Registration alone is not proof of connection: reload/restart the agent session if needed, inspect `/mcp`, then call `contracts_describe`. Follow the host's normal trust prompts rather than bypassing them. Do not run `sharp mcp` as a detached service.

Sources: [Codex MCP](https://developers.openai.com/codex/mcp), [Claude Code MCP](https://code.claude.com/docs/en/mcp). The Codex registration syntax was also checked against the installed CLI. Claude registration is documentation-verified; this development machine does not have Claude Code installed.

## 4. Import one resume, many resumes, or folders

The agent reads `skills/sharp-career-import/SKILL.md` directly. Installing a global skill is optional; reading the repository instructions is enough to follow the workflow.

Use these MCP operations:

1. `contracts_describe` requests the Career, Bullet, Evidence, and Confidence contracts.
2. `career_inspect` reads the empty/current master and its revision hash.
3. `material_extract(paths=[...])` accepts files and recursively scans folders inside the workspace. Supply multiple paths in one call. Avoid listing the same file through overlapping folder paths.
4. The current agent reconciles sources and user context, consolidates duplicate claims, preserves stable IDs and qualifiers, and prepares a complete proposed Career. It does not invent confidence assessments or silently approve facts.
5. Show the proposal for review. After the user approves, `career_replace(career_path="master.yaml", proposed_career=..., expected_hash=...)` validates and saves the complete master. If the revision changed, inspect and review again. Later wording-only updates can use `career_propose` and `career_apply`.

Supported readers: PDF, DOCX, PPTX, text, Markdown, YAML, and JSON. For scanned/image-only PDFs, the current agent reads the page images directly using its PDF/image capabilities. The skill combines that reading with user context and extracted text where useful; an empty text layer is not a reason to reject a resume. If the host cannot display PDF pages, obtain page images or an OCR copy. Sharp's optional text reader does not itself perform OCR. Corrupt/password-protected documents may need user intervention. Extraction preserves source paths and hashes, plus page/slide attribution where supported. It is text extraction, not proof that a claim is independently verified.

CLI extraction is also available. For example, from the repository root on Windows:

```powershell
& $sharpPython -m sharp material_extract --root data/career --args '{"paths":["sources/resumes","sources/notes"]}'
```

On macOS/Linux, substitute `"$sharp_python"` for `& $sharpPython`. The CLI returns extracted material; it does not run an automatic resume-to-master model or semantic deduplication. The import skill supplies that reasoning. Complete reviewed replacement uses the MCP operation above; the CLI also exposes existing-wording proposal approval and explicit legacy migration.

## 5. Create and edit a resume

Read `skills/sharp-resume-create/SKILL.md`. Call `choice_context` with the master, settings, and job text or URL. The current agent returns a ChoicePlan of approved IDs, then passes it directly to `document_create`. No second model call is required. For example, the request contains:

```json
{
  "career_path": "master.yaml",
  "settings_path": "settings.local.yaml",
  "output_dir": "outputs/YYYY-MM-DD/person/company-role",
  "job": "The job posting text or URL",
  "title": "Target Role - Company",
  "formats": ["pdf"]
}
```

Paths are relative to the MCP workspace, so these outputs stay inside ignored `data/career/`. The agent must choose the actual date/person/role path; the renderer does not add them automatically. Pass `choice_plan` alongside the request to `document_create`. Use `run_inspect` to check selected evidence, geometry, fill warnings and timings, and inspect the actual PDF preview. Formatting edits use `run_edit`; exports use `run_export`. They reuse selection and do not call a model.

For a cover letter, read `skills/sharp-cover-letter/SKILL.md` and supply reviewed `letter_text` with `document_type="cover_letter"`. It is a separate requested document, not an automatic extra.

## Completion check

Setup is complete only after the agent can discover Sharp's MCP tools and initialize/inspect its private workspace. Before claiming the user's career is ready, review and validate the imported master. Before delivering a resume, actually create it, inspect its warnings and PDF, and report the path. Review fill targets and supported sections/layouts, and confirm that any scanned pages were actually inspected by the agent.

The automated integration test covers multiple PDF/DOCX folders, real stdio MCP extraction, reviewed master replacement, and PDF generation with a supplied choice plan. It tests the plumbing, not the quality of an arbitrary agent's interpretation of a person's career.

## CLI and MCP parity

All operation names and arguments are identical in both interfaces. Use `sharp --help` and `sharp <operation> --schema` to discover them. CLI uses `--root` for the private workspace and `--args` for a JSON object or `@file` containing JSON/YAML arguments. It returns UTF-8 JSON on stdout. Argument-file paths resolve from the shell directory; paths inside operation arguments must stay inside the workspace. Only `mcp` is transport-specific.
