---
name: sharp-career-import
description: Import or update a Sharp career master from resumes, source documents, folders, and user context, retaining evidence and avoiding duplicate claims.
---

Use Sharp's contracts and MCP interfaces rather than editing application code.

1. Inspect the current career and revision. If needed initialize a workspace. Request the Career, Bullet, Evidence, and Confidence contracts through contracts_describe.
2. Extract source text with material_extract. Inspect original slides/pages/images where visuals convey meaning; text extraction is not enough. Preserve source/page/slide attribution. Ask only about material gaps in contribution, results, or scope.
3. Match existing IDs before adding work. Consolidate duplicate claims within the same employer/project; do not merge unrelated contributions across owners. Preserve IDs when wording changes. Evidence links can include explicit user attestation; never call it independent verification.
4. Keep proposed wording separate from approved wording. Preserve estimates, contribution levels, time horizons, and literal qualifiers. Never infer user confidence; omitted means neutral/unrated. User assessments describe depth/defendability and preferred prominence, not factual certainty.
5. Present the concrete proposed career changes. Apply approved wording through career_apply or an explicitly reviewed complete revision through career_replace with the matching hash. Confidence supplied by the user goes through career_assess. Do not silently promote new claims to approved.

Master holds reusable facts, not company-targeted variants or formatting. Settings are a separate complete local file. Do not modify the frozen/legacy master during an import into Sharp.
