---
name: modernize-plan
description: Turn modernization discovery into a phased migration plan with a small pilot, behavior contracts, and recorded user authorization.
---

# Plan

Read [the shared workflow](../../references/workflow.md) first. Resolve `PLUGIN` to this installed plugin's absolute root (two directories above this skill); resolve `WORKSPACE` to the migration workspace. Do not assume the current directory is either one. All helper commands below use these two resolved paths.

Require a current discover checkpoint. Read INTENT.md, PREFLIGHT.md, ASSESSMENT.md, topology.json, BUSINESS_RULES.md, rule reviews, and DELTA_CATALOG.md for an uplift. Preserve the user's scope and constraints. Do not repeat an already answered preflight questionnaire.

Write MODERNIZATION_BRIEF.md with objective, exact target stack, architecture, phased sequence, behavior contract, verification strategy, rollback, and unresolved decisions. Start with one representative module. Include schema changes, transaction boundaries, retries/idempotency, external consumers, and concurrency semantics where applicable. Establish measurable entry/exit criteria. Decide how real old/new execution can be compared and which environments are permitted; missing old execution must limit the eventual verdict.

Use this phase format so the upstream proof parser can find criteria:

```text
#### Phase 1 — Pilot
Command: $code-modernization-codex:modernize-build demo transform module-a
Modules: module-a
Entry criteria:
- [ ] Baseline can run in the named disposable environment
Exit criteria:
- [ ] Critical rules have executed tests and unexplained differences are zero
```

For uplift, put incompatible test-harness migration first; handle shared dependency changes together; state how out-of-scope consumers remain compatible. Track values are uplift, transform, reimagine. Record fixed versions and dependency lockfiles, not floating 'latest' targets. List any allowed masks/tolerances and proposed intentional differences with their rationale; a proposal is not an approved difference.

Then checkpoint the plan:

```sh
python3 "$PLUGIN/scripts/modernize.py" --workspace "$WORKSPACE" demo checkpoint plan
```

Present the concrete pilot and its acceptance criteria. If an existing user instruction already authorizes this exact scope, record its reference without asking again. Otherwise obtain approval of this concrete plan before building. Record actual authorization with:

```sh
python3 "$PLUGIN/scripts/modernize.py" --workspace "$WORKSPACE" demo authorize --evidence 'Reference and faithful summary of the user decision'
```

This is a local decision log, not an authenticated signature. Never manufacture approval text. If material inputs change, update the brief and obtain authorization for the changed scope; unchanged authorized scope can reuse the original decision with an accurate explanation. Understand-only work ends here.
