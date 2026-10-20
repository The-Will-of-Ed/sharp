# Real Codex ACP benchmark

Executed October 20, 2026, using Sharp's own virtual environment.

## Verified execution

| Item | Observed value |
|---|---|
| Python | Sharp .venv, CPython 3.14.3 |
| ACP adapter | @agentclientprotocol/codex-acp 2.2.2 |
| Existing Codex | 0.162.1; unchanged |
| Login | Existing ChatGPT login; no credentials copied |
| Actual model reported by ACP | gpt-6-sol |
| Actual reasoning reported by ACP | medium |
| Agent mode | read-only |
| Stop reason | end_turn |
| Model calls | One prompt |
| Input | Synthetic career with relevant backend evidence and an unrelated art project |
| Output | One-page Python backend resume with selectable text and profile hyperlink |

No Codex CLI was installed or updated. The published ACP package was unpacked locally; only its non-Codex runtime dependencies were installed. CODEX_PATH pointed to the existing native executable. Node dependencies and Python packages are isolated beneath Sharp. The parent virtual environment is no longer needed to run Sharp.

## Measured time

| Stage | Seconds |
|---|---:|
| Entire invocation through document completion, measured in the Python process | 12.345 |
| Selection workflow, including ACP startup/teardown and model response | 11.371 |
| ACP initialize | 0.979 |
| ACP new session | 0.897 |
| AI prompt/response | 7.058 |
| Local layout | 0.006 |
| PDF export and previews | 0.539 |

The ACP substage timings are contained within selection and must not be added to it again. The outer wall measurement includes imports/setup inside the benchmark, but not OS interpreter launch time. This is one successful run, not a statistical latency guarantee. No numeric cost was reported, so cost is unknown; existing plan usage is not represented as universally free inference.

Quality checks passed: Python delivery and SQL validation were selected, the unrelated art event was omitted, and output was one page. PDF text/link checks also passed. This fixture is a real inference smoke test, not a broad assessment of ranking quality across all jobs.

An earlier successful run took 21.98 seconds, including 15.59 seconds for selection and 5.97 seconds for export. The new environment had resolved PyMuPDF 2.0, whose heavier startup affected export. Preview dependencies now constrain PyMuPDF to 1.x, with exact versions in uv.lock. Selection latency also varied; the whole improvement must not be attributed to that dependency change.

## Findings and limits

The live exercise exposed SDK gaps that transport fixtures missed: ClientCapabilities belongs in acp.schema, and extension notifications receive positional method/params. Both are fixed and covered by an adapter regression test.

The restricted parent environment initially prevented Codex from initializing its normal session database. The successful run allowed the installed process to use its ordinary state directory. This is separate from Sharp's read-only selection mode and custom-rule sandbox. No auth file was copied into Sharp.

The two-second end-to-end target was not achieved through a fresh installed-agent process. Provider startup and inference dominate. Reusing a warm ACP connection could remove some startup overhead but was not implemented or benchmarked here. Do not advertise local-only timings as AI-inclusive latency.

The complete report, chosen IDs, PDF, previews and snapshots are under ignored outputs/acp-live-verified. The earlier run is retained under outputs/acp-live. Reproduce using scripts/benchmark_acp.py and explicit paths to the adapter and existing Codex binary.
