import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ekf.core import Problem, Repository, serialize
from ekf.seed import init_repo


class LinkEditingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "repo"
        init_repo(root, demo=True)
        self.repo = Repository(root)

    def tearDown(self):
        self.temp.cleanup()

    def update(self, identity, relations=None):
        a = self.repo.artifact(identity)
        return {"id": identity, "expected_hash": a["hash"],
                "relations": copy.deepcopy(a["meta"].get("relations", []) if relations is None else relations)}

    def test_both_directions_one_commit_and_metadata_preserved(self):
        ids = ["REQ-SAFE-001", "INT-SYS-001"]
        before = {identity: self.repo.artifact(identity) for identity in ids}
        head = self.repo.head()
        outgoing, incoming = (self.update(identity) for identity in ids)
        outgoing["relations"].append({"type": "custom-supports", "target": "INT-SYS-001", "rationale": {"weight": 0.5}})
        incoming["relations"].append({"type": "depends-on", "target": "REQ-SAFE-001"})
        result = self.repo.save_links([outgoing, incoming])
        self.assertEqual(set(result["updated"]), set(ids))
        self.assertEqual(self.repo.git("rev-list", "--count", head + "..HEAD").strip(), "1")
        for update in (outgoing, incoming):
            after = self.repo.artifact(update["id"])
            self.assertEqual(after["meta"]["relations"], update["relations"])
            self.assertEqual({k: v for k, v in after["meta"].items() if k != "relations"},
                             {k: v for k, v in before[update["id"]]["meta"].items() if k != "relations"})
            self.assertEqual(after["body"], before[update["id"]]["body"])
        self.assertTrue(self.repo.clean())

    def test_new_artifact_and_incoming_sources_saved_together(self):
        incoming = self.update("INT-SYS-001")
        incoming["relations"].append({"type": "supports", "target": "NEW-001"})
        raw = serialize({"ekf": "0.1", "id": "NEW-001", "type": "requirement", "title": "New concept",
                         "relations": [{"type": "refines", "target": "INT-SYS-001"}]}, "Draft meaning.")
        result = self.repo.save_links([incoming], {"path": "engineering/new.md", "raw": raw})
        self.assertEqual(result["id"], "NEW-001")
        self.assertEqual(self.repo.artifact("NEW-001")["body"], "Draft meaning.\n")
        self.assertTrue(self.repo.snapshot()["validation"]["graph"])

    def test_stale_source_blocks_every_change_and_new_draft(self):
        update = self.update("INT-SYS-001")
        a = self.repo.artifact("INT-SYS-001")
        self.repo.save(a["path"], a["raw"] + "\nConcurrent edit.\n", a["hash"])
        head = self.repo.head()
        other = self.update("REQ-SAFE-001", [])
        raw = serialize({"ekf": "0.1", "id": "NEW-001", "type": "requirement", "title": "New"}, "Draft")
        with self.assertRaisesRegex(Problem, "INT-SYS-001 changed"):
            self.repo.save_links([other, update], {"path": "engineering/new.md", "raw": raw})
        self.assertEqual(self.repo.head(), head)
        self.assertFalse((self.repo.root / "engineering/new.md").exists())
        self.assertNotEqual(self.repo.artifact("REQ-SAFE-001")["meta"]["relations"], [])
        self.assertTrue(self.repo.clean())

    def test_invalid_target_and_duplicate_source_do_not_write(self):
        head = self.repo.head()
        update = self.update("INT-SYS-001", [{"type": "depends-on", "target": "UNKNOWN"}])
        with self.assertRaisesRegex(Problem, "unknown artifact"):
            self.repo.save_links([self.update("REQ-SAFE-001", []), update])
        with self.assertRaisesRegex(Problem, "each source"):
            self.repo.save_links([update, update])
        self.assertEqual(self.repo.head(), head)
        self.assertTrue(self.repo.clean())

    def test_failed_commit_restores_all_files_and_index(self):
        before = {a["id"]: a["raw"] for a in self.repo.snapshot()["artifacts"]}
        head = self.repo.head()
        git = self.repo.git
        def failing_git(*args, **kwargs):
            if args[0] == "commit":
                raise Problem("Simulated Git commit failure")
            return git(*args, **kwargs)
        raw = serialize({"ekf": "0.1", "id": "NEW-001", "type": "requirement", "title": "New"}, "Draft")
        with patch.object(self.repo, "git", side_effect=failing_git), self.assertRaisesRegex(Problem, "Simulated"):
            self.repo.save_links([self.update("REQ-SAFE-001", []), self.update("INT-SYS-001", [])],
                                 {"path": "engineering/new.md", "raw": raw})
        self.assertEqual(self.repo.head(), head)
        self.assertEqual({a["id"]: a["raw"] for a in self.repo.snapshot()["artifacts"]}, before)
        self.assertTrue(self.repo.clean())

    def test_resource_metadata_and_exact_body_survive_retyping_and_removal(self):
        a = self.repo.artifact("REQ-SAFE-001")
        meta = copy.deepcopy(a["meta"])
        meta["relations"] = [{"type": "implemented-by", "resource": "tools/analyze_shutdown.py", "custom": ["keep", 42]},
                             {"type": "refines", "target": "INT-SYS-001"}]
        a = self.repo.save(a["path"], serialize(meta, a["body"]) + "\n\n", a["hash"])
        before_body = a["raw"].split("---\n", 2)[2]
        update = self.update(a["id"])
        update["relations"][0]["type"] = "custom-method"
        update["relations"].pop()
        self.repo.save_links([update])
        after = self.repo.artifact(a["id"])
        self.assertEqual(after["raw"].split("---\n", 2)[2], before_body)
        self.assertEqual(after["meta"]["relations"], update["relations"])


if __name__ == "__main__":
    unittest.main()
