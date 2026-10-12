#!/usr/bin/env python3
"""Explicit, file-level skill synchronization. Checks and the hook are read-only.

CLI: check | dry-run | bind FILE --source ROOT --repo-hash H --source-hash H
     accept FILE --repo-hash H --source-hash H [--divergence]
     approve FILE --repo-hash H --source-hash H
     apply --file FILE REPO_HASH SOURCE_HASH [--file ...] [--direction export]
Hashes are SHA-256 of raw bytes, or 'missing'. Bind selects provenance; accept
records an equal common baseline (or a non-authorizing divergence). Neither
copies files. A new filename requires explicit review of shared absence BEFORE
creation at the source. No deletion, filters, staging, commits or hook installs.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unicodedata
import uuid

MISSING = "missing"
EXCLUDED_SKILLS = {"daibi", "tuomin", "diagnosing-bugs", "claude-mem-learn-codebase",
                   "pua-mama", "pua-yes", "pua-pua", "pua-pua-loop",
                   "superpowers-using-superpowers", "superpowers-finishing-a-development-branch"}
EXCLUDED_PARTS = {"hooks", "cache", "caches", "__pycache__", "node_modules", "venv",
                  "dist", "build", "target", "_meta.json", "metadata.json", "package-lock.json",
                  "yarn.lock", "pnpm-lock.yaml", "uv.lock", "skill-lock.json", "skills-lock.json"}
REGULAR = {"100644", "100755"}


class SyncError(Exception):
    pass


class ApplyError(SyncError):
    def __init__(self, message, report):
        super().__init__(message)
        self.report = report


def sha(data):
    return MISSING if data is None else hashlib.sha256(data).hexdigest()


def safe_name(name):
    """Portable Git/materialization path, including Windows ADS/device guards."""
    parts = name.split("/")
    if (not name or "\\" in name or unicodedata.normalize("NFC", name) != name
            or any(ord(c) < 32 or ord(c) == 127 for c in name)):
        raise SyncError("unsafe-path: " + repr(name))
    for part in parts:
        if (part in {"", ".", ".."} or part.rstrip(" .") != part
                or any(c in part for c in ':<>"|?*%') or part.casefold() == ".git"
                or re.fullmatch(r"(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", part)):
            raise SyncError("unsafe-path: " + repr(name))
    return parts


def sync_name(key):
    parts = safe_name(key)
    if len(parts) < 2 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", parts[0]):
        raise SyncError("expected SKILL/FILE")
    if parts[0] in EXCLUDED_SKILLS:
        raise SyncError("excluded-skill: " + parts[0])
    for part in parts[1:]:
        low = part.casefold()
        if (low.startswith(".") or low in EXCLUDED_PARTS
                or re.search(r"credential|secret|password|cookie|token|session|^id_rsa|^id_ed25519", low)
                or low.startswith(("pre-commit", "post-commit", "pre-push"))
                or low.endswith((".pem", ".key", ".p12", ".pfx", ".pyc", ".class", ".lock"))):
            raise SyncError("excluded-file: " + key)
    if any(p.casefold() == "skill.md" for p in parts[2:]):
        raise SyncError("nested active entry: " + key)
    return parts


def linklike(path):
    try:
        info = path.lstat()
        return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)
    except FileNotFoundError:
        return False


def plain_path(root, relative):
    """Reject links/reparse points below the already-authorized canonical root."""
    path = root
    for part in safe_name(relative):
        if path.is_dir() and any(p.name.casefold() == part.casefold() and p.name != part
                                 for p in path.iterdir()):
            raise SyncError("ambiguous-case: " + relative)
        path = path / part
        if linklike(path):
            raise SyncError("unsafe-link: " + str(path))
    if not path.resolve().is_relative_to(root):
        raise SyncError("path-escape: " + relative)
    return path


def read_bytes(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if linklike(path) or not stat.S_ISREG(info.st_mode) or info.st_nlink > 1:
        raise SyncError("not a single regular file: " + str(path))
    return path.read_bytes()


def replace_file(path, data):
    """Atomic file replacement; preserve existing permissions, never execute it."""
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    fd, temporary = tempfile.mkstemp(prefix=".skill-sync-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def git(repo, *args, data=None, allow_missing=False):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_REPLACE_OBJECTS="1")
    result = subprocess.run(["git", "-C", str(repo), *args], input=data,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if result.returncode == 1 and allow_missing:
        return b""
    if result.returncode:
        raise SyncError("git " + args[0] + ": " + result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def committed_bytes(repo, data, oid):
    """Committed worktree bytes; core.autocrlf=true keeps CRLF in a clean text worktree."""
    if data is None:
        return False
    blob = git(repo, "cat-file", "blob", oid)
    if data == blob:
        return True
    if b"\x00" in data[:8000]:
        return False
    if git(repo, "config", "--get", "core.autocrlf", allow_missing=True).strip() != b"true":
        return False
    return data.replace(b"\r\n", b"\n") == blob


def index_entries(repo):
    raw = git(repo, "ls-files", "--stage", "-z")
    entries = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        meta, name = record.split(b"\t", 1)
        mode, oid, stage = meta.decode("ascii").split()
        name = name.decode("utf-8")
        if stage != "0":
            raise SyncError("unmerged index: " + name)
        safe_name(name)
        if mode not in REGULAR:
            raise SyncError("unsafe index mode " + mode + ": " + name)
        entries[name] = (mode, oid)
    return entries


def head_entries(repo):
    if not git(repo, "rev-parse", "--verify", "--quiet", "HEAD", allow_missing=True):
        return {}
    entries = {}
    for record in git(repo, "ls-tree", "-r", "-z", "HEAD").split(b"\0"):
        if record:
            meta, name = record.split(b"\t", 1)
            mode, kind, oid = meta.decode().split()
            entries[name.decode("utf-8")] = (mode, oid)
    return entries


class Sync:
    def __init__(self, repo, roots=None):
        self.repo = Path(repo).resolve()
        actual = Path(git(self.repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
        if actual != self.repo:
            raise SyncError("--repo must be the repository root")
        # Injection is programmatic only. CLI can never turn an arbitrary root into an allowed one.
        self.roots = tuple(Path(os.path.abspath(p)) for p in (roots if roots is not None else
                           [Path.home() / ".qoder/skills", Path.home() / ".agents/skills"]))
        common = Path(git(self.repo, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip()).resolve()
        gitdir = git(self.repo, "rev-parse", "--absolute-git-dir").strip()
        self.common = common
        self.state_file = common / "skill-sync" / hashlib.sha256(gitdir).hexdigest()[:16] / "state.json"

    def state(self):
        path = plain_path(self.common, self.state_file.relative_to(self.common).as_posix())
        data = read_bytes(path)
        try:
            value = json.loads(data) if data is not None else {"version": 1, "files": {}}
            if value["version"] != 1 or not isinstance(value["files"], dict):
                raise ValueError("unsupported state")
            for key, record in value["files"].items():
                sync_name(key)
                if not isinstance(record, dict) or not all(isinstance(record[p], str) for p in ("root", "target")):
                    raise ValueError("invalid binding")
                baseline = record.get("baseline")
                if baseline is not None and baseline != MISSING and not re.fullmatch(r"[a-f0-9]{64}", baseline):
                    raise ValueError("invalid baseline")
                approved = record.get("export_reviewed")
                if approved is not None and (not isinstance(approved, list) or len(approved) != 2
                                             or not all(isinstance(value, str) for value in approved)):
                    raise ValueError("invalid export approval")
            return value
        except (ValueError, KeyError, TypeError) as exc:
            raise SyncError("invalid local state: " + str(exc)) from exc

    @contextmanager
    def locked(self, expected):
        plain_path(self.common, self.state_file.relative_to(self.common).as_posix())
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        lock = self.state_file.with_suffix(".lock")
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise SyncError("another sync operation holds the local lock") from exc
        os.close(fd)
        try:
            if self.state() != expected:
                raise SyncError("local review state changed; review again")
            yield
        finally:
            lock.unlink()

    def save(self, state):
        path = plain_path(self.common, self.state_file.relative_to(self.common).as_posix())
        replace_file(path, (json.dumps(state, indent=2, sort_keys=True) + "\n").encode())

    def active(self):
        indexed = index_entries(self.repo)
        heads = head_entries(self.repo)
        names = set()
        for name in indexed.keys() & heads.keys():
            parts = name.split("/")
            if len(parts) == 3 and parts[0] == "skills" and parts[2] == "SKILL.md" and parts[1] not in EXCLUDED_SKILLS:
                try:
                    if plain_path(self.repo, name).is_file():
                        names.add(parts[1])
                except SyncError:
                    pass
        return names

    def sources(self, skill):
        targets = {}
        for root in self.roots:
            resolved = root.resolve()
            if not any(resolved.is_relative_to(allowed) for allowed in self.roots):
                raise SyncError("source-root-escape")
            path = root / skill
            target = path.resolve()
            if not any(target.is_relative_to(allowed) for allowed in self.roots):
                raise SyncError("source-escape: " + skill)
            if path.exists():
                if not target.is_dir() or target in self.roots or target.is_relative_to(self.repo):
                    raise SyncError("unsafe source target: " + skill)
                targets.setdefault(target, []).append(root)
        return targets

    def inspect(self, key, state, active=None):
        parts = sync_name(key)
        if parts[0] not in (self.active() if active is None else active):
            raise SyncError("inactive-or-deleted: " + parts[0])
        repo_path = plain_path(self.repo, "skills/" + key)
        repo_hash = sha(read_bytes(repo_path))
        targets = self.sources(parts[0])
        if len(targets) > 1:
            raise SyncError("competing-sources")
        record = state["files"].get(key)
        target = next(iter(targets), None)
        if record:
            bound_root = Path(record["root"])
            if bound_root not in self.roots:
                raise SyncError("unapproved source binding")
            bound = (bound_root / parts[0]).resolve()
            if bound != Path(record["target"]):
                raise SyncError("source binding retargeted")
            if target is not None and target != bound:
                raise SyncError("source binding unavailable")
            if not (bound_root / parts[0]).is_dir():
                target = None
        source_path = plain_path(target, "/".join(parts[1:])) if target is not None else None
        source_hash = sha(read_bytes(source_path)) if source_path is not None else MISSING
        baseline = record.get("baseline") if record else None
        if target is None or (source_hash == MISSING and baseline not in (None, MISSING)):
            status = "missing-source"
        elif repo_hash == source_hash:
            status = "equal" if record and baseline == repo_hash else "equal-unbound"
        elif record and record.get("diverged"):
            status = "diverged"
        elif baseline is None:
            status = "no-baseline"
        elif repo_hash == baseline:
            status = "import-candidate"
        elif source_hash == baseline:
            status = "repository-only"
        else:
            status = "conflict"
        return {"file": key, "status": status, "repo_hash": repo_hash, "source_hash": source_hash,
                "baseline": baseline, "bound": bool(record), "source": str(target) if target else None}

    def check(self):
        state, active = self.state(), self.active()
        keys = set(state["files"])
        rows = []
        for skill in sorted(active):
            roots = [self.repo / "skills" / skill]
            try:
                roots.extend(self.sources(skill))
            except (SyncError, OSError, RuntimeError) as exc:
                rows.append({"file": skill + "/SKILL.md", "status": str(exc)})
            for root in roots:
                # Walk only regular directories; don't recurse into junctions, caches or hooks.
                for directory, dirs, files in os.walk(root, followlinks=False):
                    def permitted(name):
                        key = skill + "/" + (Path(directory) / name).relative_to(root).as_posix()
                        try:
                            sync_name(key)
                            return not linklike(Path(directory) / name)
                        except SyncError:
                            return False
                    dirs[:] = [d for d in dirs if permitted(d)]
                    keys.update(skill + "/" + (Path(directory) / f).relative_to(root).as_posix()
                                for f in files if permitted(f))
        for key in sorted(keys):
            try:
                rows.append(self.inspect(key, state, active))
            except (SyncError, OSError, RuntimeError) as exc:
                rows.append({"file": key, "status": str(exc)})
        # Explain ignored installed entries without traversing their contents.
        for root in self.roots:
            if root.is_dir() and any(root.resolve().is_relative_to(p) for p in self.roots):
                rows.extend({"file": p.name + "/", "status": "excluded-or-inactive"}
                            for p in root.iterdir() if p.is_dir() and p.name not in active)
        return rows

    def reviewed(self, key, state, repo_hash, source_hash):
        row = self.inspect(key, state)
        if row["source"] is None:
            raise SyncError("missing-source")
        if (row["repo_hash"], row["source_hash"]) != (repo_hash, source_hash):
            raise SyncError("stale review hashes: " + key)
        return row

    def bind(self, key, source, repo_hash, source_hash):
        root = Path(os.path.abspath(Path(source).expanduser()))
        if root not in self.roots:
            raise SyncError("source root not approved")
        state = self.state()
        # Rebinding is explicit and discards any old baseline.
        trial = json.loads(json.dumps(state))
        trial["files"].pop(key, None)
        row = self.reviewed(key, trial, repo_hash, source_hash)
        target = (root / sync_name(key)[0]).resolve()
        if row["source"] != str(target) or not (root / sync_name(key)[0]).is_dir():
            raise SyncError("chosen source unavailable")
        with self.locked(state):
            self.reviewed(key, trial, repo_hash, source_hash)
            trial["files"][key] = {"root": str(root), "target": str(target), "baseline": None}
            self.save(trial)

    def accept(self, key, repo_hash, source_hash, divergence=False):
        state = self.state()
        row = self.reviewed(key, state, repo_hash, source_hash)
        if not row["bound"]:
            raise SyncError("bind this filename first")
        if repo_hash != source_hash and not divergence:
            raise SyncError("unequal hashes are not a common baseline; use --divergence")
        if repo_hash == MISSING and source_hash == MISSING:
            self.clean_repository(key)  # shared absence cannot revive a staged/worktree deletion
        with self.locked(state):
            self.reviewed(key, state, repo_hash, source_hash)
            state["files"][key].update(baseline=repo_hash if repo_hash == source_hash else None,
                                        diverged=repo_hash != source_hash)
            self.save(state)

    def approve(self, key, repo_hash, source_hash):
        """Explicit review authorizing one export to a diverged or not-yet-baselined side."""
        state = self.state()
        row = self.reviewed(key, state, repo_hash, source_hash)
        if row["status"] not in {"no-baseline", "diverged"}:
            raise SyncError("export approval applies only to reviewed divergence: " + key)
        with self.locked(state):
            self.reviewed(key, state, repo_hash, source_hash)
            state["files"][key]["export_reviewed"] = [repo_hash, source_hash]
            self.save(state)

    def clean_repository(self, key):
        name = "skills/" + key
        index, head = index_entries(self.repo), head_entries(self.repo)
        if index.get(name) != head.get(name):
            raise SyncError("staged edit/deletion: " + key)
        path = plain_path(self.repo, name)
        data = read_bytes(path)
        entry = index.get(name)
        if entry is None:
            if data is not None:
                raise SyncError("untracked target: " + key)
        elif entry[0] not in REGULAR or not committed_bytes(self.repo, data, entry[1]):
            raise SyncError("unstaged edit/deletion (raw bytes): " + key)

    def preflight(self, key, hashes, state, direction):
        row = self.reviewed(key, state, *hashes)
        if direction == "import":
            authorized = row["status"] == "import-candidate"
        else:
            approved = state["files"].get(key, {}).get("export_reviewed") == list(hashes)
            authorized = row["status"] == "repository-only" or (
                approved and row["status"] in {"no-baseline", "diverged"})
        if not row["bound"] or not authorized:
            raise SyncError("not an authorized " + direction + " candidate: " + key)
        self.clean_repository(key)
        repo = plain_path(self.repo, "skills/" + key)
        source = plain_path(Path(row["source"]), key.split("/", 1)[1])
        origin, destination = (source, repo) if direction == "import" else (repo, source)
        data, previous = read_bytes(origin), read_bytes(destination)
        if data is None:
            raise SyncError("deletion is not supported")
        # Conservative recognizable-secret guard, not a claim of complete DLP.
        if re.search(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bAKIA[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{36,}\b", data):
            raise SyncError("credential-like content: " + key)
        # New directories are deliberately not synthesized by file-level sync.
        if not destination.parent.is_dir():
            raise SyncError("destination parent must already exist: " + key)
        if sha(data) != hashes[1 if direction == "import" else 0] or sha(previous) != hashes[0 if direction == "import" else 1]:
            raise SyncError("files changed during preflight: " + key)
        return destination, data, previous

    def apply(self, reviews, direction="import"):
        if direction not in {"import", "export"} or not reviews:
            raise SyncError("select explicit filenames and import/export direction")
        state = self.state()
        index_before, head_before = index_entries(self.repo), head_entries(self.repo)
        plans = {key: self.preflight(key, hashes, state, direction) for key, hashes in reviews.items()}
        if len({path for path, _, _ in plans.values()}) != len(plans):
            raise SyncError("selected filenames share a destination")

        def recheck_git():
            if index_entries(self.repo) != index_before or head_entries(self.repo) != head_before:
                raise SyncError("Git index or HEAD changed during apply")

        report = {"written": [], "rolled_back": [], "rollback_failed": [], "backup": None}
        with self.locked(state):
            # No backups or data writes until ALL selected files have passed preflight.
            for key, hashes in reviews.items():
                self.preflight(key, hashes, state, direction)
            recheck_git()
            backup = self.state_file.parent / "backups" / uuid.uuid4().hex
            plain_path(self.common, backup.relative_to(self.common).as_posix())
            backup.mkdir(parents=True)
            report["backup"] = str(backup)
            manifest = {"direction": direction, "files": {}}
            for number, (key, (destination, data, previous)) in enumerate(plans.items()):
                blob = str(number) + ".before"
                if previous is not None:
                    (backup / blob).write_bytes(previous)
                manifest["files"][key] = {"destination": str(destination), "before": sha(previous),
                                          "after": sha(data), "blob": blob if previous is not None else None}
            (backup / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            try:
                for key, hashes in reviews.items():
                    if self.state() != state:
                        raise SyncError("baseline changed during apply")
                    recheck_git()
                    destination, data, previous = self.preflight(key, hashes, state, direction)
                    try:
                        replace_file(destination, data)
                    finally:
                        # A replacement may succeed before an I/O error is reported.
                        if sha(read_bytes(destination)) == sha(data):
                            report["written"].append(key)
                updated = json.loads(json.dumps(state))
                for key, (_, data, _) in plans.items():
                    row = self.inspect(key, state)
                    if row["repo_hash"] != sha(data) or row["source_hash"] != sha(data):
                        raise SyncError("post-write recheck failed: " + key)
                    updated["files"][key].update(baseline=sha(data), diverged=False)
                    updated["files"][key].pop("export_reviewed", None)
                if self.state() != state:
                    raise SyncError("baseline changed before completion")
                recheck_git()
                self.save(updated)
            except Exception as exc:
                # Roll back only our own unchanged output; never clobber a concurrent edit.
                for key in reversed(report["written"]):
                    destination, data, previous = plans[key]
                    try:
                        row = self.inspect(key, state)
                        current_path = (plain_path(self.repo, "skills/" + key) if direction == "import" else
                                        plain_path(Path(row["source"]), key.split("/", 1)[1]))
                        if current_path != destination or sha(read_bytes(destination)) != sha(data):
                            raise SyncError("concurrent edit; manual restore required")
                        if previous is None:
                            destination.unlink()
                        else:
                            replace_file(destination, previous)
                        report["rolled_back"].append(key)
                    except Exception:
                        report["rollback_failed"].append(key)
                raise ApplyError(str(exc), report) from exc
        return report


def materialize_index(repo, root):
    entries = index_entries(repo)
    aliases = {}
    # Preflight every path/mode before materializing anything (including case collisions).
    for name in entries:
        parts = safe_name(name)
        for count in range(1, len(parts) + 1):
            prefix = "/".join(parts[:count])
            folded = prefix.casefold()
            if folded in aliases and aliases[folded] != prefix:
                raise SyncError("ambiguous staged path: " + name)
            aliases[folded] = prefix
    # Raw object reads only: never checkout, write-tree, filters, or staged programs.
    for name, (_, oid) in entries.items():
        path = plain_path(root, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(git(repo, "cat-file", "blob", oid))
    if entries != index_entries(repo):
        raise SyncError("index changed during staged validation")
    return entries


def hook(engine, expected_active=55):
    try:
        for row in engine.check():
            if row["status"] not in {"equal", "equal-unbound"}:
                print("[sync advisory] " + json.dumps(row, ensure_ascii=True))
    except Exception as exc:
        print("[sync advisory] " + str(exc))
    try:
        with tempfile.TemporaryDirectory(prefix="skill-sync-index-") as directory:
            entries = materialize_index(engine.repo, Path(directory).resolve())
            validator = Path(__file__).resolve().with_name("validate-skills.py")
            if linklike(validator) or not validator.is_file():
                raise SyncError("trusted current validator unavailable")
            result = subprocess.run([sys.executable, "-I", "-B", str(validator), "--root", directory,
                                     "--expected-active", str(expected_active)], cwd=validator.parent,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            print(result.stdout.decode("utf-8", "replace"), end="")
            if entries != index_entries(engine.repo):
                raise SyncError("index changed during validation")
            return 1 if result.returncode else 0
    except Exception as exc:
        print("[staged validation] " + str(exc))
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "dry-run", "hook"):
        commands.add_parser(name)
    for name in ("bind", "accept", "approve"):
        sub = commands.add_parser(name)
        sub.add_argument("file")
        sub.add_argument("--repo-hash", required=True)
        sub.add_argument("--source-hash", required=True)
        if name == "bind":
            sub.add_argument("--source", type=Path, required=True)
        elif name == "accept":
            sub.add_argument("--divergence", action="store_true")
    apply = commands.add_parser("apply")
    apply.add_argument("--file", nargs=3, action="append", required=True, metavar=("FILE", "REPO_HASH", "SOURCE_HASH"))
    apply.add_argument("--direction", choices=("import", "export"), default="import")
    args = parser.parse_args(argv)
    try:
        engine = Sync(args.repo)
        if args.command in {"check", "dry-run"}:
            print(json.dumps(engine.check(), indent=2, ensure_ascii=True))
        elif args.command == "hook":
            return hook(engine)
        elif args.command == "bind":
            engine.bind(args.file, args.source, args.repo_hash, args.source_hash)
        elif args.command == "accept":
            engine.accept(args.file, args.repo_hash, args.source_hash, args.divergence)
        elif args.command == "approve":
            engine.approve(args.file, args.repo_hash, args.source_hash)
        else:
            reviews = {key: (rh, sh) for key, rh, sh in args.file}
            if len(reviews) != len(args.file):
                raise SyncError("duplicate filename selection")
            print(json.dumps(engine.apply(reviews, args.direction), indent=2))
        return 0
    except (SyncError, OSError, ValueError, RuntimeError) as exc:
        print("skill-sync: " + str(exc), file=sys.stderr)
        if isinstance(exc, ApplyError):
            print(json.dumps(exc.report, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
