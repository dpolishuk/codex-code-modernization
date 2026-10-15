#!/usr/bin/env python3
"""Validate the self-contained package without Codex or third-party packages."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"modernize", "modernize-discover", "modernize-plan", "modernize-build", "modernize-verify"}


def main():
    manifest = json.loads((ROOT / "plugin.json").read_text())
    compat = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
    assert manifest["name"] == compat["name"] == "code-modernization-codex"
    assert manifest["version"] == compat["version"]
    assert compat["skills"] == "./skills/"
    assert {p.name for p in (ROOT / "skills").iterdir()} == EXPECTED
    for path in (ROOT / "skills").glob("*/SKILL.md"):
        text = path.read_text()
        assert text.startswith("---\nname: " + path.parent.name + "\n"), path
        assert re.search(r"^description: .+", text, re.M), path
        assert text.count("\n---\n") >= 1, path
        for link in re.findall(r"\]\(([^)]+)\)", text):
            resolved = (path.parent / link).resolve()
            assert resolved.is_relative_to(ROOT) and resolved.is_file(), (path, link)
    lock = json.loads((ROOT / "UPSTREAM.json").read_text())
    for name, sha in lock["files"].items():
        assert hashlib.sha256((ROOT / "vendor/upstream" / name).read_bytes()).hexdigest() == sha, name
    for path in (ROOT / "scripts").glob("*.py"):
        compile(path.read_text(), str(path), "exec")
    print(json.dumps({"status": "CONFIG_VALIDATED", "version": manifest["version"], "skills": sorted(EXPECTED),
                      "unchanged_upstream_files": len(lock["files"]), "upstream_commit": lock["commit"]}, indent=2))


if __name__ == "__main__":
    main()
