"""Safety contracts; all mutations and Git history live in temporary fixtures."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "sync-skills.py"
KEY = "sample/reference.txt"
BASE = b"shared baseline\n"
NEW = b"installed update\n"
ENTRY = b"---\nname: sample\ndescription: Sample skill.\n---\n# Sample\n"


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else "missing"


def load_engine():
    spec = importlib.util.spec_from_file_location("skill_sync", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), "approved sync engine has not been implemented")
        self.module = load_engine()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "repository with spaces"
        self.sources = self.base / "qoder"
        self.other = self.base / "agents"
        for root in (self.repo, self.sources, self.other):
            root.mkdir()
        self.git("init", "-q")
        self.put(self.repo / "skills/sample/SKILL.md", ENTRY)
        self.put(self.repo / "skills" / KEY, BASE)
        self.put(self.sources / "sample/SKILL.md", ENTRY)
        self.put(self.sources / KEY, BASE)
        self.put(self.repo / "INDEX.md", b"[sample](skills/sample/SKILL.md)\n")
        self.put(self.repo / ".mcp.json", json.dumps({"mcpServers": {
            "chrome-devtools": {"command": "npx", "args": ["chrome-devtools-mcp"]}
        }}).encode())
        # Include real archive layout so hook exercises the validator's normal mode.
        for name in ("superpowers-using-superpowers", "superpowers-finishing-a-development-branch", "pua-pua", "pua-pua-loop"):
            self.put(self.repo / "archive/disabled" / name / "REFERENCE.md", b"Archived\n")
        for path in (
            "skills/sample/references/placeholder.txt",
            "archive/disabled/pua-pua/references/styles/pua-mama/REFERENCE.md",
            "archive/disabled/pua-pua/references/styles/pua-yes/REFERENCE.md",
        ):
            self.put(self.repo / path, b"Reference\n")
        # Real MERGED destinations imply two more active skills.
        for name, ref in (("superpowers-systematic-debugging", "diagnosing-bugs"),
                          ("claude-mem-smart-explore", "learn-codebase")):
            self.put(self.repo / f"skills/{name}/SKILL.md", ENTRY.replace(b"sample", name.encode()))
            self.put(self.repo / f"skills/{name}/references/{ref}/REFERENCE.md", b"Merged\n")
            with (self.repo / "INDEX.md").open("ab") as out:
                out.write(f"[{name}](skills/{name}/SKILL.md)\n".encode())
        self.commit_fixture()
        self.engine = self.module.Sync(self.repo, roots=[self.sources, self.other])

    def put(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def git(self, *args, data=None):
        env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                   GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid",
                   GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        return subprocess.run(["git", "-C", str(self.repo), *args], input=data,
                              capture_output=True, check=True, env=env).stdout

    def commit_fixture(self):
        self.git("add", "--all")
        tree = self.git("write-tree").strip().decode()
        commit = self.git("commit-tree", tree, "-m", "temporary fixture").strip().decode()
        self.git("update-ref", "HEAD", commit)

    def hashes(self, key=KEY):
        repo = self.repo / "skills" / key
        source = self.sources / key
        return (digest(repo.read_bytes() if repo.exists() else None),
                digest(source.read_bytes() if source.exists() else None))

    def bind(self, key=KEY):
        self.engine.bind(key, self.sources, *self.hashes(key))

    def accept(self, key=KEY):
        self.bind(key)
        self.engine.accept(key, *self.hashes(key))

    def status(self, key=KEY):
        return next(row["status"] for row in self.engine.check() if row["file"] == key)

    def snapshot(self):
        # Include mtimes/modes: rewriting unchanged baseline bytes is not read-only.
        return {str(p.relative_to(self.base)): (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_mode)
                for p in self.base.rglob("*") if p.is_file() and not p.is_symlink()}

    def run_hook(self):
        before = self.snapshot()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = self.module.hook(self.engine, expected_active=3)
        self.assertEqual(before, self.snapshot(), "hook mutated index/worktree/state/source")
        return code, output.getvalue()

    def test_readonly_without_state_and_with_unchanged_baseline(self):
        before = self.snapshot()
        self.assertEqual("equal-unbound", self.status())
        self.engine.check()
        self.assertEqual(before, self.snapshot())
        self.accept()
        before = self.snapshot()
        self.assertEqual("equal", self.status())
        self.assertEqual(before, self.snapshot())

    def test_hash_classification_ignores_mtime(self):
        self.accept()
        path = self.sources / KEY
        self.put(path, NEW)
        os.utime(path, (1, 1))
        self.assertEqual("import-candidate", self.status())
        self.put(self.repo / "skills" / KEY, b"repository update")
        self.assertEqual("conflict", self.status())
        self.put(path, BASE)
        self.assertEqual("repository-only", self.status())

    def test_binding_does_not_implicitly_accept_baseline(self):
        self.bind()
        self.put(self.sources / KEY, NEW)
        self.assertEqual("no-baseline", self.status())
        with self.assertRaises(self.module.SyncError):
            self.engine.apply({KEY: self.hashes()})

    def test_unequal_accept_never_blesses_overwrite(self):
        self.put(self.sources / KEY, NEW)
        self.bind()
        with self.assertRaises(self.module.SyncError):
            self.engine.accept(KEY, *self.hashes())
        self.engine.accept(KEY, *self.hashes(), divergence=True)
        self.assertEqual("diverged", self.status())
        with self.assertRaises(self.module.SyncError):
            self.engine.apply({KEY: self.hashes()})
        self.assertEqual(BASE, (self.repo / "skills" / KEY).read_bytes())

    def test_bind_and_accept_reject_stale_review(self):
        old = self.hashes()
        self.put(self.sources / KEY, NEW)
        with self.assertRaises(self.module.SyncError):
            self.engine.bind(KEY, self.sources, *old)
        self.bind()
        with self.assertRaises(self.module.SyncError):
            self.engine.accept(KEY, *old)

    def test_missing_and_competing_sources_are_advisory(self):
        self.accept()
        shutil.rmtree(self.sources / "sample")
        self.assertEqual("missing-source", self.status())
        self.assertEqual(0, self.run_hook()[0])
        self.put(self.sources / KEY, BASE)
        self.put(self.other / KEY, NEW)
        self.assertEqual("competing-sources", self.status())
        self.assertEqual(0, self.run_hook()[0])
        with self.assertRaises(self.module.SyncError):
            self.engine.apply({KEY: self.hashes()})

    def test_successful_import_backups_no_staging_no_source_write(self):
        self.accept()
        self.put(self.sources / KEY, NEW)
        index = self.git("ls-files", "--stage", "-z")
        report = self.engine.apply({KEY: self.hashes()})
        self.assertEqual([KEY], report["written"])
        self.assertEqual(NEW, (self.repo / "skills" / KEY).read_bytes())
        self.assertEqual(NEW, (self.sources / KEY).read_bytes())
        self.assertEqual(index, self.git("ls-files", "--stage", "-z"))
        self.assertTrue(any(p.read_bytes() == BASE for p in Path(report["backup"]).rglob("*") if p.is_file()))
        self.assertEqual("equal", self.status())

    def test_explicit_export_only_to_injected_source(self):
        self.accept()
        self.put(self.repo / "skills" / KEY, NEW)
        self.commit_fixture()
        with self.assertRaises(self.module.SyncError):
            self.engine.apply({KEY: self.hashes()})
        self.engine.apply({KEY: self.hashes()}, direction="export")
        self.assertEqual(NEW, (self.sources / KEY).read_bytes())

    def test_staged_unstaged_and_restored_deletion_reject(self):
        self.accept()
        self.put(self.sources / KEY, NEW)
        for staged in (False, True):
            with self.subTest(staged=staged):
                self.put(self.repo / "skills" / KEY, b"manual edit")
                if staged:
                    self.git("add", "--", "skills/" + KEY)
                with self.assertRaises(self.module.SyncError):
                    self.engine.apply({KEY: self.hashes()})
        # Content restored to baseline in worktree, but index has a deletion.
        self.git("update-index", "--force-remove", "skills/" + KEY)
        self.put(self.repo / "skills" / KEY, BASE)
        self.assertEqual("import-candidate", self.status())
        with self.assertRaises(self.module.SyncError):
            self.engine.apply({KEY: self.hashes()})

    def test_unstaged_restored_file_with_staged_edit_rejects(self):
        self.accept()
        self.put(self.repo / "skills" / KEY, NEW)
        self.git("add", "--", "skills/" + KEY)
        self.put(self.repo / "skills" / KEY, BASE)
        self.put(self.sources / KEY, NEW)
        with self.assertRaises(self.module.SyncError):
            self.engine.apply({KEY: self.hashes()})

    def test_whole_operation_preflight_before_backup_or_writes(self):
        second = "sample/references/placeholder.txt"
        self.put(self.sources / second, b"Reference\n")
        self.accept()
        self.accept(second)
        self.put(self.sources / KEY, NEW)
        stale = self.hashes(second)
        self.put(self.sources / second, NEW)
        before = self.snapshot()
        with self.assertRaises(self.module.SyncError):
            self.engine.apply({KEY: self.hashes(), second: stale})
        self.assertEqual(before, self.snapshot())

    def test_new_file_requires_explicit_missing_common_baseline(self):
        key = "sample/new.txt"
        self.put(self.sources / key, NEW)
        self.assertEqual("no-baseline", self.status(key))
        self.bind(key)
        with self.assertRaises(self.module.SyncError):
            self.engine.accept(key, *self.hashes(key))
        (self.sources / key).unlink()
        self.engine.accept(key, "missing", "missing")
        self.put(self.sources / key, NEW)
        self.engine.apply({key: self.hashes(key)})
        self.assertEqual(NEW, (self.repo / "skills" / key).read_bytes())

    def test_deleted_skill_not_resurrected_and_personal_unknown_skipped(self):
        for name in ("sample", "daibi", "tuomin", "pua-pua", "brand-new"):
            self.put(self.sources / name / "SKILL.md", ENTRY)
        shutil.rmtree(self.repo / "skills/sample")
        for name in ("sample", "daibi", "tuomin", "pua-pua", "brand-new"):
            key = name + "/SKILL.md"
            with self.subTest(name=name), self.assertRaises(self.module.SyncError):
                self.engine.bind(key, self.sources, "missing", digest(ENTRY))

    def test_unsafe_paths_secrets_caches_metadata_hooks_excluded(self):
        for rel in ("../escape", "/absolute", "sample/../escape", "sample/a\\b", "sample/C:evil",
                    "sample/.env", "sample/credentials.json", "sample/cache/token.json",
                    "sample/.cache/cookies.json", "sample/__pycache__/x.pyc", "sample/node_modules/x",
                    "sample/_meta.json", "sample/metadata.json", "sample/.skill-metadata.yaml",
                    "sample/hooks/pre-commit", "sample/.githooks/pre-commit", "sample/.git/config",
                    "sample/NUL", "sample/a.", "sample/%2e%2e/x", "sample/sub/SKILL.md"):
            with self.subTest(rel=rel), self.assertRaises(self.module.SyncError):
                self.engine.bind(rel, self.sources, "missing", "missing")
        self.put(self.sources / "sample/.env", b"NOT_A_REAL_SECRET")
        self.assertNotIn("sample/.env", {r["file"] for r in self.engine.check()})

    def link(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            # Directory junctions exercise Windows resolution without symlink privilege.
            subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                           check=True, capture_output=True)
        self.addCleanup(lambda: os.rmdir(link) if link.exists() else None)

    def test_shared_junction_target_deduplicates(self):
        self.link(self.other / "sample", self.sources / "sample")
        self.accept()
        self.put(self.sources / KEY, NEW)
        self.assertEqual("import-candidate", self.status())
        self.engine.apply({KEY: self.hashes()})

    def test_source_escape_and_retargeted_binding_reject(self):
        outside = self.base / "outside"
        outside.mkdir()
        self.put(outside / "reference.txt", BASE)
        self.link(self.other / "sample", outside)
        with self.assertRaises(self.module.SyncError):
            self.bind()
        os.rmdir(self.other / "sample")
        self.accept()
        (self.sources / "sample").rename(self.sources / "moved")
        self.link(self.sources / "sample", self.sources / "moved")
        with self.assertRaises(self.module.SyncError):
            self.engine.apply({KEY: self.hashes()})

    def test_repository_junction_and_child_escape_reject(self):
        self.accept()
        self.put(self.sources / KEY, NEW)
        target = self.base / "moved-repo-skill"
        (self.repo / "skills/sample").rename(target)
        self.link(self.repo / "skills/sample", target)
        with self.assertRaises(self.module.SyncError):
            self.engine.apply({KEY: self.hashes()})

    def test_unapproved_programmatic_source_argument_rejected(self):
        engine = self.module.Sync(self.repo)
        with self.assertRaises(self.module.SyncError):
            engine.bind(KEY, self.sources, *self.hashes())

    def prepare_two(self):
        key = "sample/references/placeholder.txt"
        self.put(self.sources / key, b"Reference\n")
        self.accept()
        self.accept(key)
        self.put(self.sources / KEY, NEW)
        self.put(self.sources / key, NEW)
        return {KEY: self.hashes(), key: self.hashes(key)}

    def test_failed_second_write_rolls_back_and_does_not_bless_baseline(self):
        reviews = self.prepare_two()
        state = self.engine.state_file.read_bytes()
        original = self.module.replace_file
        count = 0

        def failing(path, data):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("injected disk failure")
            return original(path, data)

        with patch.object(self.module, "replace_file", failing):
            with self.assertRaises(self.module.ApplyError) as caught:
                self.engine.apply(reviews)
        self.assertEqual([KEY], caught.exception.report["written"])
        self.assertEqual([KEY], caught.exception.report["rolled_back"])
        self.assertEqual(BASE, (self.repo / "skills" / KEY).read_bytes())
        self.assertEqual(state, self.engine.state_file.read_bytes())
        self.assertTrue(Path(caught.exception.report["backup"]).is_dir())

    def test_concurrent_source_change_is_rechecked_before_each_write(self):
        reviews = self.prepare_two()
        original = self.module.replace_file
        state = self.engine.state_file.read_bytes()

        def racing(path, data):
            original(path, data)
            if Path(path) == self.repo / "skills" / KEY:
                self.put(self.sources / "sample/references/placeholder.txt", b"raced")

        with patch.object(self.module, "replace_file", racing):
            with self.assertRaises(self.module.ApplyError):
                self.engine.apply(reviews)
        self.assertEqual(BASE, (self.repo / "skills" / KEY).read_bytes())
        self.assertEqual(state, self.engine.state_file.read_bytes())

    def test_hook_partial_staging_valid_index_invalid_worktree(self):
        self.put(self.repo / "skills/sample/SKILL.md", ENTRY + b"staged change\n")
        self.git("add", "--", "skills/sample/SKILL.md")
        self.put(self.repo / "skills/sample/SKILL.md", b"invalid unstaged")
        self.assertEqual(0, self.run_hook()[0])

    def test_hook_invalid_index_valid_worktree_blocks(self):
        self.put(self.repo / "skills/sample/SKILL.md", b"invalid staged")
        self.git("add", "--", "skills/sample/SKILL.md")
        self.put(self.repo / "skills/sample/SKILL.md", ENTRY)
        code, out = self.run_hook()
        self.assertEqual(1, code)
        self.assertIn("frontmatter", out)

    def test_hook_candidates_source_only_and_no_baseline_conflict_do_not_block(self):
        self.accept()
        self.put(self.sources / KEY, NEW)
        self.put(self.sources / "sample/new.txt", NEW)
        code, out = self.run_hook()
        self.assertEqual(0, code)
        self.assertIn("import-candidate", out)
        self.assertIn("no-baseline", out)
        self.put(self.repo / "skills" / KEY, b"manual conflict")
        self.assertEqual(0, self.run_hook()[0])

    def test_hook_unmerged_index_blocks(self):
        oid = self.git("hash-object", "-w", "--stdin", data=BASE).strip().decode()
        self.git("update-index", "--force-remove", "skills/" + KEY)
        entries = "".join(f"100644 {oid} {stage}\tskills/{KEY}\n" for stage in (1, 2, 3))
        self.git("update-index", "--index-info", data=entries.encode())
        code, out = self.run_hook()
        self.assertEqual(1, code)
        self.assertIn("unmerged", out)

    def test_hook_unsafe_index_modes_block(self):
        for mode in ("120000", "160000"):
            with self.subTest(mode=mode):
                oid = (self.git("rev-parse", "HEAD") if mode == "160000" else
                       self.git("hash-object", "-w", "--stdin", data=b"../../outside")).strip().decode()
                self.git("update-index", "--add", "--cacheinfo", f"{mode},{oid},unsafe")
                self.assertEqual(1, self.run_hook()[0])
                self.git("update-index", "--force-remove", "unsafe")

    def test_hook_does_not_execute_staged_validator_or_filters(self):
        self.put(self.repo / "validate-skills.py", b"raise RuntimeError('UNTRUSTED EXECUTED')\n")
        self.put(self.repo / ".gitattributes", b"*.md filter=must-not-run\n")
        self.git("add", "--", "validate-skills.py", ".gitattributes")
        with patch.dict(os.environ, {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "filter.must-not-run.smudge",
                                     "GIT_CONFIG_VALUE_0": "exit 97"}):
            self.assertEqual(0, self.run_hook()[0])

    def test_hook_missing_archive_and_staged_link_target_block(self):
        self.git("update-index", "--force-remove", "archive/disabled/pua-pua/REFERENCE.md")
        self.assertEqual(1, self.run_hook()[0])

    def test_linked_worktree_state_is_local_and_isolated(self):
        linked = self.base / "linked"
        self.git("worktree", "add", "--detach", str(linked), "HEAD")
        engine = self.module.Sync(linked, roots=[self.sources, self.other])
        self.assertNotEqual(engine.state_file, self.engine.state_file)
        self.assertTrue(engine.state_file.is_relative_to(self.repo / ".git/skill-sync"))
        engine.bind(KEY, self.sources, digest(BASE), digest(BASE))
        engine.accept(KEY, digest(BASE), digest(BASE))
        self.assertFalse(self.engine.state_file.exists())

    def test_cli_check_dry_run_are_readonly_and_no_test_root_flag(self):
        for command in ("check", "dry-run"):
            before = self.snapshot()
            result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--repo", str(self.repo), command],
                                    cwd=self.repo, capture_output=True)
            self.assertEqual(0, result.returncode, result.stderr.decode())
            self.assertEqual(before, self.snapshot())

    def test_thin_wrapper_no_old_copy_or_add(self):
        text = (ROOT / ".githooks/pre-commit").read_text(encoding="utf-8")
        self.assertIn("sync-skills.py", text)
        self.assertNotIn("cp -", text)
        self.assertNotIn("git add", text)
        self.assertNotIn("exit 2", text)

    def test_actual_shell_wrapper_default_55_and_partial_staging(self):
        for number in range(52):
            name = f"fixture-{number}"
            self.put(self.repo / f"skills/{name}/SKILL.md", ENTRY.replace(b"sample", name.encode()))
            with (self.repo / "INDEX.md").open("ab") as out:
                out.write(f"[{name}](skills/{name}/SKILL.md)\n".encode())
        self.put(self.repo / "sync-skills.py", SCRIPT.read_bytes())
        self.put(self.repo / "validate-skills.py", (ROOT / "validate-skills.py").read_bytes())
        self.commit_fixture()
        self.put(self.repo / "skills/sample/SKILL.md", b"invalid unstaged content")
        before = self.snapshot()
        if os.name == "nt":
            git_exe = Path(shutil.which("git")).resolve()
            bash = next(parent / suffix for parent in git_exe.parents
                        for suffix in ("bin/bash.exe", "usr/bin/bash.exe") if (parent / suffix).is_file())
        else:
            bash = Path(shutil.which("bash"))
        result = subprocess.run([str(bash), (ROOT / ".githooks/pre-commit").as_posix()], cwd=self.repo,
                                capture_output=True)
        self.assertEqual(0, result.returncode, result.stdout.decode(errors="replace") + result.stderr.decode(errors="replace"))
        self.assertIn(b"Active entries: 55; errors: 0", result.stdout)
        self.assertEqual(before, self.snapshot())

    def test_hook_corrupt_baseline_does_not_block(self):
        self.accept()
        self.engine.state_file.write_text("not JSON", encoding="utf-8")
        code, out = self.run_hook()
        self.assertEqual(0, code)
        self.assertIn("invalid local state", out)

    def test_hook_staged_link_not_worktree_link_target(self):
        self.put(self.repo / "skills/sample/SKILL.md", ENTRY + b"[reference](reference.txt)\n")
        self.git("add", "--", "skills/sample/SKILL.md")
        self.git("update-index", "--force-remove", "skills/" + KEY)
        self.assertTrue((self.repo / "skills" / KEY).is_file())
        self.assertEqual(1, self.run_hook()[0])

    def test_staged_path_traversal_case_collision_and_validator_failure(self):
        original = self.module.index_entries
        oid = self.git("hash-object", "-w", "--stdin", data=BASE).strip().decode()
        for names in (("../outside",), ("skills/sample/FILE", "skills/sample/file")):
            with self.subTest(names=names), patch.object(self.module, "index_entries",
                                                        return_value={n: ("100644", oid) for n in names}):
                self.assertEqual(1, self.run_hook()[0])
        with patch.object(self.module.subprocess, "run", wraps=subprocess.run) as run:
            def failed_validator(*args, **kwargs):
                if "--expected-active" in args[0]:
                    raise OSError("validator could not start")
                return subprocess_run(*args, **kwargs)
            subprocess_run = run._mock_wraps
            run.side_effect = failed_validator
            self.assertEqual(1, self.run_hook()[0])
        self.assertIs(self.module.index_entries, original)

    def test_unborn_repository_hook_can_validate_first_index(self):
        self.git("update-ref", "-d", "HEAD")
        self.assertEqual("excluded-or-inactive", self.engine.check()[0]["status"])
        self.assertEqual(0, self.run_hook()[0])

    def test_child_junction_escape_and_root_link_escape_reject(self):
        outside = self.base / "outside"
        outside.mkdir()
        self.link(self.sources / "sample/sub", outside)
        with self.assertRaises(self.module.SyncError):
            self.engine.bind("sample/sub/file.txt", self.sources, "missing", "missing")
        os.rmdir(self.sources / "sample/sub")
        shutil.rmtree(self.other)
        self.link(self.other, outside)
        with self.assertRaises(self.module.SyncError):
            self.bind()

    def test_sensitive_content_in_innocuous_filename_rejects_import(self):
        self.accept()
        self.put(self.sources / KEY, b"-----BEGIN PRIVATE KEY-----\nfixture-not-real\n")
        with self.assertRaises(self.module.SyncError):
            self.engine.apply({KEY: self.hashes()})
        self.assertEqual(BASE, (self.repo / "skills" / KEY).read_bytes())

    def test_deleted_entry_in_index_cannot_be_restored_from_worktree(self):
        self.git("update-index", "--force-remove", "skills/sample/SKILL.md")
        with self.assertRaises(self.module.SyncError):
            self.bind()

    def test_apply_concurrent_destination_edit_is_not_overwritten(self):
        reviews = self.prepare_two()
        second = "sample/references/placeholder.txt"
        original = self.module.replace_file
        state = self.engine.state_file.read_bytes()

        def racing(path, data):
            original(path, data)
            if Path(path) == self.repo / "skills" / KEY:
                self.put(self.repo / "skills" / second, b"concurrent user edit")

        with patch.object(self.module, "replace_file", racing):
            with self.assertRaises(self.module.ApplyError):
                self.engine.apply(reviews)
        self.assertEqual(b"concurrent user edit", (self.repo / "skills" / second).read_bytes())
        self.assertEqual(BASE, (self.repo / "skills" / KEY).read_bytes())
        self.assertEqual(state, self.engine.state_file.read_bytes())

    def test_rollback_refuses_concurrent_edit_to_already_written_file(self):
        reviews = self.prepare_two()
        original = self.module.replace_file
        state = self.engine.state_file.read_bytes()
        count = 0

        def racing(path, data):
            nonlocal count
            count += 1
            if count == 2:
                self.put(self.repo / "skills" / KEY, b"newer user work")
                raise OSError("injected failure")
            original(path, data)

        with patch.object(self.module, "replace_file", racing):
            with self.assertRaises(self.module.ApplyError) as caught:
                self.engine.apply(reviews)
        self.assertEqual([KEY], caught.exception.report["rollback_failed"])
        self.assertEqual(b"newer user work", (self.repo / "skills" / KEY).read_bytes())
        self.assertEqual(state, self.engine.state_file.read_bytes())

    def test_post_replace_failure_reports_and_rolls_back_actual_write(self):
        self.accept()
        self.put(self.sources / KEY, NEW)
        original = self.module.replace_file

        def failed_after_replace(path, data):
            original(path, data)
            if data == NEW:
                raise OSError("failure after atomic replacement")

        with patch.object(self.module, "replace_file", failed_after_replace):
            with self.assertRaises(self.module.ApplyError) as caught:
                self.engine.apply({KEY: self.hashes()})
        self.assertEqual([KEY], caught.exception.report["written"])
        self.assertEqual([KEY], caught.exception.report["rolled_back"])
        self.assertEqual(BASE, (self.repo / "skills" / KEY).read_bytes())

    def test_state_save_failure_rolls_back_entire_selection(self):
        reviews = self.prepare_two()
        state = self.engine.state_file.read_bytes()
        with patch.object(self.engine, "save", side_effect=OSError("state disk failure")):
            with self.assertRaises(self.module.ApplyError) as caught:
                self.engine.apply(reviews)
        self.assertEqual(set(reviews), set(caught.exception.report["rolled_back"]))
        self.assertEqual(state, self.engine.state_file.read_bytes())
        self.assertEqual(BASE, (self.repo / "skills" / KEY).read_bytes())

    def test_index_change_after_write_does_not_bless_baseline(self):
        self.accept()
        self.put(self.sources / KEY, NEW)
        original = self.module.replace_file
        state = self.engine.state_file.read_bytes()
        oid = self.git("hash-object", "-w", "--stdin", data=b"staged user work").strip().decode()

        def race_index(path, data):
            original(path, data)
            if data == NEW:
                self.git("update-index", "--cacheinfo", f"100644,{oid},skills/{KEY}")

        with patch.object(self.module, "replace_file", race_index):
            with self.assertRaises(self.module.ApplyError):
                self.engine.apply({KEY: self.hashes()})
        self.assertEqual(state, self.engine.state_file.read_bytes())
        self.assertIn(oid.encode(), self.git("ls-files", "--stage", "skills/" + KEY))

    def test_new_file_rollback_removes_only_our_created_file(self):
        key = "sample/new.txt"
        self.accept(key)
        self.accept()
        self.put(self.sources / key, NEW)
        self.put(self.sources / KEY, NEW)
        state = self.engine.state_file.read_bytes()
        original = self.module.replace_file
        count = 0

        def failing(path, data):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("second write failed")
            original(path, data)

        with patch.object(self.module, "replace_file", failing):
            with self.assertRaises(self.module.ApplyError) as caught:
                self.engine.apply({key: self.hashes(key), KEY: self.hashes()})
        self.assertEqual([key], caught.exception.report["rolled_back"])
        self.assertFalse((self.repo / "skills" / key).exists())
        self.assertEqual(NEW, (self.sources / key).read_bytes())
        self.assertEqual(state, self.engine.state_file.read_bytes())

    def test_preflight_case_alias_selection_is_rejected(self):
        self.accept()
        self.put(self.sources / KEY, NEW)
        with self.assertRaises(self.module.SyncError):
            self.engine.apply({KEY: self.hashes(), "sample/REFERENCE.txt": self.hashes()})

    def test_source_hardlink_rejected(self):
        (self.sources / KEY).unlink()
        os.link(self.repo / "skills" / KEY, self.sources / KEY)
        with self.assertRaises(self.module.SyncError):
            self.bind()

    def test_state_path_link_rejected_without_external_writes(self):
        outside = self.base / "external-state"
        outside.mkdir()
        self.link(self.repo / ".git/skill-sync", outside)
        before = self.snapshot()
        with self.assertRaises(self.module.SyncError):
            self.bind()
        self.assertEqual(before, self.snapshot())

    def test_cli_explicit_bind_accept_apply_and_duplicate_selection(self):
        with patch.object(self.module, "Sync", return_value=self.engine), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            args = [KEY, "--repo-hash", digest(BASE), "--source-hash", digest(BASE)]
            self.assertEqual(0, self.module.main(["bind", *args, "--source", str(self.sources)]))
            self.assertEqual(0, self.module.main(["accept", *args]))
            self.put(self.sources / KEY, NEW)
            selection = ["--file", KEY, digest(BASE), digest(NEW)]
            self.assertEqual(1, self.module.main(["apply", *selection, *selection]))
            self.assertEqual(0, self.module.main(["apply", *selection]))
        self.assertEqual(NEW, (self.repo / "skills" / KEY).read_bytes())


if __name__ == "__main__":
    unittest.main()
