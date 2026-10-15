---
name: modernize-discover
description: Assess a legacy system, map dependencies and external consumers, and extract source-cited business rules before modernization.
---

# Discover

Read [the shared workflow](../../references/workflow.md) first. Resolve `PLUGIN` to this installed plugin's absolute root (two directories above this skill); resolve `WORKSPACE` to the migration workspace. Do not assume the current directory is either one. All helper commands below use these two resolved paths.

Read INTENT.md and status. Complete PREFLIGHT.md with source scope, missing components, runtime/toolchain, commands, environment dependencies, previous attempts, and exclusions. Inspect build/test configuration before running it. Record a real small build/test result where possible, with raw logs and exit status; otherwise state the precise blocker. Run builds in scratch copies outside legacy/. Do not contact production services to obtain a baseline.

Use the user's preferred graph tools when available. In an already indexed CodeGraph repository, use CodeGraph before textual code exploration; never create an index implicitly. Fall back to scoped symbol or text search. Keep every finding tied to a source path and line, and identify dynamic dispatch or runtime-only dependencies that static analysis cannot resolve.

Write:
- ASSESSMENT.md: technologies, entry points, size, complexity, missing sources, risks, and recommended track. Separate observations from hypotheses.
- topology.json: modules with stable IDs and source paths, dependency edges, data stores, entry points, external consumers, and business flows. Include evidence citations and unknowns. Add a Mermaid diagram if useful.
- BUSINESS_RULES.md: testable Given/When/Then cards with stable RULE-001 IDs, priority, confidence, source citations, and affected modules; use the parser-compatible format in the shared reference.
- For uplift, DELTA_CATALOG.md: exact old/new versions, applicable breaking changes and silent behavioral changes, cited upstream documentation, affected source sites, and required characterization tests. A test-runner migration may be a prerequisite.

Re-read each rule's cited implementation and relevant callers independently of the first extraction. Record unresolved interpretations instead of inventing domain intent. Where user-authorized delegation is available, a separate reviewer may check bounded groups of rules; otherwise do a distinct second pass and disclose that it was the same agent. Do not claim this equals independent runtime verification.

Record human corrections in RULE_REVIEWS.json with rule ID, verdict (confirmed/wrong/discuss), note, and the actual decision reference. Do not mark your own interpretation as human-confirmed. Low-confidence critical rules and disputed rules become plan blockers for affected slices.

After checking artifact completeness and source citations:

```sh
python3 "$PLUGIN/scripts/modernize.py" --workspace "$WORKSPACE" demo checkpoint discover
python3 "$PLUGIN/scripts/modernize.py" --workspace "$WORKSPACE" demo report
```

The checkpoint records artifact hashes, not proof that the analysis is correct. Explain evidence gaps and continue to modernize-plan when within the user's request.
