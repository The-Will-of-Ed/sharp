# Implementation validation

Validated locally on Windows with Python 3.14.3. This records actual checks, not a claim that the configured cross-platform CI matrix has already run.

## Results

- 61 test cases passed with no skips when SHARP_RULE_COMPILER and Binaryen were configured.
- Actual Wasm tests covered file/network attempts, infinite-loop deadlines, excessive output, fresh state, installed artifact caching, and execution without locating the compiler.
- An actual stdio MCP client initialized the server, discovered contracts, initialized a workspace, and verified rejection of an outside-workspace path.
- Functionality covered confidence neutrality/reassessment, evidence/approval, qualifiers, required/supporting/excluded points, relevance ranking versus display order, settings edits and exceptions, single/two-page fitting, PDF links/text, editable Office exports, cover letters, atomic failed regeneration, and zero repeated selection on formatting edits.
- Ruff checks and source formatting passed. Python compilation passed.
- The distribution wheel built successfully: sharp_resume-0.1.0-py3-none-any.whl.
- Three skills passed the skill-creator validator.
- The initial regular-only default was verified at that time; it is superseded by the user-approved hierarchy documented in DEFAULT_STYLE_CHANGE.md. Demo and two-page benchmark PDF previews were inspected.
- Independent read-only subagent reviews found and confirmed fixes for dependency expansion, stale hook inputs, keep-with-next spacing, selection rank, refit exception/order handling, font-error masking, confidence variant revisions, and source-linked approved summaries. No blocker remained in their final targeted reviews.

Tests were added before implementation of the corresponding behavior. Two new test setups needed corrections: the MCP SDK's Python field is is_error rather than its wire alias isError, and the tight-page ranking fixture needed less space to force an actual choice. Behavioral assertions were retained.

## Performance

Five warm runs per case with 80 synthetic candidate bullets and a supplied selection plan:

| Operation | One page | Two pages |
|---|---:|---:|
| Cold CLI process | 1.73 s | 1.85 s |
| Warm generation median | 0.78 s | 1.01 s |
| Warm generation maximum | 1.11 s | 1.05 s |
| Warm formatting-edit median | 0.62 s | 0.81 s |
| Warm formatting-edit maximum | 0.76 s | 0.84 s |

These initial measurements cover local selection validation, fitting, export, previews and checks. They do not measure remote inference. A subsequent actual Codex ACP run using the existing ChatGPT login is documented in ACP_BENCHMARK.md: 12.35 seconds including startup and inference. This replaces the earlier untested status for that specific installed-agent path. Other live providers remain environment-specific. After the ACP fixes, 62 tests passed inside Sharp's own virtual environment, including real custom-rule runtime and stdio MCP tests.

The benchmark also records a 30-minute assumed manual baseline. It is explicitly an assumption, not an observed or quality-equivalent comparison. Do not advertise the ratio between that full manual task and local rendering as measured end-to-end acceleration.

## Reproduce

From this project directory, install the test/preview/office/MCP/agents/rules extras. Set SHARP_RULE_COMPILER to extism-js and put Binaryen's tools on PATH, then run:

```text
python -m pytest -q
python -m ruff check src scripts
python -m ruff format --check src scripts
python scripts/build_docs.py
python scripts/benchmark.py
```

Without a configured rule compiler, real sandbox tests explicitly skip. No fake runner is counted as sandbox proof.

## Limits

PDF is the checked layout. DOCX can reflow in Word; PPTX fonts can vary across machines. No universal ATS compatibility score is claimed. Custom functions operate within documented contracts; new layout/export capabilities need implementation. The career model's Sharp extension is validated by its typed contracts, and the standard core is validated at the service boundary with the vendored JSON Resume v1.0.0 schema. Source references, including user attestation, support review rather than independent factual verification.


## October 20, 2026: user-approved style defaults

The regular-only default is superseded by DEFAULT_STYLE_CHANGE.md. Full suite:
70 tests. New checks cover configurable palette/markers/offsets, hanging wrap,
PDF L/LI/Lbl/LBody structure, two-page MCID/parent-tree resolution, marker and
first-word extraction on the same line, optional native Office list metadata,
and explicit regular/marker-free overrides. Career wording remains unchanged.
The authoritative one-page fictional preview was visually inspected after export.
A separate layering review found no blocking ownership or dependency issue.
