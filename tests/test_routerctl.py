from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "routerctl.py"


class RouterCtlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="cmro-test-")
        self.root = Path(self.temp.name)
        self.repo = self.root / "target repo"
        self.repo.mkdir()
        subprocess.run(
            ["git", "init", "--quiet", str(self.repo)],
            check=True,
            capture_output=True,
            text=True,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *arguments: str, cli: Path = CLI) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(cli), *arguments],
            cwd=cli.parent,
            text=True,
            capture_output=True,
            check=False,
        )

    def install(self, *arguments: str, cli: Path = CLI) -> subprocess.CompletedProcess[str]:
        return self.run_cli("install", "--target", str(self.repo), *arguments, cli=cli)

    def verify(self, *arguments: str, cli: Path = CLI) -> subprocess.CompletedProcess[str]:
        return self.run_cli("verify", "--target", str(self.repo), *arguments, cli=cli)

    @staticmethod
    def tree_hashes(root: Path) -> dict[str, str]:
        return {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*")
            if path.is_file() and ".git" not in path.parts
        }

    def test_clean_install_verify_and_uninstall(self) -> None:
        installed = self.install()
        self.assertEqual(installed.returncode, 0, installed.stderr + installed.stdout)
        verified = self.verify()
        self.assertEqual(verified.returncode, 0, verified.stderr + verified.stdout)
        config = (self.repo / ".codex/config.toml").read_text(encoding="utf-8")
        self.assertIn('model = "gpt-5.6-sol"', config)
        self.assertIn('model_reasoning_effort = "xhigh"', config)

        removed = self.run_cli("uninstall", "--target", str(self.repo))
        self.assertEqual(removed.returncode, 0, removed.stderr + removed.stdout)
        self.assertFalse((self.repo / ".codex-model-router/installation.json").exists())
        self.assertFalse((self.repo / ".agents/skills/route-codex-work/SKILL.md").exists())
        self.assertFalse((self.repo / "AGENTS.md").exists())

    def test_install_is_idempotent(self) -> None:
        self.assertEqual(self.install().returncode, 0)
        before = self.tree_hashes(self.repo)
        second = self.install()
        after = self.tree_hashes(self.repo)
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        self.assertEqual(before, after)
        self.assertIn("current", second.stdout)

    def test_dry_run_writes_nothing(self) -> None:
        result = self.install("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(self.tree_hashes(self.repo), {})
        self.assertIn("no files changed", result.stdout.lower())

    def test_managed_conflict_aborts_before_writes(self) -> None:
        conflict = self.repo / ".codex/agents/luna_worker.toml"
        conflict.parent.mkdir(parents=True)
        conflict.write_text("user content\n", encoding="utf-8")
        result = self.install()
        self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
        self.assertEqual(conflict.read_text(encoding="utf-8"), "user content\n")
        self.assertFalse((self.repo / ".agents").exists())
        self.assertFalse((self.repo / ".codex-model-router").exists())

    def test_incompatible_config_is_staged_for_manual_merge(self) -> None:
        config = self.repo / ".codex/config.toml"
        config.parent.mkdir()
        original = 'model = "custom-model"\n'
        config.write_text(original, encoding="utf-8")

        result = self.install()
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertEqual(config.read_text(encoding="utf-8"), original)
        self.assertTrue((self.repo / ".codex/config.codex-model-router.example.toml").is_file())
        self.assertEqual(self.verify().returncode, 2)

        config.write_text(
            'model = "gpt-5.6-sol"\nmodel_reasoning_effort = "xhigh"\n'
            '\n[agents]\nmax_threads = 4\nmax_depth = 1\ninterrupt_message = true\n',
            encoding="utf-8",
        )
        self.assertEqual(self.verify().returncode, 0)
        removed = self.run_cli("uninstall", "--target", str(self.repo))
        self.assertEqual(removed.returncode, 0, removed.stderr + removed.stdout)
        self.assertTrue(config.is_file(), "Pre-existing config must survive uninstall")
        self.assertFalse((self.repo / ".codex/config.codex-model-router.example.toml").exists())

    def test_compatible_config_is_preserved(self) -> None:
        config = self.repo / ".codex/config.toml"
        config.parent.mkdir()
        original = (
            'model = "gpt-5.6-sol"\nmodel_reasoning_effort = "xhigh"\n\n[agents]\nmax_threads = 4\n'
            'max_depth = 1\ninterrupt_message = true\ncustom_key = "kept"\n'
        )
        config.write_text(original, encoding="utf-8")
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(config.read_text(encoding="utf-8"), original)
        self.assertEqual(self.run_cli("uninstall", "--target", str(self.repo)).returncode, 0)
        self.assertEqual(config.read_text(encoding="utf-8"), original)

    def test_toml_boolean_integer_aliases_are_not_accepted(self) -> None:
        config = self.repo / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text(
            "[agents]\nmax_threads = 4\nmax_depth = true\ninterrupt_message = 1\n",
            encoding="utf-8",
        )
        result = self.install()
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertTrue((self.repo / ".codex/config.codex-model-router.example.toml").is_file())

    def test_agents_merge_and_uninstall_preserve_user_content(self) -> None:
        agents = self.repo / "AGENTS.md"
        agents.write_text("# Team rules\n\n- Run the tests.\n", encoding="utf-8")
        self.assertEqual(self.install().returncode, 0)
        merged = agents.read_text(encoding="utf-8")
        self.assertIn("# Team rules", merged)
        self.assertIn("codex-model-router:begin", merged)
        self.assertEqual(self.run_cli("uninstall", "--target", str(self.repo)).returncode, 0)
        self.assertEqual(agents.read_text(encoding="utf-8"), "# Team rules\n\n- Run the tests.\n")

    def test_agents_crlf_bytes_survive_install_and_uninstall_exactly(self) -> None:
        agents = self.repo / "AGENTS.md"
        original = b"# Team rules\r\n\r\n- Preserve these bytes.\r\n"
        agents.write_bytes(original)

        installed = self.install()
        self.assertEqual(installed.returncode, 0, installed.stderr + installed.stdout)
        merged = agents.read_bytes()
        self.assertTrue(merged.startswith(original))
        self.assertIn(b"\r\n<!-- codex-model-router:begin -->\r\n", merged)

        removed = self.run_cli("uninstall", "--target", str(self.repo))
        self.assertEqual(removed.returncode, 0, removed.stderr + removed.stdout)
        self.assertEqual(agents.read_bytes(), original)

    def test_preexisting_exact_router_block_is_not_owned_or_removed(self) -> None:
        agents = self.repo / "AGENTS.md"
        original = (ROOT / "router/AGENTS.addendum.md").read_bytes()
        agents.write_bytes(original)

        installed = self.install()
        self.assertEqual(installed.returncode, 0, installed.stderr + installed.stdout)
        record = json.loads((self.repo / ".codex-model-router/installation.json").read_text(encoding="utf-8"))
        self.assertFalse(record["agents_owned"])
        self.assertFalse(record["agents_block_owned"])

        removed = self.run_cli("uninstall", "--target", str(self.repo))
        self.assertEqual(removed.returncode, 0, removed.stderr + removed.stdout)
        self.assertEqual(agents.read_bytes(), original)

    def test_existing_agents_override_receives_and_loses_only_router_block(self) -> None:
        override = self.repo / "AGENTS.override.md"
        override.write_text("# Temporary team override\n", encoding="utf-8")
        self.assertEqual(self.install().returncode, 0)
        self.assertFalse((self.repo / "AGENTS.md").exists())
        self.assertIn("codex-model-router:begin", override.read_text(encoding="utf-8"))
        record = json.loads((self.repo / ".codex-model-router/installation.json").read_text(encoding="utf-8"))
        self.assertEqual(record["agents_path"], "AGENTS.override.md")
        self.assertEqual(self.verify().returncode, 0)
        self.assertEqual(self.run_cli("uninstall", "--target", str(self.repo)).returncode, 0)
        self.assertEqual(override.read_text(encoding="utf-8"), "# Temporary team override\n")

    def test_new_override_after_install_invalidates_active_instructions(self) -> None:
        self.assertEqual(self.install().returncode, 0)
        (self.repo / "AGENTS.override.md").write_text("# New override\n", encoding="utf-8")
        self.assertEqual(self.verify().returncode, 2)
        reinstall = self.install()
        self.assertEqual(reinstall.returncode, 3, reinstall.stderr + reinstall.stdout)
        self.assertIn("active root instruction file changed", reinstall.stderr)

    def test_modified_agents_block_is_a_conflict(self) -> None:
        agents = self.repo / "AGENTS.md"
        agents.write_text(
            "<!-- codex-model-router:begin -->\nmodified\n<!-- codex-model-router:end -->\n",
            encoding="utf-8",
        )
        result = self.install()
        self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
        self.assertFalse((self.repo / ".agents").exists())

    def test_uninstall_retains_record_when_owned_agents_markers_are_removed(self) -> None:
        self.assertEqual(self.install().returncode, 0)
        agents = self.repo / "AGENTS.md"
        content = agents.read_text(encoding="utf-8")
        agents.write_text(
            content.replace("<!-- codex-model-router:begin -->\n", "").replace(
                "<!-- codex-model-router:end -->\n", ""
            ),
            encoding="utf-8",
        )

        removed = self.run_cli("uninstall", "--target", str(self.repo))
        self.assertEqual(removed.returncode, 2, removed.stderr + removed.stdout)
        self.assertIn("missing or modified", removed.stdout)
        self.assertTrue(agents.is_file())
        self.assertTrue((self.repo / ".codex-model-router/installation.json").is_file())

    def test_uninstall_retains_record_when_shared_agents_markers_are_removed(self) -> None:
        agents = self.repo / "AGENTS.md"
        original = "# Team rules\n"
        agents.write_text(original, encoding="utf-8")
        self.assertEqual(self.install().returncode, 0)
        content = agents.read_text(encoding="utf-8")
        agents.write_text(
            content.replace("<!-- codex-model-router:begin -->\n", "").replace(
                "<!-- codex-model-router:end -->\n", ""
            ),
            encoding="utf-8",
        )

        removed = self.run_cli("uninstall", "--target", str(self.repo))
        self.assertEqual(removed.returncode, 2, removed.stderr + removed.stdout)
        self.assertIn("missing or modified", removed.stdout)
        self.assertTrue((self.repo / ".codex-model-router/installation.json").is_file())

    def test_reversed_agents_markers_fail_without_tracebacks(self) -> None:
        agents = self.repo / "AGENTS.md"
        agents.write_text(
            "<!-- codex-model-router:end -->\ntext\n<!-- codex-model-router:begin -->\n",
            encoding="utf-8",
        )
        installed = self.install()
        self.assertEqual(installed.returncode, 3, installed.stderr + installed.stdout)
        self.assertNotIn("Traceback", installed.stderr)
        verified = self.verify()
        self.assertEqual(verified.returncode, 2, verified.stderr + verified.stdout)
        self.assertNotIn("Traceback", verified.stderr)

        agents.unlink()
        self.assertEqual(self.install().returncode, 0)
        agents.write_text(
            "<!-- codex-model-router:end -->\ntext\n<!-- codex-model-router:begin -->\n",
            encoding="utf-8",
        )
        removed = self.run_cli("uninstall", "--target", str(self.repo))
        self.assertEqual(removed.returncode, 2, removed.stderr + removed.stdout)
        self.assertNotIn("Traceback", removed.stderr)
        self.assertTrue((self.repo / ".codex-model-router/installation.json").is_file())

    def test_directory_collision_is_a_conflict(self) -> None:
        collision = self.repo / ".agents/skills/route-codex-work/SKILL.md"
        collision.mkdir(parents=True)
        result = self.install()
        self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
        self.assertTrue(collision.is_dir())
        self.assertFalse((self.repo / ".codex/agents").exists())

    def test_non_directory_ancestor_is_a_preflight_conflict(self) -> None:
        (self.repo / ".agents").write_text("not a directory\n", encoding="utf-8")
        result = self.install()
        self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
        self.assertIn("non-directory entry", result.stderr)
        self.assertFalse((self.repo / ".codex").exists())

    def test_tamper_fails_verification_and_survives_uninstall(self) -> None:
        self.assertEqual(self.install().returncode, 0)
        worker = self.repo / ".codex/agents/terra_worker.toml"
        worker.write_text(worker.read_text(encoding="utf-8") + "# local edit\n", encoding="utf-8")
        self.assertEqual(self.verify().returncode, 2)
        removed = self.run_cli("uninstall", "--target", str(self.repo))
        self.assertEqual(removed.returncode, 2, removed.stderr + removed.stdout)
        self.assertTrue(worker.is_file())
        self.assertIn("local edit", worker.read_text(encoding="utf-8"))
        record = self.repo / ".codex-model-router/installation.json"
        self.assertTrue(record.is_file(), "Partial uninstall must retain its ownership record")

        worker.write_bytes((ROOT / "router/.codex/agents/terra_worker.toml").read_bytes())
        completed = self.run_cli("uninstall", "--target", str(self.repo))
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertFalse(worker.exists())
        self.assertFalse(record.exists())

    def test_malicious_install_record_cannot_claim_arbitrary_path(self) -> None:
        self.assertEqual(self.install().returncode, 0)
        outside = self.root / "must-survive.txt"
        outside.write_text("important\n", encoding="utf-8")
        record_path = self.repo / ".codex-model-router/installation.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["owned_files"].append("../../must-survive.txt")
        record_path.write_text(json.dumps(record), encoding="utf-8")

        result = self.run_cli("uninstall", "--target", str(self.repo))
        self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
        self.assertEqual(outside.read_text(encoding="utf-8"), "important\n")
        self.assertTrue((self.repo / ".agents/skills/route-codex-work/SKILL.md").is_file())

    def test_non_object_install_record_has_controlled_failures(self) -> None:
        self.assertEqual(self.install().returncode, 0)
        record = self.repo / ".codex-model-router/installation.json"
        record.write_text("[]\n", encoding="utf-8")

        for command, expected in (("install", 3), ("verify", 2), ("uninstall", 3)):
            result = self.run_cli(command, "--target", str(self.repo))
            self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
            self.assertNotIn("Traceback", result.stderr)

    def test_verify_json_is_machine_readable(self) -> None:
        self.assertEqual(self.install().returncode, 0)
        result = self.verify("--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertTrue(value["passed"])
        self.assertTrue(value["checks"])
        self.assertEqual(value["scope"], "distribution")
        self.assertEqual(value["version"], "3.0.1")
        self.assertTrue(value["limitations"])

    def test_doctor_json_labels_distribution_scope(self) -> None:
        result = self.run_cli("doctor", "--target", str(self.repo), "--json")
        self.assertIn(result.returncode, {0, 2}, result.stderr + result.stdout)
        value = json.loads(result.stdout)
        self.assertEqual(value["schema"], "cmro.doctor.v1")
        self.assertEqual(value["scope"], "distribution")
        self.assertEqual(value["version"], "3.0.1")
        backend = next(item for item in value["findings"] if item["name"] == "backend_contract")
        self.assertTrue(backend["passed"])
        self.assertTrue(value["limitations"])

    def test_target_must_be_git_root(self) -> None:
        child = self.repo / "child"
        child.mkdir()
        result = self.run_cli("install", "--target", str(child))
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertEqual(self.tree_hashes(child), {})

    def test_non_git_requires_explicit_override(self) -> None:
        outside = self.root / "not git"
        outside.mkdir()
        rejected = self.run_cli("install", "--target", str(outside))
        self.assertEqual(rejected.returncode, 2)
        accepted = self.run_cli("install", "--target", str(outside), "--allow-non-git")
        self.assertEqual(accepted.returncode, 0, accepted.stderr + accepted.stdout)

    def test_unexpected_payload_file_is_rejected(self) -> None:
        copy = self.root / "distribution"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        (copy / "router/.codex/agents/surprise.toml").write_text("name='surprise'\n", encoding="utf-8")
        result = self.install(cli=copy / "routerctl.py")
        self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
        self.assertIn("allowlist mismatch", result.stderr.lower())

    def test_payload_hash_tamper_is_rejected(self) -> None:
        copy = self.root / "distribution"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        skill = copy / "router/.agents/skills/route-codex-work/SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
        result = self.install(cli=copy / "routerctl.py")
        self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
        self.assertIn("hash mismatch", result.stderr.lower())

    def test_non_object_source_manifest_is_rejected_cleanly(self) -> None:
        copy = self.root / "distribution"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        (copy / "router/MANIFEST.json").write_text("[]\n", encoding="utf-8")
        result = self.install(cli=copy / "routerctl.py")
        self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("json object", result.stderr.lower())

    def test_manifest_command_reports_allowlisted_files(self) -> None:
        result = self.run_cli("manifest")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        value = json.loads(result.stdout)
        self.assertEqual(value["scope"], "distribution")
        self.assertEqual(value["version"], "3.0.1")
        self.assertIn(".codex/agents/luna_worker.toml", value["files"])
        self.assertIn(".codex/agents/terra_worker.toml", value["files"])
        self.assertIn(".codex/agents/sol_reviewer.toml", value["files"])

    def test_validate_run_command_uses_allowlisted_validator(self) -> None:
        record = {
            "schema": "cmro.final.v3",
            "run_id": "cmro-test",
            "plan_version": 1,
            "status": "needs_human_review",
            "attempts": 0,
            "backend": "codex_app_tasks",
            "worker_id": None,
            "reviewer_id": None,
            "identity": {
                role: {"control_plane_pinned": False, "runtime_observed": False}
                for role in ("root", "worker", "reviewer")
            },
            "requirements": [{"rq_id": "RQ-001", "ac_ids": ["AC-001"], "status": "not_verified"}],
            "blockers": ["Identity preflight did not complete"],
        }
        path = self.root / "run.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        result = self.run_cli("validate-run", "--record", str(path))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_validate_packet_command_uses_allowlisted_validator_and_context(self) -> None:
        packet = {
            "schema": "cmro.worker.v3",
            "run_id": "cmro-test",
            "plan_version": 1,
            "attempt": 1,
            "worker": {
                "id": "terra-task",
                "backend": "codex_app_tasks",
                "route": "terra_worker",
                "configured_model": "gpt-5.6-terra",
            },
            "status": "done",
            "summary": "Implemented the scoped file.",
            "changed_paths": [{"path": "src/app.py", "action": "modified"}],
            "checks": [
                {
                    "command": "python -m unittest",
                    "exit_code": 0,
                    "result": "pass",
                    "evidence": "Focused test passed.",
                }
            ],
            "criteria": [
                {"ac_id": "AC-001", "status": "pass", "evidence": "Artifact inspected."}
            ],
            "blockers": [],
            "limitations": [],
        }
        context = {
            "run_id": "cmro-test",
            "plan_version": 1,
            "backend": "codex_app_tasks",
            "actor_id": "terra-task",
            "route": "terra_worker",
            "configured_model": "gpt-5.6-terra",
            "attempt": 1,
            "acceptance_ids": ["AC-001"],
            "allowed_paths": ["src/**"],
        }
        packet_path = self.root / "worker.json"
        context_path = self.root / "context.json"
        packet_path.write_text(json.dumps(packet), encoding="utf-8")
        context_path.write_text(json.dumps(context), encoding="utf-8")
        result = self.run_cli(
            "validate-packet",
            "--packet",
            str(packet_path),
            "--context",
            str(context_path),
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(json.loads(result.stdout)["valid"])
        self.assertTrue(json.loads(result.stdout)["authoritative_context_bound"])

        unbound = self.run_cli("validate-packet", "--packet", str(packet_path))
        self.assertEqual(unbound.returncode, 2)
        self.assertIn("--context", unbound.stderr)

    def test_version(self) -> None:
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "routerctl 3.0.1")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_linklike_destination_is_rejected_when_supported(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        link = self.repo / ".agents"
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Current account cannot create symlinks")
        result = self.install()
        self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
        self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_target_with_linklike_parent_is_canonicalized_when_supported(self) -> None:
        real_parent = self.root / "real-parent"
        nested_repo = real_parent / "nested-repo"
        nested_repo.mkdir(parents=True)
        subprocess.run(["git", "init", "--quiet", str(nested_repo)], check=True)
        alias_parent = self.root / "alias-parent"
        try:
            os.symlink(real_parent, alias_parent, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Current account cannot create symlinks")
        result = self.run_cli("install", "--target", str(alias_parent / "nested-repo"))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue((nested_repo / ".agents/skills/route-codex-work/SKILL.md").is_file())
        verified = self.run_cli("verify", "--target", str(alias_parent / "nested-repo"))
        self.assertEqual(verified.returncode, 0, verified.stderr + verified.stdout)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_target_that_is_itself_a_link_is_rejected_when_supported(self) -> None:
        linked_repo = self.root / "linked-repo"
        try:
            os.symlink(self.repo, linked_repo, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Current account cannot create symlinks")
        result = self.run_cli("install", "--target", str(linked_repo))
        self.assertEqual(result.returncode, 3, result.stderr + result.stdout)
        self.assertFalse((self.repo / ".agents").exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_post_install_link_swap_cannot_escape_verify_or_uninstall(self) -> None:
        self.assertEqual(self.install().returncode, 0)
        outside = self.root / "outside-agents"
        shutil.move(str(self.repo / ".agents"), str(outside))
        try:
            os.symlink(outside, self.repo / ".agents", target_is_directory=True)
        except (OSError, NotImplementedError):
            shutil.move(str(outside), str(self.repo / ".agents"))
            self.skipTest("Current account cannot create symlinks")

        skill = outside / "skills/route-codex-work/SKILL.md"
        before = skill.read_bytes()
        verified = self.verify()
        self.assertEqual(verified.returncode, 2, verified.stderr + verified.stdout)
        removed = self.run_cli("uninstall", "--target", str(self.repo))
        self.assertEqual(removed.returncode, 3, removed.stderr + removed.stdout)
        self.assertEqual(skill.read_bytes(), before)
        self.assertTrue((self.repo / ".codex/agents/terra_worker.toml").is_file())
        self.assertTrue((self.repo / ".codex-model-router/installation.json").is_file())


if __name__ == "__main__":
    unittest.main()
