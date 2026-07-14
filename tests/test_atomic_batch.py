from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import routerctl


class AtomicBatchTests(unittest.TestCase):
    def test_tool_version_reports_launch_failures(self) -> None:
        with (
            mock.patch.object(routerctl.shutil, "which", return_value="codex"),
            mock.patch.object(routerctl.subprocess, "run", side_effect=OSError("access denied")),
        ):
            available, detail = routerctl.tool_version("codex", ["--version"])
        self.assertFalse(available)
        self.assertIn("access denied", detail)

    @unittest.skipIf(os.name == "nt", "POSIX mode semantics")
    def test_replacement_preserves_existing_file_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cmro-mode-") as temp:
            root = Path(temp)
            destination = root / "shared.txt"
            destination.write_bytes(b"old")
            destination.chmod(0o640)
            batch = routerctl.AtomicBatch(root)
            batch.stage([routerctl.Write(destination, b"new", "shared")])
            batch.commit()
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o640)

    def test_stage_failure_cleans_prior_staging_files_and_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cmro-stage-") as temp:
            root = Path(temp)
            batch = routerctl.AtomicBatch(root)
            writes = [
                routerctl.Write(root / "one/first.txt", b"first", "first"),
                routerctl.Write(root / "two/second.txt", b"second", "second"),
            ]
            real_mkstemp = routerctl.tempfile.mkstemp
            calls = 0

            def fail_second(*args: object, **kwargs: object) -> tuple[int, str]:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated staging failure")
                return real_mkstemp(*args, **kwargs)

            with mock.patch.object(routerctl.tempfile, "mkstemp", side_effect=fail_second):
                with self.assertRaises(OSError):
                    batch.stage(writes)

            self.assertEqual(list(root.rglob("*")), [])

    def test_commit_failure_restores_replaced_files_and_removes_new_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cmro-atomic-") as temp:
            root = Path(temp)
            first = root / "first.txt"
            second = root / "nested/second.txt"
            first.write_bytes(b"original")
            batch = routerctl.AtomicBatch(root)
            batch.stage(
                [
                    routerctl.Write(first, b"replacement", "first"),
                    routerctl.Write(second, b"new", "second"),
                ]
            )

            real_replace = routerctl.os.replace
            calls = 0

            def fail_once(source: object, destination: object) -> None:
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise OSError("simulated commit failure")
                real_replace(source, destination)

            with mock.patch.object(routerctl.os, "replace", side_effect=fail_once):
                with self.assertRaises(OSError):
                    batch.commit()

            self.assertEqual(first.read_bytes(), b"original")
            self.assertFalse(second.exists())


if __name__ == "__main__":
    unittest.main()
