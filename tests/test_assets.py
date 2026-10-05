import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ekf.core import Repository, Problem, MAX_ASSET, serialize
from ekf.seed import init_repo


def upload(name, data):
    return {"name": name, "content": base64.b64encode(data).decode("ascii")}


class AttachmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repository"
        init_repo(self.root, demo=True)
        self.repo = Repository(self.root)
        self.a = self.repo.artifact("REQ-SAFE-001")
        self.directory = Path(self.a["path"]).parent / "assets"

    def tearDown(self):
        self.temp.cleanup()

    def test_atomic_save_and_historical_binary_read(self):
        before = self.repo.head()
        image = b"\x89PNG\r\n\x1a\n\x00\xfforiginal"
        a = self.repo.save(self.a["path"], self.a["raw"] + '\n![Diagram](assets/diagram.png)\n', self.a["hash"],
                           assets=[upload("diagram.png", image), upload("notes.md", b"An attached document, not an EKF artifact.")])
        baseline = self.repo.baseline("with-images")["commit"]
        path = (self.directory / "diagram.png").as_posix()
        self.assertEqual(self.repo.asset(path), (image, "image/png"))
        self.assertEqual(self.repo.git("rev-list", "--count", before + "..HEAD").strip(), "1")
        self.assertEqual(len(self.repo.snapshot()["artifacts"]), 23)
        self.assertTrue(self.repo.snapshot()["validation"]["syntactic"])
        self.assertTrue(self.repo.clean())
        (self.repo.root / path).write_bytes(b"current version")
        self.assertEqual(self.repo.asset(path, baseline), (image, "image/png"))
        self.assertEqual((self.repo.root / path).read_bytes(), b"current version")
        self.assertEqual(self.repo.artifact(a["id"], baseline)["body"], a["body"])
        self.assertTrue(self.repo.snapshot(baseline)["validation"]["syntactic"])
        with self.assertRaises(Problem):
            self.repo.asset(path, before)

    def test_invalid_uploads_never_write_or_commit(self):
        before = self.repo.head()
        for uploads in ([upload("../outside.png", b"x")], [upload("CON.txt", b"x")],
                        [{"name": "bad.bin", "content": "not base64!"}], {},
                        [upload("a.txt", b"first"), upload("a.txt", b"second")],
                        [upload("a.txt", b"first"), upload("A.txt", b"second")],
                        [upload("big.bin", b"x" * (MAX_ASSET+1))]):
            with self.subTest(uploads=str(uploads)[:100]), self.assertRaises(Problem):
                self.repo.save(self.a["path"], self.a["raw"] + "\nChange", self.a["hash"], assets=uploads)
            self.assertFalse((self.repo.root / self.directory).exists())
            self.assertEqual(self.repo.head(), before)
            self.assertEqual(self.repo.artifact(self.a["id"])["hash"], self.a["hash"])
            self.assertTrue(self.repo.clean())

    def test_existing_assets_are_not_overwritten_and_stale_save_is_atomic(self):
        a = self.repo.save(self.a["path"], self.a["raw"]+"\nAttachment", self.a["hash"], assets=[upload("part.bin", b"old")])
        for assets, expected in [([upload("part.bin", b"replacement")], a["hash"]),
                                 ([upload("PART.bin", b"old")], a["hash"]),
                                 ([upload("new.bin", b"new")], self.a["hash"])]:
            with self.assertRaises(Problem):
                self.repo.save(a["path"], a["raw"]+"\nChange", expected, assets=assets)
            self.assertEqual((self.repo.root / self.directory / "part.bin").read_bytes(), b"old")
            self.assertFalse((self.repo.root / self.directory / "new.bin").exists())
            self.assertTrue(self.repo.clean())

    def test_failed_commit_restores_markdown_assets_and_index(self):
        original_git = self.repo.git
        def fail_commit(*args, **kwargs):
            if args[0] == "commit":
                raise Problem("Simulated failed commit")
            return original_git(*args, **kwargs)
        with patch.object(self.repo, "git", side_effect=fail_commit), self.assertRaises(Problem):
            self.repo.save(self.a["path"], self.a["raw"]+"\nChange", self.a["hash"], assets=[upload("file.bin", b"new")])
        self.assertEqual(self.repo.artifact(self.a["id"])["hash"], self.a["hash"])
        self.assertFalse((self.repo.root / self.directory / "file.bin").exists())
        self.assertTrue(self.repo.clean())

    def test_new_artifact_assets_and_incoming_links_share_one_commit(self):
        before = self.repo.head()
        raw = serialize({"ekf":"0.1", "id":"ATTACH-001", "type":"requirement", "title":"With assets"}, "[File](assets/document.pdf)")
        self.repo.save_links([{"id":self.a["id"], "expected_hash":self.a["hash"],
                               "relations":[*self.a["meta"].get("relations", []), {"type":"supports", "target":"ATTACH-001"}]}],
                             {"path":"new/location/item.md", "raw":raw, "assets":[upload("document.pdf", b"%PDF fixture")]})
        self.assertEqual((self.repo.root / "new/location/assets/document.pdf").read_bytes(), b"%PDF fixture")
        self.assertEqual(self.repo.git("rev-list", "--count", before + "..HEAD").strip(), "1")
        self.assertTrue(self.repo.clean())

    def test_read_boundaries_and_mime_do_not_execute_attachments(self):
        for path in ("../outside", ".git/config", "engineering/../ekf.yaml", "/etc/passwd", "engineering\\assets\\x"):
            for ref in ("", self.repo.head()):
                with self.subTest(path=path, ref=ref), self.assertRaises(Problem):
                    self.repo.asset(path, ref)
        self.repo.save(self.a["path"], self.a["raw"]+"\nFiles", self.a["hash"], assets=[upload("fake.png", b"<script>alert(1)</script>")])
        self.assertEqual(self.repo.asset((self.directory / "fake.png").as_posix())[1], "application/octet-stream")
        (self.repo.root / self.directory / "escape").symlink_to("/etc/passwd")
        with self.assertRaises(Problem):
            self.repo.asset((self.directory / "escape").as_posix())
