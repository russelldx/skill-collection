"""Black-box DOCX cleanup and cumulative metadata lifecycle regressions."""
from pathlib import Path
import base64
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

SCRIPT = Path(__file__).with_name("docx-meta.py")
APP_NS = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
SAMPLE_TEXT = "用于验证元数据清理的中文正文 English words"
LATER_MTIME = dt.datetime(2026, 10, 20, 12, tzinfo=dt.timezone.utc).timestamp()

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="jpeg" ContentType="image/jpeg"/>
<Default Extension="png" ContentType="image/png"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
<Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/>
<Override PartName="/word/people.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.people+xml"/>
<Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties" Target="docProps/custom.xml"/>
<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail" Target="docProps/thumbnail.jpeg"/>
</Relationships>"""

DOCUMENT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.microsoft.com/office/2011/relationships/people" Target="people.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/pixel.png"/>
</Relationships>"""

DOCUMENT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:r><w:t>用于验证元数据清理的中文正文 English words</w:t></w:r></w:p>
<w:tbl><w:tr><w:tc><w:p><w:r><w:t>项目</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
<w:sectPr/>
</w:body></w:document>"""

CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:creator>Smoke Author</dc:creator>
<cp:lastModifiedBy>Smoke Editor</cp:lastModifiedBy>
<cp:revision>7</cp:revision>
<dc:title>Secret Title</dc:title>
<dc:description>Secret Description</dc:description>
<dcterms:created xsi:type="dcterms:W3CDTF">2026-09-01T08:00:00Z</dcterms:created>
<dcterms:modified xsi:type="dcterms:W3CDTF">2026-09-02T09:00:00Z</dcterms:modified>
</cp:coreProperties>"""

APP = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
<Application>Microsoft Macintosh Word</Application>
<Company>Secret Company</Company>
<TotalTime>0</TotalTime>
</Properties>"""

CUSTOM = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" name="SecretProp"><vt:lpwstr>hidden</vt:lpwstr></property>
</Properties>"""

PEOPLE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w15:people xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml">
<w15:person w15:author="Smoke Author"/>
</w15:people>"""

COMMENTS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:comment w:id="1" w:author="Reviewer X" w:initials="RX"><w:p><w:r><w:t>note</w:t></w:r></w:p></w:comment>
</w:comments>"""


STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:default="1" w:styleId="Normal">
<w:name w:val="Normal"/><w:rPr><w:sz w:val="22"/></w:rPr>
</w:style></w:styles>"""

PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII="
)
PRESERVED_PARTS = ("word/document.xml", "word/styles.xml", "word/media/pixel.png")


def document_xml(text):
    return DOCUMENT.replace(SAMPLE_TEXT, escape(text)).encode("utf-8")


def build_sample(path, total_minutes=0, text=SAMPLE_TEXT):
    parts = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": ROOT_RELS,
        "word/document.xml": document_xml(text),
        "word/_rels/document.xml.rels": DOCUMENT_RELS,
        "word/styles.xml": STYLES,
        "word/media/pixel.png": PIXEL,
        "word/people.xml": PEOPLE,
        "word/comments.xml": COMMENTS,
        "docProps/core.xml": CORE,
        "docProps/app.xml": APP.replace("<TotalTime>0</TotalTime>",
                                       f"<TotalTime>{total_minutes}</TotalTime>"),
        "docProps/custom.xml": CUSTOM,
        "docProps/thumbnail.jpeg": b"\xff\xd8\xff\xd9",
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    # Stable, non-future mtime: no wall-clock waiting is needed in any test.
    stamp = dt.datetime(2026, 10, 1, 12, tzinfo=dt.timezone.utc).timestamp()
    os.utime(path, (stamp, stamp))


def package_parts(path):
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def rewrite_zip(path, updates=None, total_minutes=0, remove_app=False):
    """Simulate an editor save, preserving all other entries and ZIP metadata."""
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        parts = {info.filename: archive.read(info.filename) for info in infos}
        comment = archive.comment
    parts.update(updates or {})
    if remove_app:
        parts.pop("docProps/app.xml", None)
    else:
        root = ET.fromstring(parts["docProps/app.xml"])
        total = root.find(f"{{{APP_NS}}}TotalTime")
        if total_minutes is None:
            if total is not None:
                root.remove(total)
        else:
            if total is None:
                total = ET.SubElement(root, f"{{{APP_NS}}}TotalTime")
            total.text = str(total_minutes)
        parts["docProps/app.xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.comment = comment
        for info in infos:
            if info.filename in parts:
                archive.writestr(info, parts[info.filename])
    os.utime(path, (LATER_MTIME, LATER_MTIME))


def properties(path, part="docProps/app.xml"):
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read(part))
    return {child.tag.rsplit("}", 1)[-1]: child.text for child in root}


def state_dir(path):
    return Path(path).resolve().parent / ".docx-meta-state"


def run(*args):
    # The last argument is always a fixture document, including multi-path errors.
    # Do not mkdir here: inspect/dry-run must prove that they create nothing.
    env = dict(os.environ, PYTHONUTF8="1", DOCX_META_STATE_DIR=str(state_dir(args[-1])))
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
        timeout=30,
    )


def output(result):
    return (f"command: {result.args!r}\nexit: {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")


def tree_snapshot(parent):
    """Detect changed bytes/times and new state, lock, backup or temporary files."""
    snapshot = {}
    for path in sorted(parent.rglob("*")):
        name = str(path.relative_to(parent))
        if path.is_dir():
            snapshot[name] = None
        else:
            stat = path.stat()
            # Reading can update atime on some filesystems; it is not a write.
            birth = getattr(stat, "st_birthtime_ns", stat.st_ctime_ns if os.name == "nt" else None)
            snapshot[name] = (path.read_bytes(), stat.st_mtime_ns, birth)
    return snapshot


def inspect(path):
    result = run("--inspect", str(path))
    assert result.returncode == 0, output(result)
    text = result.stdout
    values = dict(re.findall(r"^\s+(?:core|app)\.(\w+)=(.*)$", text, re.MULTILINE))
    removable = re.search(r"^\s+removable parts: (.*)$", text, re.MULTILINE)
    review = re.search(r"^\s+review authors: (.*)$", text, re.MULTILINE)
    times = re.search(r"file times: created=(\S+) modified=(\S+) accessed=(\S+)", text)
    assert removable and review and times, output(result)
    values["removable"], values["review"] = removable.group(1), review.group(1)
    values["fs.created"], values["fs.modified"], values["fs.accessed"] = times.groups()
    return values


class DocxMetaTests(unittest.TestCase):
    def test_cleanup_package_registration_and_timeline(self):
        with tempfile.TemporaryDirectory(prefix="docx-meta-") as temp:
            sample = Path(temp) / "样本.docx"
            build_sample(sample)

            before = inspect(sample)
            self.assertEqual(before["author"], "Smoke Author")
            self.assertIn("docProps/custom.xml", before["removable"])
            self.assertIn("docProps/thumbnail.jpeg", before["removable"])
            self.assertIn("word/people.xml", before["removable"])
            self.assertIn("Reviewer X", before["review"])

            result = run("--clean", "--backup", "--edit-minutes", "90",
                         "--modified", "2026-10-01T12:00:00Z", str(sample))
            self.assertEqual(result.returncode, 0, output(result))
            self.assertIn("dropped parts: docProps/custom.xml, word/people.xml, docProps/thumbnail.jpeg",
                          result.stdout, output(result))

            after = inspect(sample)
            self.assertEqual(after["author"], "<empty>")
            self.assertEqual(after["lastModifiedBy"], "<empty>")
            self.assertEqual(after["title"], "<empty>")
            self.assertEqual(after["description"], "<empty>")
            self.assertEqual(after["Company"], "<empty>")
            self.assertEqual(after["TotalTime"], "90")
            self.assertEqual(after["removable"], "<none>")
            self.assertEqual(after["review"], "<none>")
            self.assertEqual(after["created"], "2026-09-01T08:00:00Z")
            self.assertEqual(after["modified"], "2026-10-01T12:00:00Z")
            self.assertEqual(after["fs.created"], before["fs.created"])
            self.assertEqual(after["fs.modified"], after["modified"])

            with zipfile.ZipFile(sample) as archive:
                names = set(archive.namelist())
                root_rels = archive.read("_rels/.rels").decode("utf-8")
                doc_rels = archive.read("word/_rels/document.xml.rels").decode("utf-8")
                content_types = archive.read("[Content_Types].xml").decode("utf-8")
                comments = archive.read("word/comments.xml").decode("utf-8")
            self.assertNotIn("docProps/custom.xml", names)
            self.assertNotIn("docProps/thumbnail.jpeg", names)
            self.assertNotIn("word/people.xml", names)
            self.assertIn("word/comments.xml", names)
            self.assertNotIn("custom-properties", root_rels)
            self.assertNotIn("/metadata/thumbnail", root_rels)
            self.assertNotIn("/people", doc_rels)
            self.assertNotIn("/docProps/custom.xml", content_types)
            self.assertNotIn("/word/people.xml", content_types)
            self.assertIn('w:author=""', comments)
            self.assertIn('w:initials=""', comments)

            backup = Path(str(sample) + ".bak")
            self.assertTrue(backup.exists())
            with zipfile.ZipFile(backup) as archive:
                self.assertIn(b"Smoke Author", archive.read("docProps/core.xml"))
                self.assertIn("docProps/custom.xml", archive.namelist())

    def test_estimated_minutes_and_explicit_author(self):
        with tempfile.TemporaryDirectory(prefix="docx-meta-estimate-") as temp:
            sample = Path(temp) / "estimate.docx"
            build_sample(sample)
            before = inspect(sample)
            result = run("--clean", "--author", "保留作者", str(sample))
            self.assertEqual(result.returncode, 0, output(result))

            after = inspect(sample)
            minutes = int(after["TotalTime"])
            self.assertGreaterEqual(minutes, 8)
            self.assertLessEqual(minutes, 6000)
            self.assertNotEqual(minutes % 5, 0)
            self.assertEqual(after["author"], "保留作者")
            self.assertEqual(after["lastModifiedBy"], "保留作者")
            self.assertEqual(after["review"], "保留作者")
            self.assertEqual(after["created"], "2026-09-01T08:00:00Z")
            self.assertEqual(after["fs.created"], before["fs.created"])
            span = dt.datetime.strptime(after["modified"], "%Y-%m-%dT%H:%M:%SZ") - dt.datetime.strptime(
                after["created"], "%Y-%m-%dT%H:%M:%SZ"
            )
            self.assertGreaterEqual(span, dt.timedelta(minutes=minutes))

    def test_clean_caps_total_without_moving_creation_time(self):
        with tempfile.TemporaryDirectory(prefix="docx-meta-capped-") as temp:
            sample = Path(temp) / "capped.docx"
            build_sample(sample)
            result = run("--clean", "--created", "2026-10-01T11:50:00Z",
                         "--modified", "2026-10-01T12:00:00Z",
                         "--edit-minutes", "90", str(sample))
            self.assertEqual(result.returncode, 0, output(result))
            after = inspect(sample)
            self.assertEqual(after["created"], "2026-10-01T11:50:00Z")
            self.assertEqual(after["modified"], "2026-10-01T12:00:00Z")
            self.assertEqual(after["TotalTime"], "10")
            self.assertIn("capped to 10min", result.stdout)

    def test_copy_style_keeps_core_creation_time(self):
        with tempfile.TemporaryDirectory(prefix="docx-meta-copy-style-core-") as temp:
            sample = Path(temp) / "copy-style-core.docx"
            build_sample(sample)
            before = inspect(sample)
            result = run("--clean", "--copy-style", "--edit-minutes", "90", str(sample))
            self.assertEqual(result.returncode, 0, output(result))
            after = inspect(sample)
            self.assertEqual(after["created"], before["created"])
            self.assertEqual(after["TotalTime"], "90")
            if os.name == "nt":
                self.assertNotEqual(after["fs.created"], after["created"])

    def test_default_preserve_keeps_identity_and_package_parts(self):
        with tempfile.TemporaryDirectory(prefix="docx-meta-preserve-") as temp:
            sample = Path(temp) / "preserve.docx"
            build_sample(sample)
            before_app = properties(sample)

            result = run("--edit-minutes", "90", str(sample))
            self.assertEqual(result.returncode, 0, output(result))

            after = inspect(sample)
            self.assertEqual(after["author"], "Smoke Author")
            self.assertEqual(after["lastModifiedBy"], "Smoke Editor")
            self.assertEqual(after["revision"], "7")
            self.assertEqual(after["title"], "Secret Title")
            self.assertEqual(after["description"], "Secret Description")
            self.assertEqual(after["Company"], "Secret Company")
            self.assertEqual(after["TotalTime"], "90")
            self.assertEqual(after["created"], "2026-09-01T08:00:00Z")
            # The fixture mtime is newer than core.modified, so the saved time follows it.
            self.assertEqual(after["modified"], "2026-10-01T12:00:00Z")
            self.assertEqual(sample.stat().st_mtime,
                             dt.datetime(2026, 10, 1, 12, tzinfo=dt.timezone.utc).timestamp())

            with zipfile.ZipFile(sample) as archive:
                names = set(archive.namelist())
                comments = archive.read("word/comments.xml").decode("utf-8")
            self.assertIn("docProps/custom.xml", names)
            self.assertIn("docProps/thumbnail.jpeg", names)
            self.assertIn("word/people.xml", names)
            self.assertIn('w:author="Reviewer X"', comments)
            self.assertIn('w:initials="RX"', comments)

            after_app = properties(sample)
            for key in ("Application", "Company", "Pages", "Words", "Characters",
                        "Lines", "Paragraphs", "CharactersWithSpaces"):
                self.assertEqual(after_app.get(key), before_app.get(key), key)
            self.assertEqual(after_app["TotalTime"], "90")

    def test_preserve_explicit_values_override_only_named_fields(self):
        with tempfile.TemporaryDirectory(prefix="docx-meta-preserve-override-") as temp:
            sample = Path(temp) / "override.docx"
            build_sample(sample)

            result = run("--author", "新作者", "--title", "新标题", "--company", "新公司",
                         "--revision", "12", "--created", "2026-09-03T08:00:00Z",
                         "--modified", "2026-09-04T09:00:00Z", "--pages", "3",
                         "--edit-minutes", "90", str(sample))
            self.assertEqual(result.returncode, 0, output(result))

            after = inspect(sample)
            self.assertEqual(after["author"], "新作者")
            self.assertEqual(after["lastModifiedBy"], "新作者")
            self.assertEqual(after["title"], "新标题")
            self.assertEqual(after["description"], "Secret Description")
            self.assertEqual(after["Company"], "新公司")
            self.assertEqual(after["revision"], "12")
            self.assertEqual(after["created"], "2026-09-03T08:00:00Z")
            self.assertEqual(after["modified"], "2026-09-04T09:00:00Z")
            self.assertEqual(after["Pages"], "3")
            self.assertEqual(after["TotalTime"], "90")

            with zipfile.ZipFile(sample) as archive:
                names = set(archive.namelist())
                comments = archive.read("word/comments.xml").decode("utf-8")
            self.assertIn("docProps/custom.xml", names)
            self.assertIn("word/people.xml", names)
            self.assertIn('w:author="Reviewer X"', comments)
            self.assertEqual(properties(sample)["Application"], "Microsoft Macintosh Word")

    def test_copy_style_requires_clean_mode(self):
        with tempfile.TemporaryDirectory(prefix="docx-meta-copy-style-") as temp:
            sample = Path(temp) / "copy-style.docx"
            build_sample(sample)
            before = tree_snapshot(sample.parent)
            result = run("--copy-style", str(sample))
            self.assertNotEqual(result.returncode, 0, output(result))
            self.assertEqual(tree_snapshot(sample.parent), before, output(result))


class DocxMetaLifecycleTests(unittest.TestCase):
    def fixture(self, total_minutes=0, text=SAMPLE_TEXT):
        temp = tempfile.TemporaryDirectory(prefix="docx-meta-lifecycle-")
        self.addCleanup(temp.cleanup)
        sample = Path(temp.name) / "样本.docx"
        build_sample(sample, total_minutes=total_minutes, text=text)
        return sample, sample.parent / "baseline.json"

    def succeed(self, *args):
        result = run(*args)
        self.assertEqual(result.returncode, 0, output(result))
        return result

    def assert_total(self, sample, expected, result):
        self.assertEqual(properties(sample).get("TotalTime"), str(expected), output(result))

    def assert_state(self, state, result):
        self.assertTrue(state.is_file(), f"Missing external JSON baseline: {state}\n{output(result)}")
        try:
            data = json.loads(state.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as exc:
            self.fail(f"Invalid JSON baseline: {exc}\n{output(result)}")
        self.assertIsInstance(data, dict, output(result))
        self.assertTrue(data, output(result))
        self.assertFalse(Path(str(state) + ".lock").exists(), output(result))
        # Field names are deliberately opaque; later CLI runs verify the baseline.

    def baseline(self, sample, state, minutes=90, *options):
        result = self.succeed("--state-file", state, "--edit-minutes", minutes, *options, sample)
        self.assert_total(sample, minutes, result)
        self.assert_state(state, result)
        return result

    def reject_without_writes(self, *args):
        parent = Path(args[-1]).parent
        before = tree_snapshot(parent)
        result = run(*args)
        self.assertEqual(tree_snapshot(parent), before, output(result))
        self.assertNotEqual(result.returncode, 0, output(result))
        # An old parser rejecting a new flag is not successful domain validation.
        self.assertNotRegex(result.stdout + result.stderr,
                            r"(?i)unrecognized arguments|unknown (?:argument|option)", output(result))
        return result

    def live_lock(self, state):
        lock = Path(str(state) + ".lock")
        # Fresh sentinel owned by a live process; keep the real handle open.
        handle = lock.open("xb")
        self.addCleanup(handle.close)
        handle.write(json.dumps({"pid": os.getpid(), "created_at": dt.datetime.now(
            dt.timezone.utc).timestamp()}).encode("utf-8"))
        handle.flush()
        return lock

    def test_auto_initializes_default_cache_and_preserves_payloads(self):
        for native, text in ((90, SAMPLE_TEXT), (0, "文" * 4500 + " word" * 3200)):
            with self.subTest(native_total=native):
                sample, _ = self.fixture(total_minutes=native, text=text)
                before = package_parts(sample)
                result = self.succeed(sample)  # No --mode means auto.
                if native:
                    self.assert_total(sample, 90, result)
                else:
                    # Full-text estimation, not merely a one-minute new session.
                    self.assertGreater(int(properties(sample)["TotalTime"]), 90, output(result))
                    self.assertLessEqual(int(properties(sample)["TotalTime"]), 6000, output(result))
                after = package_parts(sample)
                for part in PRESERVED_PARTS:
                    self.assertEqual(after[part], before[part], f"{part}\n{output(result)}")
                states = list(state_dir(sample).rglob("*.json"))
                self.assertEqual(len(states), 1, f"Expected one cached JSON baseline\n{output(result)}")
                self.assert_state(states[0], result)
                total = int(properties(sample)["TotalTime"])
                rewrite_zip(sample)  # WPS resets the app total, but not external state.
                result = self.succeed(sample)
                self.assert_total(sample, total, result)

    def test_auto_uses_baseline_when_editor_resets_or_removes_total(self):
        cases = (("zero", {"total_minutes": 0}),
                 ("missing-total", {"total_minutes": None}),
                 ("missing-app", {"remove_app": True}))
        for name, changes in cases:
            with self.subTest(editor_save=name):
                sample, state = self.fixture()
                self.baseline(sample, state)
                rewrite_zip(sample, **changes)
                payloads = package_parts(sample)
                result = self.succeed("--mode", "auto", "--state-file", state, sample)
                self.assert_total(sample, 90, result)
                for part in PRESERVED_PARTS:
                    self.assertEqual(package_parts(sample)[part], payloads[part], output(result))
                self.assert_total(sample, 90, self.succeed("--state-file", state, sample))

    def test_initial_intentionally_reestimates_and_rebaselines(self):
        sample, state = self.fixture()
        self.baseline(sample, state)
        result = self.succeed("--mode", "initial", "--state-file", state, sample)
        total = int(properties(sample)["TotalTime"])
        self.assertGreaterEqual(total, 8, output(result))
        self.assertLess(total, 90, output(result))  # Discard the deliberate 90-minute baseline.
        self.assert_state(state, result)
        rewrite_zip(sample)
        result = self.succeed("--state-file", state, sample)
        self.assert_total(sample, total, result)
        result = self.succeed("--mode", "update", "--state-file", state, sample)
        self.assert_total(sample, total, result)

    def test_update_and_add_require_baseline_without_mutation(self):
        for operation in (("--mode", "update"), ("--add-minutes", "15")):
            for explicit in (False, True):
                with self.subTest(operation=operation, explicit_state=explicit):
                    sample, state = self.fixture(total_minutes=90)
                    options = ("--state-file", state) if explicit else ()
                    # A positive native total alone is not an external baseline.
                    self.reject_without_writes(*operation, *options, sample)

    def test_update_estimates_inserted_cjk_latin_and_punctuation_tokens(self):
        for added in ("新增正文", " additional words", "！？"):
            with self.subTest(added=added):
                sample, state = self.fixture()
                self.baseline(sample, state)
                rewrite_zip(sample, {"word/document.xml": document_xml(SAMPLE_TEXT + added)})
                result = self.succeed("--mode", "update", "--state-file", state, sample)
                total = int(properties(sample)["TotalTime"])
                self.assertGreaterEqual(total, 91, output(result))
                result = self.succeed("--mode", "update", "--state-file", state, sample)
                self.assert_total(sample, total, result)

    def test_edit_minutes_is_absolute_override_and_rebaseline_including_zero(self):
        sample, state = self.fixture()
        self.baseline(sample, state)
        for absolute in (15, 0):
            with self.subTest(absolute=absolute):
                rewrite_zip(sample, {"word/document.xml": document_xml(SAMPLE_TEXT + "修改")})
                result = self.succeed("--edit-minutes", absolute, "--state-file", state, sample)
                self.assert_total(sample, absolute, result)  # Not 90 + absolute or an estimate.
                self.assert_state(state, result)
                rewrite_zip(sample)
                result = self.succeed("--state-file", state, sample)
                self.assert_total(sample, absolute, result)

    def test_manual_sessions_and_native_total_are_not_double_counted(self):
        sample, state = self.fixture()
        self.baseline(sample, state)
        # Manual minutes cover this edit instead of adding an automatic estimate too.
        rewrite_zip(sample, {"word/document.xml": document_xml(SAMPLE_TEXT + "人工修改")})
        result = self.succeed("--add-minutes", "15", "--state-file", state, sample)
        self.assert_total(sample, 105, result)
        rewrite_zip(sample)
        self.assert_total(sample, 105, self.succeed("--state-file", state, sample))
        # Word supplies a higher total for another text edit: adopt 110, not 215 or 111.
        rewrite_zip(sample, {"word/document.xml": document_xml(SAMPLE_TEXT + "原生修改")},
                    total_minutes=110)
        self.assert_total(sample, 110, self.succeed("--state-file", state, sample))
        self.assert_total(sample, 110, self.succeed("--state-file", state, sample))
        rewrite_zip(sample)
        self.assert_total(sample, 110, self.succeed("--state-file", state, sample))
        # Identical explicit additions are distinct new sessions, not idempotent retries.
        for expected in (115, 120):
            result = self.succeed("--add-minutes", "5", "--state-file", state, sample)
            self.assert_total(sample, expected, result)
        rewrite_zip(sample)
        self.assert_total(sample, 120, self.succeed("--state-file", state, sample))

    def test_invalid_additions_and_pages_leave_doc_and_state_untouched(self):
        sample, state = self.fixture()
        self.baseline(sample, state)
        cases = (("--add-minutes", "-1"),
                 ("--add-minutes", "15", "--edit-minutes", "90"),
                 ("--pages", "0"), ("--pages", "-1"), ("--pages", "1.5"))
        for options in cases:
            with self.subTest(options=options):
                self.reject_without_writes(*options, "--state-file", state, sample)

    def test_equal_length_replacements_add_changed_token_time(self):
        cases = ((SAMPLE_TEXT, SAMPLE_TEXT.replace("中文", "汉字")),
                 (SAMPLE_TEXT, SAMPLE_TEXT.replace("English", "Revised")),
                 (SAMPLE_TEXT + "！", SAMPLE_TEXT + "？"))
        for original, changed in cases:
            with self.subTest(changed=changed):
                self.assertEqual(len(original), len(changed))
                sample, state = self.fixture(text=original)
                self.baseline(sample, state)
                rewrite_zip(sample, {"word/document.xml": document_xml(changed)})
                result = self.succeed("--state-file", state, sample)
                total = int(properties(sample)["TotalTime"])
                self.assertGreater(total, 90, output(result))  # Delta, not the short full-text estimate.
                rewrite_zip(sample)
                self.assert_total(sample, total, self.succeed("--state-file", state, sample))

    def test_deletions_add_changed_token_time(self):
        cases = ((SAMPLE_TEXT, SAMPLE_TEXT.replace("中文", "")),
                 (SAMPLE_TEXT, SAMPLE_TEXT.replace("English ", "")),
                 (SAMPLE_TEXT + "！", SAMPLE_TEXT))
        for original, changed in cases:
            with self.subTest(changed=changed):
                self.assertLess(len(changed), len(original))
                sample, state = self.fixture(text=original)
                self.baseline(sample, state)
                rewrite_zip(sample, {"word/document.xml": document_xml(changed)})
                result = self.succeed("--state-file", state, sample)
                total = int(properties(sample)["TotalTime"])
                self.assertGreater(total, 90, output(result))  # Deletion is work, not negative growth.
                self.assert_total(sample, total, self.succeed("--state-file", state, sample))

    def test_unchanged_content_with_later_mtime_adds_no_idle_time(self):
        sample, state = self.fixture()
        self.baseline(sample, state)
        before = package_parts(sample)
        old_mtime = sample.stat().st_mtime
        self.assertGreater(LATER_MTIME, old_mtime)
        os.utime(sample, (LATER_MTIME, LATER_MTIME))
        result = self.succeed("--state-file", state, sample)
        self.assert_total(sample, 90, result)
        self.assertEqual(properties(sample, "docProps/core.xml")["created"],
                         ET.fromstring(before["docProps/core.xml"]).find(
                             "{http://purl.org/dc/terms/}created").text, output(result))
        for part in PRESERVED_PARTS:
            self.assertEqual(package_parts(sample)[part], before[part], output(result))
        self.assert_total(sample, 90, self.succeed("--state-file", state, sample))

    def test_formatting_only_warns_preserves_total_and_accepts_manual_time(self):
        for part in ("word/document.xml", "word/styles.xml"):
            with self.subTest(part=part):
                sample, state = self.fixture()
                self.baseline(sample, state)
                data = package_parts(sample)[part]
                if part == "word/document.xml":
                    changed = data.replace(b"<w:r>", b"<w:r><w:rPr><w:b/></w:rPr>", 1)
                else:
                    changed = data.replace(b'w:val="22"', b'w:val="28"')
                self.assertNotEqual(changed, data)
                rewrite_zip(sample, {part: changed})
                result = self.succeed("--state-file", state, sample)
                self.assert_total(sample, 90, result)
                message = result.stdout + result.stderr
                self.assertIn("--add-minutes", message, output(result))
                self.assertRegex(message, r"(?i)warn|unknown|format|警告|格式|未知", output(result))
                self.assertEqual(package_parts(sample)[part], changed, output(result))
                result = self.succeed("--add-minutes", "15", "--state-file", state, sample)
                self.assert_total(sample, 105, result)
                rewrite_zip(sample)
                self.assert_total(sample, 105, self.succeed("--state-file", state, sample))

    def test_subsequent_text_edit_preserves_existing_creation_time(self):
        sample, state = self.fixture()
        created = "2026-09-01T08:00:00Z"
        self.baseline(sample, state, 90, "--created", created,
                      "--modified", "2026-10-01T12:00:00Z")
        self.assertEqual(properties(sample, "docProps/core.xml")["created"], created)
        rewrite_zip(sample, {"word/document.xml": document_xml(SAMPLE_TEXT + "后续编辑")})
        result = self.succeed("--state-file", state, sample)
        self.assertGreater(int(properties(sample)["TotalTime"]), 90, output(result))
        after = inspect(sample)
        self.assertEqual(after["created"], created, output(result))
        self.assertEqual(after["modified"], "2026-10-20T12:00:00Z", output(result))
        if os.name == "nt":
            self.assertEqual(after["fs.created"], created, output(result))
        self.assertEqual(after["fs.modified"], after["modified"], output(result))

    def test_explicit_state_reuses_baseline_after_document_rename(self):
        sample, state = self.fixture()
        self.baseline(sample, state)
        renamed = sample.with_name("重命名.docx")
        sample.rename(renamed)
        rewrite_zip(renamed)
        result = self.succeed("--mode", "update", "--state-file", state, renamed)
        self.assert_total(renamed, 90, result)
        result = self.succeed("--add-minutes", "15", "--state-file", state, renamed)
        self.assert_total(renamed, 105, result)
        rewrite_zip(renamed)
        self.assert_total(renamed, 105, self.succeed("--state-file", state, renamed))
        self.assert_state(state, result)

    def test_explicit_state_rejects_multiple_documents_without_mutation(self):
        sample, state = self.fixture()
        second = sample.with_name("second.docx")
        build_sample(second)
        self.reject_without_writes("--state-file", state, sample, second)

    def test_pages_positive_integer_overrides_estimate(self):
        sample, state = self.fixture()
        self.baseline(sample, state)
        for pages in (7, 2):
            with self.subTest(pages=pages):
                result = self.succeed("--pages", pages, "--state-file", state, sample)
                self.assertEqual(properties(sample)["Pages"], str(pages), output(result))
                self.assert_total(sample, 90, result)

    def test_read_only_modes_do_not_write_doc_state_or_lock(self):
        for mode in ("--dry-run", "--inspect"):
            for scenario in ("fresh-default", "fresh-explicit", "existing", "locked"):
                with self.subTest(mode=mode, scenario=scenario):
                    sample, state = self.fixture()
                    options = () if scenario == "fresh-default" else ("--state-file", state)
                    if scenario in ("existing", "locked"):
                        self.baseline(sample, state)
                        rewrite_zip(sample, {"word/document.xml": document_xml(SAMPLE_TEXT + "待处理")})
                    if scenario == "locked":
                        self.live_lock(state)
                    before = tree_snapshot(sample.parent)
                    result = self.succeed(mode, *options, sample)
                    self.assertEqual(tree_snapshot(sample.parent), before, output(result))

    def test_corrupt_state_fails_closed_without_touching_doc(self):
        for mode in ("auto", "update"):
            with self.subTest(mode=mode):
                sample, state = self.fixture(total_minutes=90)
                state.write_bytes(b'{"truncated":')
                self.reject_without_writes("--mode", mode, "--state-file", state, sample)

    def test_state_file_cannot_be_the_document(self):
        sample, _ = self.fixture()
        self.reject_without_writes("--state-file", sample, sample)

    def test_live_state_lock_fails_without_deleting_lock(self):
        sample, state = self.fixture()
        self.baseline(sample, state)
        lock = self.live_lock(state)
        before = lock.read_bytes()
        self.reject_without_writes("--state-file", state, sample)
        self.assertTrue(lock.is_file())
        self.assertEqual(lock.read_bytes(), before)

    def test_repeated_text_prepend_costs_only_the_added_token(self):
        sample, state = self.fixture()
        template = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                    '<w:body><w:p><w:r><w:t>{}</w:t></w:r></w:p></w:body></w:document>')
        rewrite_zip(sample, {"word/document.xml": template.format("文" * 4500).encode("utf-8")})
        self.baseline(sample, state)
        rewrite_zip(sample, {"word/document.xml": template.format("新" + "文" * 4500).encode("utf-8")})
        result = self.succeed("--state-file", state, sample)
        self.assert_total(sample, 91, result)

    def test_heading_style_only_does_not_invent_editing_time(self):
        sample, state = self.fixture()
        self.baseline(sample, state)
        changed = package_parts(sample)["word/document.xml"].replace(
            b"<w:p>", b'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>', 1)
        rewrite_zip(sample, {"word/document.xml": changed})
        result = self.succeed("--state-file", state, sample)
        self.assert_total(sample, 90, result)
        self.assertIn("--add-minutes", result.stdout, output(result))

    def replace_failure(self, destination, *args):
        code = """
