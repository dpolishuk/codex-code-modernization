#!/usr/bin/env python3
"""Run a real tiny transform fixture. Writes only to a new output directory.

This fixture validates the local tooling, not a real migration or model behavior.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import modernize

LEGACY = '''import sys
def double(value):
    return value + value
if __name__ == "__main__":
    print(double(int(sys.argv[1])))
'''
NEW = LEGACY.replace("value + value", "value * 2")
TESTS = '''import unittest
from calc import double

class CalcTests(unittest.TestCase):
    def test_RULE_001_positive(self):
        self.assertEqual(double(7), 14)
    def test_RULE_001_negative(self):
        self.assertEqual(double(-3), -6)
    def test_RULE_001_zero(self):
        self.assertEqual(double(0), 0)
'''
# Transparent adapter: each XML testcase comes from an actual unittest outcome.
RUNNER = '''import sys, unittest, xml.etree.ElementTree as ET
from pathlib import Path
rows = []
class Result(unittest.TextTestResult):
    def addSuccess(self, test):
        super().addSuccess(test); rows.append((test, ""))
    def addFailure(self, test, err):
        super().addFailure(test, err); rows.append((test, "failure"))
    def addError(self, test, err):
        super().addError(test, err); rows.append((test, "error"))
    def addSkip(self, test, reason):
        super().addSkip(test, reason); rows.append((test, "skipped"))
suite = unittest.defaultTestLoader.discover(".", pattern="test_*.py")
result = unittest.TextTestRunner(resultclass=Result, verbosity=2).run(suite)
root = ET.Element("testsuite", name="CalcTests", tests=str(result.testsRun))
for test, state in rows:
    case = ET.SubElement(root, "testcase", classname=type(test).__name__, name=test._testMethodName)
    if state: ET.SubElement(case, state)
Path(sys.argv[1]).write_bytes(ET.tostring(root))
sys.exit(0 if result.wasSuccessful() else 1)
'''


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def cli(ws, *args):
    command = [sys.executable, str(Path(__file__).with_name("modernize.py")), "--workspace", str(ws), "demo", *args]
    run = subprocess.run(command, capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(run.stderr or run.stdout)
    return json.loads(run.stdout)


def prepare(root):
    root = Path(root).resolve()
    if root.exists():
        raise ValueError("demo output must be a new directory")
    source, ws = root / "source", root / "workspace"
    put(source / "calc.py", LEGACY)
    cli(ws, "init", "--source", str(source), "--track", "transform", "--intent", "Local adapter test: preserve integer doubling; no external services.")
    adir = ws / "analysis/demo"
    put(adir / "PREFLIGHT.md", "# Preflight\nLocal Python fixture, complete source, no dependencies or services.\n")
    put(adir / "ASSESSMENT.md", "# Assessment\nOne Python integer-doubling function; transform fixture.\n")
    put(adir / "topology.json", json.dumps({"modules": [{"id": "calc", "source": "calc.py"}], "edges": []}))
    put(adir / "BUSINESS_RULES.md", "### RULE-001: Double integer\n**Priority:** P0\n**Confidence:** High\n**Source:** `calc.py:2-3`\n\nGiven an integer, when double is called, then return twice its value.\n")
    cli(ws, "checkpoint", "discover")
    put(adir / "MODERNIZATION_BRIEF.md", "# Brief\n\n#### Phase 1 — Pilot\nCommand: $code-modernization-codex:modernize-build demo transform calc\nModules: calc\nExit criteria:\n- [ ] Fixture evidence inspected\n")
    cli(ws, "checkpoint", "plan")
    cli(ws, "authorize", "--evidence", "User requested local plugin testing; this authorization applies only to this generated fixture.")
    target = ws / "modernized/demo/calc"
    put(target / "calc.py", NEW)
    put(target / "test_calc.py", TESTS)
    put(target / "TRANSFORMATION_NOTES.md", "Legacy: `legacy/demo/calc.py`\nRULE-001 maps to calc.py and test_calc.py.\n")
    put(adir / "BUILD.md", "# Build\nPython integer doubling: addition becomes multiplication.\nLocal fixture only; tests and raw comparisons will run during verification.\n")
    cli(ws, "checkpoint", "build")
    return ws


def evidence(ws, *, broken=False, legacy_ran=True, ineffective_canary=False):
    root = ws.parent
    adir = ws / "analysis/demo"
    target = ws / "modernized/demo/calc"
    cli(ws, "begin-verify")
    eq = adir / "equivalence"
    eq.mkdir(exist_ok=True)
    runner = root / "run_tests.py"
    put(runner, RUNNER)
    def suite(folder, name):
        xml = eq / (name + ".xml")
        run = subprocess.run([sys.executable, "-B", str(runner), str(xml)], cwd=folder, capture_output=True, text=True)
        put(eq / (name + ".log"), run.stdout + run.stderr)
        return run.returncode
    assert suite(target, "clean") == 0
    canary = root / "canary"
    # Repeated evidence generation uses a new scratch directory without deleting
    # any caller-provided tree.
    number = 1
    while canary.exists():
        canary = root / ("canary-" + str(number)); number += 1
    shutil.copytree(target, canary, ignore=shutil.ignore_patterns("__pycache__"))
    if not ineffective_canary:
        put(canary / "calc.py", NEW.replace("value * 2", "value * 3"))
    expected = 0 if ineffective_canary else 1
    assert suite(canary, "canary") == expected
    baseline = root / "baseline-copy"
    if not baseline.exists():
        shutil.copytree(root / "source", baseline)
    for filename, prefix, inputs in (("cases.json", "dev", [1, 2]), ("fresh-cases.json", "fresh", list(range(10, 22)))):
        cases = []
        for value in inputs:
            item = {"id": prefix + str(value), "input": str(value)}
            for side, folder in (("legacy", baseline), ("new", target)):
                command = [sys.executable, "-B", str(folder / "calc.py"), str(value)]
                run = subprocess.run(command, check=True, capture_output=True, text=True)
                relative = prefix + "/" + side + "/" + str(value) + ".txt"
                # A fixture's deliberately changed output models a comparison
                # mismatch; it is never represented as a successful real run.
                output = run.stdout + ("FIXTURE DIFFERENCE\n" if broken and side == "new" and value == 10 else "")
                put(eq / relative, output)
                item[side] = relative
            cases.append(item)
        put(eq / filename, json.dumps({"system": "demo", "cases": cases}, indent=2))
    runs = {"date": modernize.timestamp(), "legacy": {"ran": legacy_ran, "how": "Python fixture scratch copy" if legacy_ran else "", "why": "" if legacy_ran else "Fixture simulates unavailable baseline"},
            "suites": [{"module": "calc", "name": "unit", "command": "python -B run_tests.py clean.xml", "junit": ["analysis/demo/equivalence/clean.xml"], "log": ["analysis/demo/equivalence/clean.log"]}],
            "canaries": [{"module": "calc", "change": "scratch multiplication by three" if not ineffective_canary else "no defect (negative test)", "junit": ["analysis/demo/equivalence/canary.xml"], "log": ["analysis/demo/equivalence/canary.log"]}]}
    put(eq / "test-runs.json", json.dumps(runs, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    ws = prepare(args.output)
    evidence(ws)
    result = cli(ws, "verify")
    print(json.dumps({"workspace": str(ws), "result": result, "report": str(ws / "analysis/demo/REPORT.html")}, indent=2))


if __name__ == "__main__":
    main()
