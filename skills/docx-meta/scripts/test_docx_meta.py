"""Isolated regression for docx-meta cleanup, package registration and timeline closure."""
from pathlib import Path
import datetime as dt
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).with_name("docx-meta.py")

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="jpeg" ContentType="image/jpeg"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
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


def build_sample(path):
    parts = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": ROOT_RELS,
        "word/document.xml": DOCUMENT,
        "word/_rels/document.xml.rels": DOCUMENT_RELS,
        "word/people.xml": PEOPLE,
        "word/comments.xml": COMMENTS,
        "docProps/core.xml": CORE,
        "docProps/app.xml": APP,
        "docProps/custom.xml": CUSTOM,
        "docProps/thumbnail.jpeg": b"\xff\xd8\xff\xd9",
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)


def run(*args):
    env = dict(os.environ, PYTHONUTF8="1")
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )


def inspect(path):
    result = run("--inspect", str(path))
    assert result.returncode == 0, result.stderr
    text = result.stdout
    values = dict(re.findall(r"^\s+(?:core|app)\.(\w+)=(.*)$", text, re.MULTILINE))
    values["removable"] = re.search(r"^\s+removable parts: (.*)$", text, re.MULTILINE).group(1)
    values["review"] = re.search(r"^\s+review authors: (.*)$", text, re.MULTILINE).group(1)
    times = re.search(r"file times: created=(\S+) modified=(\S+) accessed=(\S+)", text)
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

            result = run("--backup", "--edit-minutes", "90",
                         "--modified", "2026-10-01T12:00:00Z", str(sample))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("dropped parts: docProps/custom.xml, word/people.xml, docProps/thumbnail.jpeg",
                          result.stdout)

            after = inspect(sample)
            self.assertEqual(after["author"], "<empty>")
            self.assertEqual(after["lastModifiedBy"], "<empty>")
            self.assertEqual(after["title"], "<empty>")
            self.assertEqual(after["description"], "<empty>")
            self.assertEqual(after["Company"], "<empty>")
            self.assertEqual(after["TotalTime"], "90")
            self.assertEqual(after["removable"], "<none>")
            self.assertEqual(after["review"], "<none>")
            self.assertEqual(after["created"], "2026-10-01T10:30:00Z")
            self.assertEqual(after["modified"], "2026-10-01T12:00:00Z")
            self.assertEqual(after["fs.created"], after["created"])
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
            result = run("--author", "保留作者", str(sample))
            self.assertEqual(result.returncode, 0, result.stderr)

            after = inspect(sample)
            minutes = int(after["TotalTime"])
            self.assertGreaterEqual(minutes, 8)
            self.assertLessEqual(minutes, 6000)
            self.assertEqual(after["author"], "保留作者")
            self.assertEqual(after["lastModifiedBy"], "保留作者")
            self.assertEqual(after["review"], "保留作者")
            created = after["created"]
            self.assertEqual(created, after["fs.created"])
            span = dt.datetime.strptime(after["modified"], "%Y-%m-%dT%H:%M:%SZ") - dt.datetime.strptime(
                created, "%Y-%m-%dT%H:%M:%SZ"
            )
            self.assertEqual(span, dt.timedelta(minutes=minutes))


if __name__ == "__main__":
    unittest.main()
