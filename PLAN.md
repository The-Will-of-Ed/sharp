# Sharp implementation plan

Sharp is a standalone, local-first resume and cover-letter tool. Existing career files and workflows are not modified.

## Delivery sequence

1. Define versioned contracts, synthetic examples, and acceptance tests.
2. Implement career validation, one local settings file, and deterministic fitting.
3. Implement PDF export and preview using the same measured lines.
4. Add replaceable AI adapters and restricted custom functions.
5. Add optional editable exports, CLI/MCP, documentation, and three agent skills.
6. Run functionality tests, independent layering reviews, visual checks, and cold/warm benchmarks.

## Boundaries

Contracts, career semantics, selection validation, and fitting are core. Vendor SDKs, extraction, network, PDF, Office, agent access, and Wasm belong in adapters. workflow.py is outer run/file orchestration, while service.py composes vendor adapters; domain modules remain pure. Workflow receives rendering/selection/rule capabilities explicitly. No internal HTTP services, event bus, or application framework. Core cannot import adapters or the old app/resume2 packages.

## User-owned data

JSON Resume-compatible career fields plus x_resume hold approved bullets, stable IDs, evidence, qualifiers, variants, supported skills, and user confidence. Confidence combines firsthand depth/defendability and preferred prominence. Definitions are user-editable, supplied to selection, and never confused with provider certainty. Missing assessments are neutral/unrated. Substantive edits flag reassessment, never invent a rating.

settings.local.yaml is the complete local settings authority, initialized once from an example. It contains layout, content constraints, specific exceptions, selection instructions, and custom function source. No hidden runtime inheritance. Share a portable copy, never secrets or personal career material.

## Creation flow

Import/review career -> supply job -> choose approved evidence once -> before-layout changes -> measure/fit -> after-layout paint -> PDF/preview/checks. Saved runs can restart at selection, fitting, or export. PDF is default. PPTX/DOCX/cover letters are opt-in. Defaults contain no bold text.

Choice is a replaceable adapter. An existing agent can submit the plan directly; optional maintained ACP adapters and LiteLLM connect other providers. Custom policy postprocesses selection; it does not modify master claims. Rewriting is a separate proposal/approval operation.

Custom JavaScript functions run through optional Extism, without allowed paths/hosts or privileged host functions. Compilation happens on installation/update, with pinned fixed arguments and bounded execution. Before hooks can change style/constraints; after hooks can only paint. No corrective loops. Invalid changes are atomic failures attributed to their function.

## Acceptance

Tests precede implementation. Do not weaken tests to accommodate broken behavior. Verify contract errors, stable ownership, qualifiers, no fabricated confidence, no bold defaults, relevance/experience priority, constraints, 1/2-page fitting, line/page fill, logical text order, working links, sandbox boundaries, zero AI calls for formatting/export edits, lazy optional dependencies, and inward-only imports. Review PNG previews. Benchmark local work separately from provider latency; target under two seconds on representative fixtures, not a guarantee for remote inference. Private data, caches, and outputs stay ignored.
