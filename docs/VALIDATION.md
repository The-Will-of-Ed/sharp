# Validation

Validated locally on Windows with Python 3.14.3. The complete suite passes 75 tests when the custom-rule compiler/runtime prerequisites are configured. Configured Linux/Windows CI is not a claim that every hosted CI run has already completed.

## Functional checks

- Real stdio MCP startup, contract discovery, workspace initialization and rejection of outside-workspace paths.
- Multiple PDF/DOCX source folders through CLI and MCP extraction, a reviewed consolidated master saved through `career_replace`, rejection of stale revisions and PDF generation with a supplied selection plan. The agent supplies consolidation; extraction is not credited with semantic deduplication.
- Confidence neutrality and reassessment, evidence/approval references, protected qualifiers, required/supporting/excluded points, relevance ranking versus display order, settings changes and per-item exceptions.
- Single/two-page fitting, selectable PDF text, links, reading order, margin geometry, hanging bullet markers, PDF list tags, and two-page MCID/parent-tree resolution.
- Optional editable DOCX/PPTX exports, cover-letter requests, preservation of successful output after a failed edit, and no repeated selection for formatting-only edits.
- Real restricted-runtime checks for file/network attempts, deadlines, output limits, fresh state and cached execution without locating a compiler.
- Portable sample-gallery links and all 30 resume/posting/selection sets.

A fresh isolated environment installed with standard pip and the preview, office, MCP and test extras passes both the stdio MCP check and the multi-source import-to-PDF check. ACP and custom-rule extras are not needed for that basic route. Claude Code registration is documentation-verified; a live Claude Code host has not been tested here.

## Run checks

```text
python -m pip install -e ".[test,preview,office,mcp,agents,rules]"
python -m pytest -q
python scripts/build_docs.py
python scripts/benchmark.py
```

For real custom-function tests, install the compiler/runtime prerequisites in [RULES.md](RULES.md), set `SHARP_RULE_COMPILER` if necessary, and put Binaryen's executables on PATH. Without that opt-in, sandbox tests explicitly skip. An ordinary runner is not counted as sandbox proof.

Performance measurements are generated on demand into ignored `outputs/`. Keep inference, rendering and edit timings separate. Do not advertise a modeled manual baseline as a measured human comparison.

## Scope

Codex/Claude interprets career sources through the import skill, including visually reading scanned pages when its host provides PDF/image access. Sharp supplies contracts, optional text extraction, validated updates and rendering. The integration test checks those interfaces, not the factual quality of arbitrary agent interpretation.

PDF is the checked layout. DOCX can reflow in Word; fonts can vary across machines. No universal ATS score or PDF/UA certification is claimed. The JSON Resume core is validated against the vendored schema; the extension uses typed contracts. Source references, including user attestation, support review rather than independent verification. Customizations remain bounded by their documented input/output contracts.
