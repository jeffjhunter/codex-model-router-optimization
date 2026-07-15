from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "router/.agents/skills/route-codex-work/scripts/snapshot_worktree.py"


class SnapshotWorktreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name) / "repo"
        self.repo.mkdir()
        self.git("init", "--quiet")
        self.git("config", "user.email", "cmro@example.invalid")
        self.git("config", "user.name", "CMRO Test")
        (self.repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        (self.repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        self.git("add", ".gitignore", "tracked.txt")
        self.git("commit", "--quiet", "-m", "baseline")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", "-C", str(self.repo), *arguments],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return result

    def take_snapshot(self) -> tuple[dict, str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--cwd", str(self.repo)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads(result.stdout), result.stdout

    def test_snapshot_is_stable_without_mutation(self) -> None:
        first, _ = self.take_snapshot()
        second, _ = self.take_snapshot()
        self.assertEqual(first["snapshot_sha256"], second["snapshot_sha256"])
        self.assertEqual(first["scope"], "tracked-index-and-untracked-content")

    def test_detects_change_to_already_modified_tracked_file(self) -> None:
        path = self.repo / "tracked.txt"
        path.write_text("first modification\n", encoding="utf-8")
        first, _ = self.take_snapshot()
        path.write_text("second modification\n", encoding="utf-8")
        second, _ = self.take_snapshot()
        self.assertNotEqual(first["snapshot_sha256"], second["snapshot_sha256"])

    def test_detects_untracked_and_index_changes(self) -> None:
        untracked = self.repo / "notes.txt"
        untracked.write_text("one\n", encoding="utf-8")
        first, _ = self.take_snapshot()
        untracked.write_text("two\n", encoding="utf-8")
        second, _ = self.take_snapshot()
        self.assertNotEqual(first["snapshot_sha256"], second["snapshot_sha256"])

        self.git("add", "notes.txt")
        third, _ = self.take_snapshot()
        self.assertNotEqual(second["snapshot_sha256"], third["snapshot_sha256"])

    def test_output_does_not_disclose_artifact_paths_or_contents(self) -> None:
        (self.repo / "private-note.txt").write_text("sensitive fixture text\n", encoding="utf-8")
        _, output = self.take_snapshot()
        self.assertNotIn("private-note.txt", output)
        self.assertNotIn("sensitive fixture text", output)

    def test_ignored_file_is_declared_out_of_scope(self) -> None:
        ignored = self.repo / "ignored.txt"
        ignored.write_text("one\n", encoding="utf-8")
        first, _ = self.take_snapshot()
        ignored.write_text("two\n", encoding="utf-8")
        second, _ = self.take_snapshot()
        self.assertEqual(first["snapshot_sha256"], second["snapshot_sha256"])
        self.assertIn("Ignored files", first["limitations"][0])


if __name__ == "__main__":
    unittest.main()
