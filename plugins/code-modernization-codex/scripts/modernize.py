#!/usr/bin/env python3
"""Codex workflow adapter. Python 3.9+, standard library only.

Runs no commands from analyzed repositories. Checkpoints are recorded observations,
not authorization or an attestation service. See references/workflow.md.
"""
import argparse
import datetime
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time

PLUGIN = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(PLUGIN / "vendor/upstream/scripts"))
import proof_pack

STAGES = ("discover", "plan", "build", "verify")
IGNORED = {".git", "__pycache__", ".pytest_cache", ".DS_Store"}
GENERATED = {"node_modules", "target", "build", "dist", "bin", "obj", ".venv"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return digest(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode())


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("refusing to overwrite a symlink: " + str(path))
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".modernize-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def save(path, obj):
    atomic(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def tree(root, generated=False):
    """Content manifest; do not follow nested symlinks. Exclusions are explicit."""
    root = Path(root)
    if not root.is_dir():
        raise ValueError("directory is missing: " + str(root))
    entries = {}
    ignored = IGNORED | (GENERATED if generated else set())
    def walk(folder):
        for item in sorted(folder.iterdir()):
            if item.name in ignored:
                continue
            rel = item.relative_to(root).as_posix()
            if item.is_symlink():
                entries[rel] = {"link": os.readlink(item)}
            elif item.is_dir():
                walk(item)
            elif item.is_file():
                h = hashlib.sha256()
                with item.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        h.update(chunk)
                entries[rel] = {"sha256": h.hexdigest(), "executable": bool(item.stat().st_mode & 0o111)}
            else:
                raise ValueError("unsupported special file: " + rel)
    walk(root)
    return entries


def safe(workspace, rel):
    path = workspace / rel
    if path.is_symlink() or not path.resolve().is_relative_to(workspace):
        raise ValueError("workspace output must not escape through a symlink: " + str(rel))
    return path


def context(args):
    ws = Path(args.workspace).resolve()
    adir = safe(ws, "analysis/" + args.system)
    state = json.loads((adir / "STATE.json").read_text())
    if state["system"] != args.system:
        raise ValueError("system does not match checkpoint")
    if (ws / "legacy" / args.system).resolve() != Path(state["source"]):
        raise ValueError("legacy link no longer points at the recorded source")
    return ws, adir, state


def required(state, stage):
    files = ["INTENT.md"]
    if STAGES.index(stage) >= 0:
        files += ["PREFLIGHT.md", "ASSESSMENT.md", "topology.json", "BUSINESS_RULES.md"]
        if state["track"] == "uplift":
            files += ["DELTA_CATALOG.md"]
    if STAGES.index(stage) >= 1:
        files += ["MODERNIZATION_BRIEF.md"]
    if STAGES.index(stage) >= 2:
        files += ["BUILD.md"]
    return files


def referenced_results(ws, adir):
    """Include runner outputs even when a build tool stores them outside analysis/."""
    runs_path = safe(ws, (adir / "equivalence/test-runs.json").relative_to(ws))
    if not runs_path.exists():
        return {}
    runs = json.loads(runs_path.read_text())
    result = {}
    for group in ("suites", "canaries"):
        for run in runs.get(group, []):
            for field in ("junit", "log"):
                paths = run.get(field, [])
                for rel in [paths] if isinstance(paths, str) else paths:
                    p = safe(ws, rel)
                    if p.is_dir():
                        result[str(rel)] = tree(p)
                    elif p.is_file():
                        result[str(rel)] = digest(p.read_bytes())
                    else:
                        result[str(rel)] = None
    return result


def signature(ws, adir, state, stage):
    data = {"source": tree(Path(state["source"])), "track": state["track"], "files": {}}
    for name in required(state, stage):
        p = safe(ws, (adir / name).relative_to(ws))
        if not p.is_file() or not p.stat().st_size:
            raise ValueError("required artifact is missing or empty: " + name)
        data["files"][name] = digest(p.read_bytes())
    if (adir / "RULE_REVIEWS.json").exists():
        data["files"]["RULE_REVIEWS.json"] = digest(safe(ws, (adir / "RULE_REVIEWS.json").relative_to(ws)).read_bytes())
    if stage in ("build", "verify"):
        target = safe(ws, state["target"])
        data["target"] = tree(target, generated=True)
        if not data["target"]:
            raise ValueError("no implementation files in target")
        data["approval"] = state.get("approval")
    if stage == "verify":
        data["evidence"] = tree(safe(ws, (adir / "equivalence").relative_to(ws)))
        data["runner_results"] = referenced_results(ws, adir)
        for name in ("BASELINE.md",):
            if (adir / name).exists():
                data["files"][name] = digest((adir / name).read_bytes())
        if (adir / "baseline").exists():
            data["baseline"] = tree(safe(ws, (adir / "baseline").relative_to(ws)))
    return canonical(data)


def status(ws, adir, state):
    unchanged = tree(Path(state["source"])) == state["source_manifest"]
    stages = {}
    previous = unchanged
    for stage in STAGES:
        record = state["stages"].get(stage)
        try:
            valid = bool(record and record["signature"] == signature(ws, adir, state, stage))
        except (OSError, ValueError):
            valid = False
        stages[stage] = "current" if previous and valid else "stale" if record else "pending"
        previous = previous and valid
    approved = bool(stages["plan"] == "current" and state.get("approval", {}).get("plan_signature") == state["stages"]["plan"]["signature"])
    verdict = state["stages"].get("verify", {}).get("verdict") if stages["verify"] == "current" else "UNVERIFIED"
    next_stage = next((s for s in STAGES if stages[s] != "current"), None)
    next_action = "source changed: start a new named baseline after reviewing the change" if not unchanged else (
        "record the user's authorization for the current plan" if next_stage == "build" and not approved else
        "$code-modernization-codex:modernize-" + next_stage + " " + state["system"] if next_stage else
        "$code-modernization-codex:modernize-verify " + state["system"] + " review gaps" if verdict != "PROVEN" else
        "$code-modernization-codex:modernize " + state["system"] + " status")
    return {"system": state["system"], "track": state["track"], "source_unchanged": unchanged,
            "stages": stages, "plan_authorized": approved, "next": next_action,
            "verdict": verdict}


def require_current(ws, adir, state, through):
    result = status(ws, adir, state)
    if not result["source_unchanged"]:
        raise ValueError("source differs from the initial content manifest; do not rebaseline silently")
    for stage in STAGES[:STAGES.index(through) + 1]:
        if result["stages"][stage] != "current":
            raise ValueError(stage + " is missing or stale; complete it first")
    return result


def initialize(args):
    ws = Path(args.workspace).resolve()
    source = Path(args.source).resolve()
    if not source.is_dir() or not any(source.iterdir()):
        raise ValueError("source must be a nonempty directory")
    # Refuse nesting that would make the evidence or target part of the baseline.
    if ws == source or ws.is_relative_to(source):
        raise ValueError("use a modernization workspace outside the source tree")
    adir = safe(ws, "analysis/" + args.system)
    link = safe(ws, "legacy/" + args.system)
    if adir.exists() or link.exists():
        raise ValueError("system already exists; use status to resume")
    target = "modernized/" + args.system + {"transform": "", "uplift": "-uplifted", "reimagine": "-reimagined"}[args.track]
    if source.is_relative_to(ws / "analysis") or source.is_relative_to(ws / "modernized") or source.is_relative_to(ws / "legacy"):
        raise ValueError("source overlaps managed directories")
    manifest = tree(source)
    if not manifest:
        raise ValueError("source contains no tracked content")
    state = {"schema": 1, "system": args.system, "track": args.track, "source": str(source), "target": target,
             "created": timestamp(), "source_manifest": manifest, "stages": {}}
    adir.mkdir(parents=True)
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(source, target_is_directory=True)
    atomic(adir / "INTENT.md", "# Intent\n\n" + args.intent + "\n\nTrack: " + args.track + "\n")
    atomic(adir / "PREFLIGHT.md", "# Preflight\n\nBaseline captured: " + timestamp() + "\n\nBuild and runtime are UNVERIFIED. Complete this preflight before discovery checkpoint.\n")
    save(adir / "STATE.json", state)
    return status(ws, adir, state)


def report(ws, adir, state):
    result = status(ws, adir, state)
    sections = ["<!doctype html><html lang='en'><meta charset='utf-8'><title>Modernization report</title>",
                "<style>body{font:16px system-ui;max-width:960px;margin:3rem auto;padding:1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;padding:1rem}</style>",
                "<h1>Code modernization — " + html.escape(state["system"]) + "</h1>",
                "<p>Local evidence only. This is not production certification or user sign-off.</p>",
                "<pre>" + html.escape(json.dumps(result, indent=2)) + "</pre>"]
    for name in ("INTENT.md", "PREFLIGHT.md", "ASSESSMENT.md", "BUSINESS_RULES.md", "MODERNIZATION_BRIEF.md", "BUILD.md", "VERIFICATION.md", "CODEX_VERIFICATION.md"):
        path = safe(ws, (adir / name).relative_to(ws))
        if path.exists():
            sections.append("<h2>" + html.escape(name) + "</h2><pre>" + html.escape(path.read_text()) + "</pre>")
    sections.append("</html>")
    atomic(adir / "REPORT.html", "\n".join(sections))
    return result | {"report": str(adir / "REPORT.html")}


def verify(ws, adir, state):
    require_current(ws, adir, state, "build")
    start = state.get("verification_start", {})
    if start.get("build_signature") != signature(ws, adir, state, "build"):
        raise ValueError("run begin-verify before the independent test run; implementation changed or no run started")
    before = signature(ws, adir, state, "verify")
    expected_track = {"transform": "rewrite", "uplift": "uplift", "reimagine": "reimagine"}[state["track"]]
    if any(subject["track"] != expected_track for subject in proof_pack.trace_rules.discover_modules(str(ws), state["system"])):
        raise ValueError("another migration track exists for this system; isolate it under a different system name")
    pack = proof_pack.overall(proof_pack.build(state["system"], str(ws)))
    proof_pack.write_outputs(pack, str(adir))
    verdict = pack["overall"]["verdict"]
    limitations = []
    if any("link" in v for v in state["source_manifest"].values()):
        limitations.append("Nested source symlink targets are outside the content attestation; review their scope.")
    if any("link" in v for v in tree(safe(ws, state["target"]), generated=True).values()):
        limitations.append("Nested target symlink targets are outside the content attestation; review their scope.")
    runs_path = adir / "equivalence/test-runs.json"
    runs = json.loads(runs_path.read_text()) if runs_path.exists() else {}
    evidence = [runs_path]
    for group in ("suites", "canaries"):
        for run in runs.get(group, []):
            for field in ("junit", "log"):
                paths = run.get(field, [])
                for rel in [paths] if isinstance(paths, str) else paths:
                    p = safe(ws, rel)
                    evidence.extend(p.rglob("*")) if p.is_dir() else evidence.append(p)
    # Development legacy outputs may be recorded baselines. New outputs and all
    # fresh outputs must come from the independent run.
    eqdir = adir / "equivalence"
    for name in ("cases.json", "fresh-cases.json"):
        for file in eqdir.rglob(name):
            doc = json.loads(file.read_text())
            for case in doc.get("cases", []):
                for side in (("legacy", "new") if name == "fresh-cases.json" else ("new",)):
                    if isinstance(case.get(side), str):
                        evidence.append(safe(ws, (file.parent / case[side]).relative_to(ws)))
    if any(p.is_file() and p.stat().st_mtime_ns < start["started_ns"] for p in evidence):
        limitations.append("Some test or comparison evidence predates begin-verify; rerun it independently.")
    if limitations and verdict == "PROVEN":
        verdict = "PARTLY PROVEN"
    after = signature(ws, adir, state, "verify")
    if before != after:
        raise ValueError("code or evidence changed while verification was being computed; rerun")
    state["stages"]["verify"] = {"signature": after, "at": timestamp(), "verdict": verdict}
    result = {"verdict": verdict, "upstream_verdict": pack["overall"]["verdict"], "limitations": limitations,
              "source_sha256": canonical(state["source_manifest"]), "build_signature": start["build_signature"],
              "upstream_commit": json.loads((PLUGIN / "UPSTREAM.json").read_text())["commit"],
              "scope": "Only recorded cases and executed checks; no production certification or human approval."}
    save(adir / "CODEX_VERIFICATION.json", result)
    atomic(adir / "CODEX_VERIFICATION.md", "# Codex verification\n\n" + verdict + "\n\n```json\n" + json.dumps(result, indent=2) + "\n```\n")
    save(adir / "STATE.json", state)
    report(ws, adir, state)
    return result, 0 if verdict == "PROVEN" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".", help="modernization workspace, outside legacy source")
    parser.add_argument("system", help="letters, digits, hyphens, underscores")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("init")
    p.add_argument("--source", required=True)
    p.add_argument("--track", choices=("transform", "uplift", "reimagine"), required=True)
    p.add_argument("--intent", required=True)
    for name in ("status", "check-build", "begin-verify", "verify", "report"):
        commands.add_parser(name)
    p = commands.add_parser("checkpoint")
    p.add_argument("stage", choices=STAGES[:-1])
    p = commands.add_parser("authorize")
    p.add_argument("--evidence", required=True, help="reference and faithful summary of actual user authorization")
    args = parser.parse_args(argv)
    try:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.system):
            raise ValueError("invalid system name")
        if args.command == "init":
            result = initialize(args)
        else:
            ws, adir, state = context(args)
            if args.command in ("status", "report"):
                result = report(ws, adir, state) if args.command == "report" else status(ws, adir, state)
            elif args.command == "authorize":
                require_current(ws, adir, state, "plan")
                if not args.evidence.strip():
                    raise ValueError("authorization evidence cannot be empty")
                state["approval"] = {"at": timestamp(), "evidence": args.evidence, "plan_signature": state["stages"]["plan"]["signature"]}
                save(adir / "STATE.json", state)
                result = status(ws, adir, state)
            elif args.command == "check-build":
                result = require_current(ws, adir, state, "plan")
                if not result["plan_authorized"]:
                    raise ValueError("current plan has no recorded user authorization")
            elif args.command == "checkpoint":
                if tree(Path(state["source"])) != state["source_manifest"]:
                    raise ValueError("source changed from baseline")
                index = STAGES.index(args.stage)
                if index:
                    result = require_current(ws, adir, state, STAGES[index - 1])
                    if args.stage == "build" and not result["plan_authorized"]:
                        raise ValueError("current plan has no recorded user authorization")
                state["stages"][args.stage] = {"at": timestamp(), "signature": signature(ws, adir, state, args.stage)}
                for stage in STAGES[index + 1:]:
                    state["stages"].pop(stage, None)
                state.pop("verification_start", None)
                save(adir / "STATE.json", state)
                result = status(ws, adir, state)
            elif args.command == "begin-verify":
                require_current(ws, adir, state, "build")
                state["verification_start"] = {"started_ns": time.time_ns(), "build_signature": signature(ws, adir, state, "build")}
                state["stages"].pop("verify", None)
                save(adir / "STATE.json", state)
                result = state["verification_start"]
            else:
                result, code = verify(ws, adir, state)
                print(json.dumps(result, indent=2))
                return code
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, proof_pack.InputError) as err:
        print("modernize: " + str(err), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