import os, runpy, sys
script, destination = sys.argv[1:3]
sys.argv = [script, *sys.argv[3:]]
replace = os.replace
def fail_selected_replace(source, target):
    if os.path.normcase(os.path.abspath(target)) == os.path.normcase(os.path.abspath(destination)):
        raise PermissionError('injected replacement failure')
    return replace(source, target)
os.replace = fail_selected_replace
runpy.run_path(script, run_name='__main__')
"""
        env = dict(os.environ, PYTHONUTF8="1", DOCX_META_STATE_DIR=str(state_dir(args[-1])))
        return subprocess.run([sys.executable, "-B", "-c", code, str(SCRIPT), str(destination),
                               *map(str, args)], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=env, timeout=30)

    def test_failed_baseline_save_keeps_modified_anchor_for_recovery(self):
        sample, state = self.fixture()
        self.baseline(sample, state)
        rewrite_zip(sample)
        previous_state = state.read_bytes()
        result = self.replace_failure(state, "--state-file", state, "--add-minutes", "15", sample)
        self.assertNotEqual(result.returncode, 0, output(result))
        self.assert_total(sample, 105, result)
        self.assertEqual(state.read_bytes(), previous_state)
        self.assertEqual(sample.stat().st_mtime, LATER_MTIME, output(result))
        result = self.succeed("--state-file", state, "--edit-minutes", "105", sample)
        self.assert_total(sample, 105, result)
        self.assertEqual(properties(sample, "docProps/core.xml")["modified"],
                         "2026-10-20T12:00:00Z", output(result))
        self.assert_state(state, result)

    def test_failed_docx_replace_does_not_advance_baseline(self):
        sample, state = self.fixture()
        self.baseline(sample, state)
        rewrite_zip(sample)
        before = tree_snapshot(sample.parent)
        result = self.replace_failure(sample, "--state-file", state, "--add-minutes", "15", sample)
        self.assertNotEqual(result.returncode, 0, output(result))
        self.assertEqual(tree_snapshot(sample.parent), before, output(result))


if __name__ == "__main__":
    unittest.main()
