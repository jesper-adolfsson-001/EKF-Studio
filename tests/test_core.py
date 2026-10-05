import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ekf.core import Repository, Problem, analyze, parse_artifact, safe_path, scan, serialize
from ekf.seed import init_repo
from ekf.runner import Runner


class FormatTests(unittest.TestCase):
    def test_minimal_draft_example_and_extensibility(self):
        raw = '---\nekf: "0.1"\nid: REQ-HV-014\ntype: future-custom-type\ntitle: Emergency shutdown\ncustom: {unit: ms, value: 250}\n---\n\nThe battery shall disconnect.\n'
        a = parse_artifact(raw)
        self.assertEqual(a["type"], "future-custom-type")
        self.assertEqual(parse_artifact(serialize(a["meta"], a["body"]))["meta"], a["meta"])

    def test_yaml_aliases_and_unsafe_yaml(self):
        raw = '---\nekf: "0.1"\nid: A\ntype: requirement\ntitle: A\nx: &value [a, b]\ny: *value\n---\n'
        self.assertEqual(parse_artifact(raw)["meta"]["y"], ["a", "b"])
        for bad in [raw.replace('x: &value [a, b]', 'x: &value [*value]'), raw.replace('type: requirement', 'type: !!python/object/apply:os.system [echo unsafe]'), raw.replace('id: A', 'id: A\nid: B')]:
            with self.assertRaises(Exception):
                parse_artifact(bad)
        merged = raw.replace('x: &value [a, b]\ny: *value', 'defaults: &defaults {x: old}\ncustom: {<<: *defaults, x: new}')
        self.assertEqual(parse_artifact(merged)["meta"]["custom"]["x"], "new")

    def test_required_metadata_and_relation_shapes(self):
        meta = {"ekf": "0.1", "id": "A", "type": "requirement", "title": "A"}
        for key in meta:
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_artifact(serialize({k: v for k, v in meta.items() if k != key}, ""))
        for relations in ({}, [{"type": "verified-by"}], [{"type": "x", "target": "A", "resource": "a.py"}], [{"type": 5, "target": "A"}]):
            with self.subTest(relations=relations), self.assertRaises(ValueError):
                parse_artifact(serialize({**meta, "relations": relations}, ""))


class RepoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        init_repo(self.root, demo=True)
        self.repo = Repository(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_demo_conformance_and_regeneration(self):
        snapshot = self.repo.snapshot()
        self.assertEqual(len(snapshot["artifacts"]), 23)
        self.assertTrue(snapshot["validation"]["graph"])
        self.assertEqual(len(snapshot["validation"]["coverage"]), 5)
        self.assertEqual(len([r for r in snapshot["validation"]["coverage"] if r["verification"]]), 4)
        a = self.repo.artifact("REQ-SAFE-001")
        destination = self.root / "moved.md"
        (self.root / a["path"]).rename(destination)
        self.assertTrue(self.repo.snapshot()["validation"]["graph"])
        self.assertEqual(self.repo.artifact(a["id"])["path"], "moved.md")

    def test_invalid_repository_reports_errors_without_crashing(self):
        a = self.repo.artifact("REQ-SAFE-001")
        (self.root / "duplicate.md").write_text(a["raw"])
        (self.root / "bad.md").write_text('---\nid: [\n---\n')
        report = self.repo.snapshot()["validation"]
        self.assertFalse(report["syntactic"])
        self.assertTrue(any(f["rule"] == "duplicate-id" for f in report["findings"]))
        (self.root / a["path"]).write_text(a["raw"].replace("INT-SYS-001", "NONEXISTENT"))
        self.assertTrue(any(f["rule"] == "unresolved-target" for f in self.repo.snapshot()["validation"]["findings"]))

    def test_edit_roundtrip_stable_identity_and_optimistic_concurrency(self):
        a = self.repo.artifact("REQ-SAFE-001")
        baseline = self.repo.head()
        changed = self.repo.save(a["path"], a["raw"] + "\nA reviewed clarification.\n", a["hash"])
        self.assertNotEqual(self.repo.head(), baseline)
        self.assertIn("A reviewed clarification", changed["body"])
        self.assertTrue(self.repo.clean())
        self.assertNotIn("A reviewed clarification", self.repo.git("show", baseline + ":" + a["path"]))
        with self.assertRaises(Problem):
            self.repo.save(a["path"], a["raw"], a["hash"])
        with self.assertRaises(Problem):
            self.repo.save(a["path"], changed["raw"].replace("id: REQ-SAFE-001", "id: DIFFERENT"), changed["hash"])

    def test_proposals_do_not_change_main_until_review(self):
        a = self.repo.artifact("REQ-SAFE-001")
        original = self.repo.head()
        p = self.repo.propose("Clarify isolation", [{"path": a["path"], "content": a["raw"] + "\nClarification.\n"}])
        self.assertEqual(self.repo.head(), original)
        self.assertNotIn("Clarification.", self.repo.artifact(a["id"])["raw"])
        self.assertIn("REQ-SAFE-001", p["affected"])
        self.assertIn("agent:external", p["diff"])
        self.repo.workflow.update(p["id"])
        self.repo.decide(p["id"], "approve")
        self.assertNotEqual(self.repo.head(), original)
        self.assertIn("human:local: approve", self.repo.history()[0]["message"])
        self.repo.git("merge-base", "--is-ancestor", p["commit"], "HEAD")
        self.assertIn("Clarification.", self.repo.artifact(a["id"])["raw"])

    def test_stale_and_invalid_proposals_are_rejected(self):
        a = self.repo.artifact("REQ-SAFE-001")
        p = self.repo.propose("Tool", [{"path": "tools/new.py", "content": "print(42)\n"}])
        self.repo.save(a["path"], a["raw"] + "\nExternal update.\n", a["hash"])
        with self.assertRaises(Problem):
            self.repo.decide(p["id"], "approve")
        with self.assertRaises(Problem):
            self.repo.propose("Break graph", [{"path": a["path"], "content": None}])
        self.assertTrue(self.repo.clean())

    def test_review_preserves_human_machine_distinction(self):
        a = self.repo.artifact("REQ-SAFE-001")
        result = self.repo.review(a["id"], a["hash"])
        self.assertEqual(result["meta"]["verified"][-1]["by"], "human:local")
        self.assertEqual(result["meta"]["generated"]["by"], "human:example-author")

    def test_baseline_and_reports_derived_from_source(self):
        result = self.repo.baseline("prototype-1")
        self.assertEqual(result["commit"], self.repo.head())
        with self.assertRaises(Problem):
            self.repo.baseline("prototype-1")
        for kind in ("requirements", "architecture", "traceability", "verification", "safety", "review"):
            self.assertIn(self.repo.head(), self.repo.report(kind))
        self.assertIn("REQ-SAFE-001", self.repo.report())
        self.assertIn("REQ-SAFE-001 → mitigates → HAZ-001", self.repo.report("safety"))
        (self.root / "index.md").write_text("# External update\n")
        self.assertIn("Uncommitted working tree", self.repo.report())

    def test_traversal_symlinks_and_dirty_tree_are_blocked(self):
        for name in ("../outside", "/tmp/outside", ".git/config", ".ekf/agent-token", "a/../../outside"):
            with self.subTest(name=name), self.assertRaises(Problem):
                safe_path(self.root, name)
        (self.root / "escape").symlink_to("/tmp", target_is_directory=True)
        with self.assertRaises(Problem):
            safe_path(self.root, "escape/file")
        a = self.repo.artifact("REQ-SAFE-001")
        with self.assertRaises(Problem):
            self.repo.save(a["path"], a["raw"], a["hash"])

    def test_runner_fails_closed_without_bubblewrap(self):
        with patch("ekf.runner.shutil.which", return_value=None):
            runner = Runner(self.repo)
            self.assertFalse(runner.available)
            with patch("ekf.runner.subprocess.Popen") as popen:
                with self.assertRaises(Problem):
                    runner.start("echo must-not-run")
                popen.assert_not_called()

    def test_invalid_manifest_is_not_committed(self):
        before = self.repo.head()
        with self.assertRaises(Problem):
            self.repo.propose("Invalid manifest", [{"path": "ekf.yaml", "content": "not a mapping"}])
        self.assertEqual(self.repo.head(), before)
        self.assertTrue(self.repo.clean())

    def test_empty_workspace_conforms(self):
        empty = Path(self.temp.name) / "empty"
        init_repo(empty, demo=False, title="A mechanical assembly")
        repo = Repository(empty)
        snapshot = repo.snapshot()
        self.assertEqual(snapshot["manifest"]["system"]["title"], "A mechanical assembly")
        self.assertEqual(snapshot["artifacts"], [])
        self.assertTrue(snapshot["validation"]["graph"])


if __name__ == "__main__":
    unittest.main()
