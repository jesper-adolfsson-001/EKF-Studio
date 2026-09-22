import copy
from pathlib import Path
import tempfile
import unittest

from ekf.core import MAX_FILE, Problem, Repository, serialize
from ekf.seed import init_repo


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repository"
        init_repo(self.root, demo=True)
        self.repo = Repository(self.root)
        self.before = self.repo.baseline("design-v1")["commit"]

    def tearDown(self):
        self.temp.cleanup()

    def commit(self):
        self.repo.git("add", "--all")
        self.repo.git("commit", "-m", "Change engineering state")
        return self.repo.head()

    def test_historical_browsing_preserves_working_files_branch_and_index(self):
        a = self.repo.artifact("REQ-SAFE-001")
        self.repo.save(a["path"], a["raw"] + "\nCurrent clarification.\n", a["hash"])
        (self.root / a["path"]).write_text("Uncommitted content")
        self.repo.git("add", "--", a["path"])
        (self.root / "untracked.txt").write_text("Keep this file")
        head, status = self.repo.head(), self.repo.git("status", "--porcelain")
        branch = self.repo.git("branch", "--show-current")
        index = self.repo.git("diff", "--cached")
        old = self.repo.snapshot("design-v1")
        self.assertEqual(old["head"], self.before)
        self.assertTrue(old["readonly"])
        self.assertFalse(old["dirty"])
        self.assertEqual(self.repo.artifact(a["id"], self.before)["raw"], a["raw"])
        self.assertNotIn("Current clarification", self.repo.report("requirements", self.before))
        self.assertIn(self.before, self.repo.report("requirements", self.before))
        self.assertEqual(self.repo.head(), head)
        self.assertEqual(self.repo.git("branch", "--show-current"), branch)
        self.assertEqual(self.repo.git("status", "--porcelain"), status)
        self.assertEqual(self.repo.git("diff", "--cached"), index)
        self.assertEqual((self.root / a["path"]).read_text(), "Uncommitted content")

    def test_old_relationships_resources_and_manifest_come_from_the_same_revision(self):
        old = self.repo.snapshot(self.before)
        a = self.repo.artifact("REQ-SAFE-001")
        meta = copy.deepcopy(a["meta"])
        meta["relations"] = []
        (self.root / a["path"]).write_text(serialize(meta, a["body"]))
        (self.root / "ekf.yaml").write_text("system: {title: Later title}\n")
        resource = "tools/analyze_shutdown.py"
        original = (self.root / resource).read_text()
        (self.root / resource).unlink()
        self.commit()
        self.assertEqual(self.repo.snapshot(self.before)["manifest"], old["manifest"])
        self.assertEqual(self.repo.snapshot(self.before)["edges"], old["edges"])
        self.assertEqual(self.repo.resource(resource, self.before)["content"], original)
        impact = self.repo.impact(a["id"], ref=self.before)
        self.assertTrue(any(e["source"] == a["id"] for e in impact["edges"]))
        self.assertFalse(any(f["rule"] == "resource" for f in self.repo.snapshot(self.before)["findings"]))

    def test_compare_matches_stable_ids_including_moves_additions_and_deletions(self):
        a = self.repo.artifact("REQ-SAFE-001")
        (self.root / a["path"]).rename(self.root / "moved.md")
        removable = next(item for item in self.repo.snapshot()["artifacts"] if item["type"] == "assumption")
        (self.root / removable["path"]).unlink()
        meta = {"ekf": "0.1", "id": "REQ-NEW", "type": "requirement", "title": "New requirement"}
        (self.root / "new.md").write_text(serialize(meta, "A new statement."))
        after = self.commit()
        c = self.repo.compare(self.before, after)
        changes = {a["id"]: a for a in c["artifacts"]}
        self.assertTrue(changes[a["id"]]["moved"])
        self.assertFalse(changes[a["id"]]["content_changed"])
        self.assertEqual(changes["REQ-NEW"]["status"], "added")
        self.assertEqual(changes[removable["id"]]["status"], "removed")
        self.assertEqual(self.repo.compare(self.before, after, a["id"])["diff"], "")
        self.assertIn("+A new statement.", self.repo.compare(self.before, after, "REQ-NEW")["diff"])

    def test_comparison_reports_coverage_relationships_metadata_and_markdown(self):
        a = self.repo.artifact("REQ-SAFE-001")
        meta = copy.deepcopy(a["meta"])
        meta["relations"] = [r for r in meta["relations"] if r["type"] != "verified-by"]
        meta["status"] = "draft"
        meta["optional_note"] = None
        (self.root / a["path"]).write_text(serialize(meta, a["body"] + "\nA new limit.\n"))
        c = self.repo.compare("design-v1")
        self.assertTrue(c["after"]["dirty"])
        self.assertTrue(c["artifacts"][0]["content_changed"])
        self.assertIn("relations", c["artifacts"][0]["fields"])
        self.assertIn("optional_note", c["artifacts"][0]["fields"])
        self.assertTrue(any(e["source"] == a["id"] and e["type"] == "verified-by" for e in c["relations_removed"]))
        coverage = next(r for r in c["coverage"] if r["id"] == a["id"])
        self.assertEqual(coverage["after"]["state"], "unplanned")
        self.assertTrue(coverage["before"]["verification"])
        self.assertTrue(any(f["id"] == a["id"] and f["rule"] == "verification-coverage" for f in c["findings_added"]))
        self.assertIn("+A new limit.", self.repo.compare(self.before, identity=a["id"])["diff"])

    def test_resource_comparison_includes_untracked_binary_and_manifest_changes(self):
        (self.root / "tools/analyze_shutdown.py").write_text("print('changed')\n")
        (self.root / "new.bin").write_bytes(b"\x00\xff\x00")
        (self.root / "notes.txt").write_text("Untracked design notes")
        (self.root / "ekf.yaml").write_text("ekf: '0.1'\nsystem: {title: Changed}\n")
        c = self.repo.compare(self.before)
        resources = {r["path"]: r for r in c["resources"]}
        self.assertEqual(resources["notes.txt"]["status"], "added")
        self.assertTrue(c["manifest_changed"])
        self.assertIn("+print('changed')", self.repo.compare_resource(self.before, "", "tools/analyze_shutdown.py")["diff"])
        self.assertIn("binary", self.repo.compare_resource(self.before, "", "new.bin")["notice"].lower())
        self.assertNotIn(".ekf", " ".join(resources))

    def test_identical_baselines_have_no_differences_and_cache_is_not_mutable(self):
        self.repo.baseline("same-state")
        c = self.repo.compare("design-v1", "same-state")
        for key in ("artifacts", "relations_added", "relations_removed", "coverage", "findings_added", "findings_removed", "resources"):
            self.assertEqual(c[key], [])
        snapshot = self.repo.snapshot(self.before)
        snapshot["artifacts"].clear()
        self.assertEqual(len(self.repo.snapshot(self.before)["artifacts"]), 23)

    def test_revision_and_resource_boundaries(self):
        for ref in ("--help", "HEAD~1", "HEAD:ekf.yaml", "../outside", "missing-tag"):
            with self.subTest(ref=ref), self.assertRaises(Problem):
                self.repo.snapshot(ref)
        for path in (".git/config", ".ekf/agent-token", "../outside", "/etc/passwd", "tools/../ekf.yaml"):
            with self.subTest(path=path), self.assertRaises(Problem):
                self.repo.resource(path, self.before)
        (self.root / "secret-link.md").symlink_to("/etc/passwd")
        (self.root / ".private.md").write_text("Private")
        self.commit()
        current = self.repo.head()
        self.assertNotIn("secret-link.md", self.repo.file_index(current))
        self.assertNotIn(".private.md", self.repo.file_index(current))
        with self.assertRaises(Problem):
            self.repo.resource("secret-link.md", current)

    def test_historical_invalid_files_report_errors_and_duplicate_ids_block_comparison(self):
        a = self.repo.artifact("REQ-SAFE-001")
        (self.root / "duplicate.md").write_text(a["raw"])
        (self.root / "invalid.md").write_text("---\nid: [\n---\n")
        (self.root / "large.md").write_text("x" * (MAX_FILE + 1))
        revision = self.commit()
        errors = self.repo.snapshot(revision)["validation"]
        self.assertFalse(errors["syntactic"])
        self.assertEqual({"duplicate-id", "syntax", "size"}, {f["rule"] for f in errors["findings"] if f["severity"] == "error"})
        with self.assertRaises(Problem):
            self.repo.compare(self.before, revision)


if __name__ == "__main__":
    unittest.main()
