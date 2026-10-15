"""Behavior tests for the Codex adapter; real Python fixture, no model calls."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))
import modernize as m
import demo


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="codex-modernize-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "fixture with spaces"
        self.ws = demo.prepare(self.root)
        self.adir = self.ws / "analysis/demo"

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = m.main(["--workspace", str(self.ws), "demo", *args])
        return rc, json.loads(out.getvalue()) if out.getvalue() else None, err.getvalue()

    def state(self):
        return self.run_cli("status")[1]

    def test_real_fixture_proven_and_resumes(self):
        demo.evidence(self.ws)
        rc, data, err = self.run_cli("verify")
        self.assertEqual(rc, 0, err or str(data))
        self.assertEqual(data["verdict"], "PROVEN")
        self.assertEqual(self.state()["verdict"], "PROVEN")
        pack = json.loads((self.adir / "VERIFICATION.json").read_text())
        self.assertEqual(pack["modules"][0]["evidence"]["tests"]["executed"], 3)
        self.assertEqual(pack["signoff"]["name"], "")

    def test_difference_is_not_proven(self):
        demo.evidence(self.ws, broken=True)
        rc, data, _ = self.run_cli("verify")
        self.assertEqual(rc, 1)
        self.assertEqual(data["verdict"], "NOT PROVEN")
        self.assertIn("review gaps", self.state()["next"])

    def test_ineffective_canary_is_not_proven(self):
        demo.evidence(self.ws, ineffective_canary=True)
        rc, data, _ = self.run_cli("verify")
        self.assertEqual(rc, 1)
        self.assertEqual(data["verdict"], "NOT PROVEN")

    def test_unavailable_legacy_caps_proof(self):
        demo.evidence(self.ws, legacy_ran=False)
        rc, data, _ = self.run_cli("verify")
        self.assertEqual(rc, 1)
        self.assertEqual(data["verdict"], "PARTLY PROVEN")

    def test_stale_runner_evidence_caps_proof(self):
        demo.evidence(self.ws)
        self.assertEqual(self.run_cli("begin-verify")[0], 0)
        rc, data, _ = self.run_cli("verify")
        self.assertEqual(rc, 1)
        self.assertEqual(data["upstream_verdict"], "PROVEN")
        self.assertEqual(data["verdict"], "PARTLY PROVEN")
        self.assertTrue(data["limitations"])

    def test_changed_source_detected_even_with_preserved_mtime(self):
        p = self.root / "source/calc.py"
        st = p.stat()
        p.write_text(p.read_text().replace("value + value", "value - value"))
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
        self.assertFalse(self.state()["source_unchanged"])
        self.assertEqual(self.run_cli("check-build")[0], 2)

    def test_changed_plan_invalidates_authorization_and_build(self):
        p = self.adir / "MODERNIZATION_BRIEF.md"
        p.write_text(p.read_text() + "\nAnother module is now proposed.\n")
        state = self.state()
        self.assertEqual(state["stages"]["plan"], "stale")
        self.assertFalse(state["plan_authorized"])
        self.assertEqual(self.run_cli("check-build")[0], 2)

    def test_changed_discovery_invalidates_plan(self):
        (self.adir / "RULE_REVIEWS.json").write_text('{"reviews":[{"id":"RULE-001","verdict":"wrong"}]}')
        self.assertEqual(self.state()["stages"]["discover"], "stale")
        self.assertFalse(self.state()["plan_authorized"])

    def test_implementation_change_requires_new_build(self):
        demo.evidence(self.ws)
        p = self.ws / "modernized/demo/calc/calc.py"
        p.write_text(p.read_text() + "\n# actual source edit\n")
        self.assertEqual(self.run_cli("verify")[0], 2)
        self.assertEqual(self.state()["stages"]["build"], "stale")

    def test_evidence_change_invalidates_previous_verdict(self):
        demo.evidence(self.ws)
        self.assertEqual(self.run_cli("verify")[0], 0)
        (self.adir / "equivalence/fresh/new/10.txt").write_text("different\n")
        self.assertEqual(self.state()["stages"]["verify"], "stale")
        self.assertEqual(self.state()["verdict"], "UNVERIFIED")

    def test_external_runner_output_is_part_of_checkpoint(self):
        demo.evidence(self.ws)
        external = self.ws / "modernized/demo/calc/target/results.xml"
        external.parent.mkdir()
        external.write_bytes((self.adir / "equivalence/clean.xml").read_bytes())
        runs = json.loads((self.adir / "equivalence/test-runs.json").read_text())
        runs["suites"][0]["junit"] = [external.relative_to(self.ws).as_posix()]
        (self.adir / "equivalence/test-runs.json").write_text(json.dumps(runs))
        self.assertEqual(self.run_cli("verify")[0], 0)
        external.write_text(external.read_text().replace("<testcase", '<testcase changed="yes"', 1))
        self.assertEqual(self.state()["verdict"], "UNVERIFIED")

    def test_missing_authorization_blocks_build(self):
        path = self.adir / "STATE.json"
        state = json.loads(path.read_text())
        state.pop("approval")
        path.write_text(json.dumps(state))
        self.assertEqual(self.run_cli("check-build")[0], 2)
        self.assertEqual(self.run_cli("checkpoint", "build")[0], 2)

    def test_verify_requires_begin(self):
        self.assertEqual(self.run_cli("verify")[0], 2)

    def test_zero_executed_tests_is_not_proven(self):
        demo.evidence(self.ws)
        (self.adir / "equivalence/clean.xml").write_text('<testsuite tests="0"/>')
        runs = json.loads((self.adir / "equivalence/test-runs.json").read_text())
        runs["suites"][0]["log"] = []
        (self.adir / "equivalence/test-runs.json").write_text(json.dumps(runs))
        rc, data, _ = self.run_cli("verify")
        self.assertEqual(rc, 1)
        self.assertEqual(data["verdict"], "NOT PROVEN")

    def test_target_symlink_caps_proof(self):
        target = self.ws / "modernized/demo/calc"
        (target / "linked.txt").symlink_to(self.root / "source/calc.py")
        self.assertEqual(self.run_cli("checkpoint", "build")[0], 0)
        demo.evidence(self.ws)
        rc, data, _ = self.run_cli("verify")
        self.assertEqual(rc, 1)
        self.assertNotEqual(data["verdict"], "PROVEN")
        self.assertTrue(any("target symlink" in reason for reason in data["limitations"]))

    def test_other_track_not_silently_judged(self):
        demo.evidence(self.ws)
        other = self.ws / "modernized/demo-uplifted"
        other.mkdir()
        (other / "calc.py").write_text(demo.NEW)
        self.assertEqual(self.run_cli("verify")[0], 2)

    def test_report_preserves_text_without_rendering_markup(self):
        p = self.adir / "ASSESSMENT.md"
        p.write_text("Compare x < y & count > 0")
        self.assertEqual(self.run_cli("report")[0], 0)
        text = (self.adir / "REPORT.html").read_text()
        self.assertIn("x &lt; y &amp; count &gt; 0", text)

    def test_reinit_preserves_existing_work(self):
        before = (self.adir / "STATE.json").read_bytes()
        rc, _, _ = self.run_cli("init", "--source", str(self.root / "source"), "--track", "uplift", "--intent", "new")
        self.assertEqual(rc, 2)
        self.assertEqual((self.adir / "STATE.json").read_bytes(), before)


class PackageTests(unittest.TestCase):
    def test_pinned_upstream_files_are_unchanged(self):
        lock = json.loads((PLUGIN / "UPSTREAM.json").read_text())
        for name, sha in lock["files"].items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((PLUGIN / "vendor/upstream" / name).read_bytes()).hexdigest(), sha)

    def test_exactly_five_skills_and_links_resolve(self):
        names = {"modernize", "modernize-discover", "modernize-plan", "modernize-build", "modernize-verify"}
        self.assertEqual({p.name for p in (PLUGIN / "skills").iterdir()}, names)
        import re
        for file in (PLUGIN / "skills").glob("*/SKILL.md"):
            for rel in re.findall(r"\]\(([^)]+)\)", file.read_text()):
                self.assertTrue((file.parent / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
