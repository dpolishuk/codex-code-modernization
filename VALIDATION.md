# Local validation — 2026-10-15

- CONFIG_VALIDATED: five skills pass Codex skill validation; both manifests parse; references resolve; 18 copied upstream files match pinned hashes.
- RUNTIME_VERIFIED: 259 retained upstream tests and 20 adapter tests passed (279 total).
- RUNTIME_VERIFIED: the executable fixture ran three unit tests, two development comparisons, twelve fresh comparisons, and a meaningful failing canary. Both proof layers returned PROVEN for this fixture.
- RUNTIME_VERIFIED: Codex app-server discovers the local marketplace with no load errors and parses all five namespaced skills.
- RUNTIME_VERIFIED: local installation and a fresh Codex chat advertised all five skills, read the installed files and references, and ran the package validator successfully.
- UNVERIFIED: an agent-driven migration of a real target repository.

The fixture result is local test evidence, not production certification. The upstream test suite emitted benign ResourceWarning notices about unclosed fixture reads; all tests passed.

The adapter regression suite covers source drift with preserved modification times, changed plans and rule reviews, stale runner evidence, missing authorization, changed implementation, changed result files including build-directory results, unavailable legacy execution, zero executed tests, mismatching outputs, ineffective canaries, symlink limitations, mixed-track rejection, and resumable status.

See README.md for installation and repeatable test commands, UPSTREAM.json in the plugin for provenance, and VALIDATION.json for the machine-readable summary.
