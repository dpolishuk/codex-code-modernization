# Verification procedure and evidence

The vendored proof engine is pinned in UPSTREAM.json and kept unchanged. Read
its module docstrings for extended formats. It reads evidence only; the skill
must run the actual tests and old/new drivers separately. The Codex adapter adds
content hashes and an independent-run time window without altering upstream
verdicts. CODEX_VERIFICATION is the effective result; it may be stricter.

## Order

1. Require a current build checkpoint and the intended scope/environment.
2. Run `begin-verify` before generating fresh evidence. Keep implementation,
   BUILD.md and plan unchanged until `verify`; any repair restarts the window.
3. Clean known generated build output in disposable/replacement directories,
   rerun the complete relevant suite and save runner XML plus raw logs. Preserve
   the exit code (a shell pipeline through tee can otherwise hide a failure).
4. Rerun replacement outputs for development cases. Keep the measured legacy
   baseline and original inputs intact.
5. Execute both sides for at least ten new accepted inputs. Save actual outputs
   and list exclusions with reasons. Keep malformed inputs within INTENT's scope.
6. Copy the replacement to scratch outside modernized/ and analysis/, introduce
   one meaningful defect (e.g. wrong rounding or threshold), and rerun its tests.
   Save the actual failures; the unmodified suite must not already fail those
   same tests. Do not mutate the real replacement or baseline.
7. Write test-runs.json with real paths/commands, run the adapter `verify`, and
   report all limitations. Its HTML report uses escaped text and no external JS.

## Comparison files

For a multi-module migration, put each module's cases under
analysis/demo/equivalence/<module>/. Case output paths are relative to that cases
file's directory and must stay inside it. Do not use --allow-outside.

```json
{
  "system": "demo",
  "legacy": {"label": "old runtime", "command": "exact executed command"},
  "new": {"label": "new runtime", "command": "exact executed command"},
  "cases": [
    {"id": "C01", "input": "C01", "title": "Normal quantity",
     "legacy": "dev/legacy/C01.txt", "new": "dev/new/C01.txt", "mask": []}
  ]
}
```

fresh-cases.json has the same shape and fresh output paths. The upstream engine
checks output uniqueness against development cases. Boolean/constant-output
systems may need a reviewed adaptation of that heuristic; report partial proof
instead of adding artificial output to satisfy it.

Use masks only for declared nondeterminism, with `why`. For example,
`{"regex":"generated_at=[0-9T:Z-]+","why":"wall-clock timestamp"}`.
Optional numeric tolerance must include a reason, for example
`{"rel":1e-9,"abs":0,"why":"last digit of floating-point computation"}`.
Integers and nonnumeric content must still match. Do not broaden tolerances to
hide a behavior change. Only actual user decisions can justify
`approvedDifference` or top-level `approvedInputs` entries; record the decision
reference in the reason. Explicitly list accepted differences in the result.

For development feedback, the comparison helper can run independently:

```sh
python3 "$PLUGIN/vendor/upstream/scripts/compare.py" "$WORKSPACE/analysis/demo/equivalence/orders/cases.json"
```

## Test runs

Paths in test-runs.json are workspace-relative. Use the actual module ID as it
appears under modernized/demo; for uplift use the working-copy/unit identity
recognized by the upstream proof engine. Prefer per-test XML over log summaries:
only per-test records can establish that a rule's test ran and passed.

```json
{
  "date": "actual run date",
  "legacy": {"ran": true, "how": "actual local baseline invocation", "why": ""},
  "leftOut": [],
  "suites": [
    {"module": "orders", "name": "unit tests", "command": "actual test command",
     "junit": ["analysis/demo/equivalence/results/orders.xml"],
     "log": ["analysis/demo/equivalence/results/orders.log"],
     "skippedReason": "", "note": ""}
  ],
  "canaries": [
    {"module": "orders", "change": "scratch copy accepts zero quantity",
     "junit": ["analysis/demo/equivalence/canary/orders.xml"], "log": []}
  ]
}
```

Never write result XML to claim a test passed: it must be emitted by the runner
or a transparent runner adapter that records actual executed test outcomes.
Do not put typed pass/fail counts into test-runs.json. Record unavailable legacy
execution as ran=false with a reason, never as a successful substitute run.

## Uplift baseline

Preserve old-runtime per-test results in analysis/demo/baseline/. BASELINE.md
must name actual measured evidence, for example:

```markdown
# Baseline
Code: modernized/demo-uplifted
Command: exact original test command
Recorded: baseline/results.xml
```

Use `baseline_diff.py --help` for runner result formats. Keep test identities
stable so missing and changed tests can be detected. DELTA_CATALOG.md needs
affected source sites and categories, including `Behavioral-silent` when
applicable; each such site needs characterization coverage. A test mentioning a
site is only a traceability check, not proof of semantic coverage.

## Verdicts and limits

The engine checks executed tests, critical-rule tracing, development equivalence
or measured uplift baseline, fresh inputs, canary failures, and untouched source.
Uplifts also check baseline measurement, preserved tests, and covered deltas.
The adapter adds a source content comparison, checkpoint validity and evidence
freshness. Do not bypass the adapter by citing the upstream result alone.

Exit codes: 0 = PROVEN; 1 = PARTLY PROVEN or NOT PROVEN; 2 = workflow/input error.
On 2, an older report can remain on disk: run status and treat stale results as
UNVERIFIED. The evidence is local and editable, not a cryptographic attestation.
Race-free verification requires no concurrent changes during the run.

Report the effective verdict, original per-module reasons, all masks/tolerances,
skips, unresolved decisions and excluded scope. Preserve the blank sign-off block
in upstream VERIFICATION.md; actual approval is separate from test success.
