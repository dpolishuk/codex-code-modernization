---
name: modernize-verify
description: Independently rerun modernization tests and old/new comparisons, exercise a defect canary, and compute scoped evidence-based verdicts.
---

# Verify

Read [the shared workflow](../../references/workflow.md) first. Resolve `PLUGIN` to this installed plugin's absolute root (two directories above this skill); resolve `WORKSPACE` to the migration workspace. Do not assume the current directory is either one. All helper commands below use these two resolved paths.

Read [the verification procedure and schemas](../../references/verification.md). Require a current build checkpoint. Prefer a fresh chat or separately authorized verifier; with the same agent, disclose that limitation and rerun all evidence independently. Treat build notes as claims.

Start the verification window before test execution:

```sh
python3 "$PLUGIN/scripts/modernize.py" --workspace "$WORKSPACE" demo begin-verify
```

Inspect database/service configuration before execution. Use the plan's local/disposable environment. Clean only known generated output in the replacement/scratch tree, run the full relevant suite, and save the actual per-test XML and raw logs. Rerun development comparisons on the replacement. Run at least ten distinct fresh inputs on both old and new implementations; include valid boundaries and explicitly scoped malformed inputs. Keep raw outputs. The upstream heuristic requires fresh outputs distinct from development outputs; if a finite-output system cannot satisfy it, report that limitation rather than manufacturing outputs.

Create a disposable copy of the replacement, introduce a meaningful one-line defect, rerun its covering tests, and save the failing results. This canary checks test sensitivity; it is not a security exploit exercise. Never weaken tests, alter raw outputs, approve differences, or edit implementation during verification. If repairs are needed, return to modernize-build and restart verification after re-checkpointing.

Write equivalence/test-runs.json with paths, commands and observations, never invented counts. Run:

```sh
python3 "$PLUGIN/scripts/modernize.py" --workspace "$WORKSPACE" demo verify
```

Report CODEX_VERIFICATION.json's verdict and the upstream per-module verdicts/reasons in VERIFICATION.json. Exit 0 means PROVEN for recorded scope, 1 means partial/not proven, 2 means unusable input or workflow error. Do not soften failures or call local evidence production certification. Report skipped tests, masks, tolerances, approved differences, untested scope, and unavailable legacy execution. Human sign-off remains blank unless the user actually supplies it. The five-skill workflow does not automatically trigger security scanning or deployment.

The helper refreshes REPORT.html after verification. Close only processes you started. On resume, run status first: stale evidence is UNVERIFIED even if an older report says PROVEN.
