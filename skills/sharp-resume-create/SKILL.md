---
name: sharp-resume-create
description: Create, tailor, edit, or export a Sharp resume using approved career evidence, replaceable selection, and deterministic fitting.
---

Use the user's current agent to choose directly when possible; do not spawn another model just to repeat that choice.

1. Inspect settings and obtain choice_context with the job text or URL. Read only the contracts needed. Use confidence definitions as supplied; unrated is neutral. Prefer proven relevant function and experience, respecting the user's settings and exceptions.
2. Judge relevance across the whole inventory, not by employer order. Rank direct evidence for the job above adjacent technical work. Do not treat broad technical difficulty as a substitute for the requested function. Return a ChoicePlan of relevant approved IDs plus useful ranked reserves, a supported approved summary, and relevant supported skill IDs. Do not copy or rewrite facts into selection. Link identified job requirements where meaningful. Do not invent provider confidence or reasons.
3. Call document_create. Default to PDF; add PPTX/DOCX only when requested. Inspect actual fill, missing space, and issues. Review the exported PDF preview and text order. Never fill gaps with unsupported keywords or artificial word spacing.
4. Formatting edits use run_edit; export-only changes use run_export. Neither should repeat selection. Propose substantive wording changes separately with evidence and user approval, then explicitly choose to update the run snapshot.
5. Add user-requested formatting behavior through settings_update or customization management, with purpose, stage, references and representative preview. Do not touch core code for a user-specific rule. Before-layout changes may affect dimensions; after-layout output is paint only.

Defaults bold names, roles, section/employer headings and degree rows, with regular bullet text and configurable hanging list markers. Do not infer which phrases to bold; use explicit text ranges when requested. Respect user formatting changes. An unattainable target is reported, not a reason to fabricate content. Deliver full absolute paths and identify any unreviewed Office reflow limitations.

Selection-only execution: when a caller supplies the choice context and requests a ChoicePlan, perform steps 1-2 from that input and return the plan. Do not attempt MCP calls, rendering, edits, or another agent process. The same skill is supplied to ACP and gateway selectors; user selection settings accompany it.
