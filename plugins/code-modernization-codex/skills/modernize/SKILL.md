---
name: modernize
description: Start or resume a legacy modernization project, record its scope and migration track, and report the next evidence-backed step.
---

# Modernize

Read [the shared workflow](../../references/workflow.md) first. Resolve `PLUGIN` to this installed plugin's absolute root (two directories above this skill); resolve `WORKSPACE` to the migration workspace. Do not assume the current directory is either one. All helper commands below use these two resolved paths.

Capture the user's intended outcome, source directory, target stack, scope, behavior that must remain stable, and exclusions. Reuse answers and authorization already given in this chat or INTENT.md. Ask only for missing facts that affect execution. Distinguish understand-only, same-stack uplift, cross-stack transform, and architectural reimagine. For understand-only, record that limit in INTENT.md and stop after the plan.

Initialize a new named system with the helper (choose the actual migration track; for understand-only with no target, use transform as a provisional storage layout and explain it in intent):

```sh
python3 "$PLUGIN/scripts/modernize.py" --workspace "$WORKSPACE" demo init --source /absolute/source --track transform --intent 'User objective, constraints, and any understand-only limit'
```

The helper creates a legacy symlink, initial content manifest, INTENT.md, and an explicitly unverified PREFLIGHT.md. The link does not make the source read-only. Use an OS-enforced read-only mount when protection is needed; build and run from disposable copies. Never overwrite an existing system to restart it.

For an existing project:

```sh
python3 "$PLUGIN/scripts/modernize.py" --workspace "$WORKSPACE" demo status
```

Read the current intent, stage artifacts, and exact stale or missing stage. Report what is established, what remains unverified, and the next skill. Artifacts alone are not completed stages. A changed source requires a reviewed new baseline under a new system name/workspace; do not erase the original manifest.

Route to modernize-discover, modernize-plan, modernize-build, or modernize-verify as appropriate. Continue already-authorized work when scope is clear. Do not start a migration merely because this skill was selected for a status question.
