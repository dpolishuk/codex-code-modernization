---
name: modernize-build
description: Implement an authorized modernization pilot or phase, preserving legacy behavior and collecting runnable tests and comparison evidence.
---

# Build

Read [the shared workflow](../../references/workflow.md) first. Resolve `PLUGIN` to this installed plugin's absolute root (two directories above this skill); resolve `WORKSPACE` to the migration workspace. Do not assume the current directory is either one. All helper commands below use these two resolved paths.

Before edits run:

```sh
python3 "$PLUGIN/scripts/modernize.py" --workspace "$WORKSPACE" demo check-build
```

Read the current brief and its user authorization. Select only the requested module/phase, honor entry criteria, and stop on unresolved decisions affecting it. Understand-only intent does not authorize implementation. Keep the legacy source unchanged. Use the output layout in the shared reference; do not silently switch tracks.

- Uplift: copy the source into the uplifted working tree, capture actual old-runtime test results and BASELINE.md, then implement applicable DELTA_CATALOG.md changes. Preserve test identity and explain removed or changed tests. An old-runtime failure is evidence, not a test to hide.
- Transform: implement one module in the new stack against the discovered behavior contract. Map source rules to new code and tests in TRANSFORMATION_NOTES.md.
- Reimagine: implement one service and its integration contracts under the reimagined tree. Record compatibility boundaries and migration/rollback behavior in REIMAGINE_NOTES.md. Scaffolding and pending tests are not a completed migration.

Add characterization tests for critical behavior before changing it where the baseline can run. Compare old/new outputs for development cases using [the verification evidence format](../../references/verification.md). Keep genuine runner XML/logs and comparison outputs; never synthesize successful runner results. Each relevant P0 rule needs a test that actually exercises it and names its ID. Fix failures in implementation work; retain all proposed differences for the user to decide. Do not introduce blanket masks to make comparison pass.

Run the relevant build and tests. Write analysis/demo/BUILD.md with implemented scope, exact source/target revisions when available, toolchain versions, commands, raw evidence paths, limitations, proposed differences, and rollback. Record source Git revision if already known/trusted; the helper's content hashes also account for uncommitted changes.

```sh
python3 "$PLUGIN/scripts/modernize.py" --workspace "$WORKSPACE" demo checkpoint build
python3 "$PLUGIN/scripts/modernize.py" --workspace "$WORKSPACE" demo report
```

A build checkpoint only freezes the implementation and metadata for verification; it is not a pass verdict. Continue with modernize-verify. After further code edits or changed build notes, checkpoint build again before verification. Do not modify the brief merely to fit an unexpected implementation; revise and re-authorize material scope changes first.
