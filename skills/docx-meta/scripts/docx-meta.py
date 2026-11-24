#!/usr/bin/env python3
"""Preserve or clean docx metadata, maintain total editing time, and align timelines."""

import argparse
from collections import Counter
from contextlib import contextmanager
import datetime as dt
import difflib
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile
from xml.etree import ElementTree as ET

CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC = "http://purl.org/dc/elements/1.1/"
DCTERMS = "http://purl.org/dc/terms/"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
APP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
VT = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"

CT_CORE = "application/vnd.openxmlformats-package.core-properties+xml"
CT_APP = "application/vnd.openxmlformats-officedocument.extended-properties+xml"
REL_CORE = "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"
REL_APP = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties"

for _p, _u in (("cp", CP), ("dc", DC), ("dcterms", DCTERMS), ("xsi", XSI)):
    ET.register_namespace(_p, _u)
ET.register_namespace("", APP)
ET.register_namespace("vt", VT)

APP_TEMPLATE = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="{APP}" xmlns:vt="{VT}">
<Template>Normal.dotm</Template>
<TotalTime>0</TotalTime>
<Pages>1</Pages>
<Words>0</Words>
<Characters>0</Characters>
<Application>Microsoft Office Word</Application>
<DocSecurity>0</DocSecurity>
<Lines>1</Lines>
<Paragraphs>1</Paragraphs>
<ScaleCrop>false</ScaleCrop>
<Company></Company>
<LinksUpToDate>false</LinksUpToDate>
<CharactersWithSpaces>0</CharactersWithSpaces>
<SharedDoc>false</SharedDoc>
<HyperlinksChanged>false</HyperlinksChanged>
<AppVersion>16.0000</AppVersion>
</Properties>"""

CORE_PRIVATE = [
    (DC, "title"),
    (DC, "subject"),
    (DC, "description"),
    (CP, "keywords"),
    (CP, "category"),
    (CP, "contentStatus"),
    (CP, "identifier"),
    (CP, "language"),
    (CP, "version"),
    (CP, "lastPrinted"),
]

DROP_SPECS = [
    ("docProps/custom.xml", ["_rels/.rels"], "/custom-properties", "/docProps/custom.xml"),
    ("word/people.xml", ["word/_rels/document.xml.rels"], "/people", "/word/people.xml"),
]


def _out(text):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    print(text)


def parse_dt(value):
    if not value:
        return None
    s = value.strip()
    if s.endswith("Z"):
        return dt.datetime.fromisoformat(s[:-1]).replace(tzinfo=dt.timezone.utc)
    d = dt.datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.astimezone()
    return d.astimezone(dt.timezone.utc)


def file_times(path):
    st = os.stat(path)
    modified = dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc)
    birth = getattr(st, "st_birthtime", None)
    if birth is None:
        birth = st.st_ctime if os.name == "nt" else st.st_mtime
    created = dt.datetime.fromtimestamp(birth, dt.timezone.utc)
    return created, modified


def text_stats(document_xml):
    source = document_xml.decode("utf-8", "ignore") if document_xml else ""
    text = html.unescape("".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", source, re.S)))
    cjk = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text))
    latin = len(re.findall(r"[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)*", text))
    chars_with_spaces = len(text)
    chars = len(re.sub(r"\s", "", text))
    paragraphs = max(1, len(re.findall(r"<w:p(?:\s[^>]*)?/?>", source)))
    lines = max(paragraphs, math.ceil(chars_with_spaces / 38)) if chars_with_spaces else paragraphs
    pages = max(1, math.ceil(lines / 32))
    return {
        "text": text,
        "cjk": cjk,
        "latin": latin,
        "words": cjk + latin,
        "chars": chars,
        "chars_with_spaces": chars_with_spaces,
        "paragraphs": paragraphs,
        "lines": lines,
        "pages": pages,
        "tables": len(re.findall(r"<w:tbl(?:\s[^>]*)?/?>", source)),
        "images": len(re.findall(r"<w:(?:drawing|pict)(?:\s[^>]*)?>", source)),
        "headings": len(re.findall(r'<w:pStyle\s+w:val="Heading\d?"', source)),
    }


def non_round_minutes(value):
    value = max(1, min(6000, int(value)))
    if value % 5 == 0:
        value += 1 if value < 6000 else -1
    return value


def estimate_minutes(stats, chars_per_min, words_per_min):
    base = stats["cjk"] / chars_per_min + stats["latin"] / words_per_min
    overhead = (
        max(0, stats["paragraphs"] - 1) * 0.4
        + stats["tables"] * 4
        + stats["images"] * 2
        + stats["headings"] * 1.5
    )
    digest = hashlib.sha256(stats["text"].encode("utf-8")).digest()
    jitter = 0.92 + (int.from_bytes(digest[:2], "big") % 21) / 100
    return non_round_minutes(max(8, min(6000, round((base + overhead) * jitter))))


TOKEN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]|[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)*|[^\s]")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def content_snapshot(entries, stats):
    tokens, media = [], []
    digest = hashlib.sha256()
    for name, original in sorted(entries.items()):
        if not name.startswith("word/") or name == "word/people.xml" or name.endswith("/"):
            continue
        data = original
        if name.endswith(".xml"):
            data = AUTHOR_RE.sub(lambda m: m.group(1) + b'=""', data)
            chunks = []
            for el in ET.fromstring(data).iter():
                if el.tag in (f"{{{W}}}p", f"{{{W}}}tab", f"{{{W}}}br"):
                    chunks.append("\n")
                elif el.tag == f"{{{W}}}t":
                    chunks.append(el.text or "")
            for token in TOKEN_RE.findall("".join(chunks)):
                kind = "word" if re.match(r"[A-Za-z0-9]", token) else "char"
                tokens.append([hashlib.sha256(token.encode("utf-8")).hexdigest(), kind])
        elif name == "word/_rels/document.xml.rels":
            data = strip_rel(data, "/people")
        if name.startswith("word/media/"):
            media.append(hashlib.sha256(data).hexdigest())
        digest.update(name.encode("utf-8") + b"\0" + hashlib.sha256(data).digest())
    return {
        "tokens": tokens, "media": media, "content_hash": digest.hexdigest(),
        "paragraphs": stats["paragraphs"], "tables": stats["tables"], "headings": stats["headings"],
    }


def estimate_delta(previous, current, chars_per_min, words_per_min):
    old, new = previous["tokens"], current["tokens"]
    start, old_end, new_end = 0, len(old), len(new)
    while start < min(old_end, new_end) and old[start] == new[start]:
        start += 1
    while old_end > start and new_end > start and old[old_end - 1] == new[new_end - 1]:
        old_end -= 1
        new_end -= 1
    old, new = old[start:old_end], new[start:new_end]
    rates = {"char": chars_per_min, "word": words_per_min}
    matcher = difflib.SequenceMatcher(None, [t[0] for t in old], [t[0] for t in new], autojunk=False)
    minutes = 0.0
    for operation, i, j, k, l in matcher.get_opcodes():
        if operation != "equal":
            minutes += max(sum(1 / rates[t[1]] for t in old[i:j]),
                           sum(1 / rates[t[1]] for t in new[k:l]))
    old_media, new_media = Counter(previous["media"]), Counter(current["media"])
    minutes += 2 * max(sum((old_media - new_media).values()), sum((new_media - old_media).values()))
    if not minutes:
        return 0
    for field, weight in (("paragraphs", 0.4), ("tables", 4), ("headings", 1.5)):
        minutes += abs(current[field] - previous[field]) * weight
    return min(6000, max(1, round(minutes)))


def baseline_path(path, explicit):
    document = Path(path).resolve()
    if explicit:
        state = Path(explicit).expanduser().resolve()
    else:
        default = (Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
                   if os.name == "nt" else Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")))
        root = Path(os.environ.get("DOCX_META_STATE_DIR", default / "docx-meta")).expanduser()
        key = hashlib.sha256(os.path.normcase(str(document)).encode("utf-8")).hexdigest()
        state = (root / (key + ".json")).resolve()
    if state == document or state == Path(str(document) + ".bak"):
        raise ValueError("state file must be separate from the document and its backup")
    if state.exists() and os.path.samefile(state, document):
        raise ValueError("state file aliases the document")
    if state.suffix.lower() != ".json":
        raise ValueError("--state-file must be a JSON path")
    return state


def read_baseline(path):
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        snapshot = state["snapshot"]
        valid = (state["version"] == 1 and type(state["total_minutes"]) is int
                 and state["total_minutes"] >= 0 and type(state["estimated"]) is bool
                 and isinstance(state["source"], str)
                 and bool(parse_dt(state["created"])) and bool(parse_dt(state["modified"]))
                 and isinstance(snapshot["tokens"], list) and isinstance(snapshot["media"], list)
                 and isinstance(snapshot["content_hash"], str)
                 and bool(re.fullmatch(r"[a-f0-9]{64}", snapshot["content_hash"]))
                 and all(type(snapshot[k]) is int and snapshot[k] >= 0
                         for k in ("paragraphs", "tables", "headings"))
                 and all(isinstance(t, list) and len(t) == 2 and isinstance(t[0], str)
                         and re.fullmatch(r"[a-f0-9]{64}", t[0]) and t[1] in ("char", "word")
                         for t in snapshot["tokens"])
                 and all(isinstance(h, str) and re.fullmatch(r"[a-f0-9]{64}", h)
                         for h in snapshot["media"]))
        if not valid:
            raise ValueError("invalid baseline fields")
        return state
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
        raise ValueError(f"invalid baseline {path}; preserve it before using --mode initial to reset") from exc


@contextmanager
def baseline_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = Path(str(path) + ".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(f"baseline is locked: {lock}; check the owning process, do not remove a live lock") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"pid": os.getpid()}, stream)
        yield
    finally:
        lock.unlink()


def resolve_minutes(args, entries, stats, snapshot, baseline):
    if args.edit_minutes is not None:
        return args.edit_minutes, "explicit-total", False
    if args.add_minutes is not None:
        return baseline["total_minutes"] + args.add_minutes, "baseline+manual", baseline["estimated"]
    app = entries.get("docProps/app.xml")
    value = ET.fromstring(app).findtext(f"{{{APP}}}TotalTime", "0") if app else "0"
    try:
        native_total = max(0, int(value))
    except (TypeError, ValueError):
        native_total = 0
    if baseline is None:
        if native_total and args.mode != "initial":
            return native_total, "document-total", False
        return estimate_minutes(stats, args.chars_per_min, args.words_per_min), "initial-estimate", True
    if native_total > baseline["total_minutes"]:
        return native_total, "editor-total", baseline["estimated"]
    added = estimate_delta(baseline["snapshot"], snapshot, args.chars_per_min, args.words_per_min)
    if added:
        return non_round_minutes(baseline["total_minutes"] + added), "baseline+estimated-delta", True
    if snapshot["content_hash"] != baseline["snapshot"]["content_hash"]:
        _out("  warning: formatting/review duration is unknown; use --add-minutes N if known")
    return baseline["total_minutes"], "baseline-preserved", baseline["estimated"]


def get_or_add(root, ns, tag):
    el = root.find(f"{{{ns}}}{tag}")
    if el is None:
        el = ET.SubElement(root, f"{{{ns}}}{tag}")
    return el


def remove_tag(root, ns, tag):
    el = root.find(f"{{{ns}}}{tag}")
    if el is not None:
        root.remove(el)


def read_core_datetime(data, tag):
    if not data:
        return None
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    el = root.find(f"{{{DCTERMS}}}{tag}")
    if el is None or not el.text:
        return None
    try:
        return parse_dt(el.text)
    except (ValueError, OverflowError):
        return None


def set_core_datetime(root, tag, value):
    el = get_or_add(root, DCTERMS, tag)
    el.set(f"{{{XSI}}}type", "dcterms:W3CDTF")
    el.text = value.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_core_clean(old, args, created, modified):
    root = ET.fromstring(old) if old else ET.Element(f"{{{CP}}}coreProperties")
    for ns, tag in CORE_PRIVATE:
        if tag == "title" and args.title:
            continue
        remove_tag(root, ns, tag)
    if args.title:
        get_or_add(root, DC, "title").text = args.title
    if args.author:
        get_or_add(root, DC, "creator").text = args.author
        get_or_add(root, CP, "lastModifiedBy").text = args.author
    else:
        remove_tag(root, DC, "creator")
        remove_tag(root, CP, "lastModifiedBy")
    revision = args.revision if args.revision is not None else 1
    get_or_add(root, CP, "revision").text = str(revision)
    for tag, value in (("created", created), ("modified", modified)):
        set_core_datetime(root, tag, value)
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def update_core_preserve(old, args, created, modified):
    """Edit only explicitly supplied core fields; otherwise keep the part bytes."""
    explicit = any(value is not None for value in (
        args.author, args.title, args.revision, created, modified))
    if old is None:
        if not explicit:
            return None
        root = ET.Element(f"{{{CP}}}coreProperties")
    elif not explicit:
        return old
    else:
        root = ET.fromstring(old)
    if args.author is not None:
        get_or_add(root, DC, "creator").text = args.author
        get_or_add(root, CP, "lastModifiedBy").text = args.author
    if args.title is not None:
        get_or_add(root, DC, "title").text = args.title
    if args.revision is not None:
        get_or_add(root, CP, "revision").text = str(args.revision)
    if created is not None:
        set_core_datetime(root, "created", created)
    if modified is not None:
        set_core_datetime(root, "modified", modified)
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def set_app_text(data, tag, value):
    text = data.decode("utf-8")
    pattern = re.compile(
        rf"<(?P<prefix>[A-Za-z_][\w.-]*:)?{tag}\b[^>]*(?:/>|>.*?</(?:\w+:)?{tag}>)", re.S
    )
    match = pattern.search(text)
    if match:
        prefix = match.group("prefix") or ""
        replacement = f"<{prefix}{tag}>{html.escape(value)}</{prefix}{tag}>"
        return pattern.sub(lambda _: replacement, text, count=1).encode("utf-8")
    root_match = re.search(r"<(?P<prefix>[A-Za-z_][\w.-]*:)?Properties\b", text)
    prefix = (root_match.group("prefix") or "") if root_match else ""
    closing = re.compile(rf"</{re.escape(prefix)}Properties\s*>")
    if not closing.search(text):
        raise ValueError(f"cannot update docProps/app.xml: missing {tag} and Properties root")
    replacement = f"<{prefix}{tag}>{html.escape(value)}</{prefix}{tag}>"
    return closing.sub(lambda m: replacement + m.group(0), text, count=1).encode("utf-8")


def minimal_app(edit_minutes, company=None, pages=None):
    parts = []
    if company is not None:
        parts.append(f"<Company>{html.escape(company)}</Company>")
    if pages is not None:
        parts.append(f"<Pages>{pages}</Pages>")
    parts.append(f"<TotalTime>{edit_minutes}</TotalTime>")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<Properties xmlns="{APP}">' + "".join(parts) + "</Properties>").encode("utf-8")


def build_app_clean(old, args, stats, edit_minutes):
    root = ET.fromstring(old) if old else ET.fromstring(APP_TEMPLATE)
    for tag in ("HeadingPairs", "TitlesOfParts"):
        remove_tag(root, APP, tag)
    values = {
        "Template": "Normal.dotm",
        "TotalTime": str(edit_minutes),
        "Pages": str(stats["pages"]),
        "Words": str(stats["words"]),
        "Characters": str(stats["chars"]),
        "Application": "Microsoft Office Word",
        "DocSecurity": "0",
        "Lines": str(stats["lines"]),
        "Paragraphs": str(stats["paragraphs"]),
        "ScaleCrop": "false",
        "Company": args.company or "",
        "Manager": "",
        "HyperlinkBase": "",
        "LinksUpToDate": "false",
        "CharactersWithSpaces": str(stats["chars_with_spaces"]),
        "SharedDoc": "false",
        "HyperlinksChanged": "false",
        "AppVersion": "16.0000",
    }
    for tag, value in values.items():
        get_or_add(root, APP, tag).text = value
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def update_app_preserve(old, args, edit_minutes):
    if old is None:
        return minimal_app(edit_minutes, args.company, args.pages)
    data = set_app_text(old, "TotalTime", str(edit_minutes))
    if args.company is not None:
        data = set_app_text(data, "Company", args.company)
    if args.pages is not None:
        data = set_app_text(data, "Pages", str(args.pages))
    return data


REL_RE = re.compile(rb"<Relationship\b[^>]*/>")
OVR_RE = re.compile(rb'<Override\b[^>]*PartName="([^"]+)"[^>]*/>')


def strip_rel(data, fragment):
    frag = fragment.encode()
    return REL_RE.sub(lambda m: b"" if frag in m.group(0) else m.group(0), data)


def strip_override(data, part):
    part_b = part.encode()
    return OVR_RE.sub(lambda m: b"" if m.group(1) == part_b else m.group(0), data)


def drop_part(entries, drops, name, rel_files, rel_fragment, ct_part):
    if name not in entries:
        return False
    entries.pop(name, None)
    drops.add(name)
    for rel in rel_files:
        if rel in entries:
            entries[rel] = strip_rel(entries[rel], rel_fragment)
    if ct_part and "[Content_Types].xml" in entries:
        entries["[Content_Types].xml"] = strip_override(entries["[Content_Types].xml"], ct_part)
    return True


def thumbnail_parts(entries):
    return [name for name in entries if name.startswith("docProps/thumbnail.")]


def ensure_registration(entries, part, content_type, rel_type):
    part_name = "/" + part.lstrip("/")
    if "[Content_Types].xml" in entries:
        ct = entries["[Content_Types].xml"].decode("utf-8")
        if f'PartName="{part_name}"' not in ct:
            entry = f'<Override PartName="{part_name}" ContentType="{content_type}"/>'
            entries["[Content_Types].xml"] = ct.replace("</Types>", entry + "</Types>", 1).encode("utf-8")
    if "_rels/.rels" in entries:
        rels = entries["_rels/.rels"].decode("utf-8")
        target = part.lstrip("/")
        if f'Target="{target}"' not in rels:
            used = {int(x) for x in re.findall(r'Id="rId(\d+)"', rels)}
            rid = max(used, default=0) + 1
            entry = f'<Relationship Id="rId{rid}" Type="{rel_type}" Target="{target}"/>'
            entries["_rels/.rels"] = rels.replace("</Relationships>", entry + "</Relationships>", 1).encode("utf-8")


AUTHOR_RE = re.compile(rb'(w:(?:author|initials))="[^"]*"')


def scrub_review_authors(entries, drops, author, keep):
    if keep:
        return 0
    value = html.escape(author, quote=True).encode("utf-8") if author else b""

    def repl(match):
        return match.group(1) + b'="' + value + b'"'

    count = 0
    for name in list(entries):
        if name in drops or not re.match(r"word/.*\.xml$", name):
            continue
        data, n = AUTHOR_RE.subn(repl, entries[name])
        if n:
            entries[name] = data
            count += n
    return count


def review_authors(entries, drops):
    found = set()
    for name, data in entries.items():
        if name in drops or not re.match(r"word/.*\.xml$", name):
            continue
        for value in re.findall(rb'w:author="([^"]*)"', data):
            text = value.decode("utf-8", "replace")
            if text:
                found.add(text)
    return found


def load_package(path):
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        entries = {info.filename: z.read(info.filename) for info in infos}
    return infos, entries


def zip_stamp(local_dt):
    if local_dt.year < 1980:
        local_dt = local_dt.replace(year=1980, month=1, day=1)
    return local_dt.timetuple()[:6]


def rewrite_package(path, infos, entries, drops, stamp):
    fd, tmp = tempfile.mkstemp(suffix=".docx", dir=os.path.dirname(os.path.abspath(path)))
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            known = set()
            for info in infos:
                if info.filename in drops:
                    continue
                known.add(info.filename)
                zi = zipfile.ZipInfo(info.filename, stamp)
                zi.compress_type = info.compress_type
                zi.external_attr = info.external_attr
                zi.create_system = info.create_system
                zout.writestr(zi, entries[info.filename])
            for name, data in entries.items():
                if name in known or name in drops:
                    continue
                zout.writestr(zipfile.ZipInfo(name, stamp), data)
        with zipfile.ZipFile(tmp) as check:
            if check.testzip() is not None:
                raise ValueError("zip integrity check failed")
            for name in ("[Content_Types].xml", "_rels/.rels", "docProps/core.xml", "docProps/app.xml"):
                if name in check.namelist():
                    ET.fromstring(check.read(name))
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def clamp_total_to_span(minutes, created, modified):
    span = max(0, int((modified - created).total_seconds() // 60))
    return min(minutes, span), span


def restore_file_times(path, created, accessed, modified):
    if os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]

    # FILETIME: 100ns ticks since 1601-01-01 UTC
    epoch = dt.datetime(1601, 1, 1, tzinfo=dt.timezone.utc)

    def filetime(value):
        ticks = int((value - epoch).total_seconds() * 10_000_000)
        return FILETIME(ticks & 0xFFFFFFFF, (ticks >> 32) & 0xFFFFFFFF)

    created_ft = filetime(created)
    accessed_ft = filetime(accessed)
    modified_ft = filetime(modified)

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.SetFileTime.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME), ctypes.POINTER(FILETIME),
    ]
    k32.SetFileTime.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL

    FILE_WRITE_ATTRIBUTES = 0x0100
    OPEN_EXISTING = 3
    handle = k32.CreateFileW(
        os.path.abspath(path), FILE_WRITE_ATTRIBUTES, 0, None, OPEN_EXISTING, 0, None
    )
    if not handle or handle == ctypes.c_void_p(-1).value:
        return False
    try:
        return bool(
            k32.SetFileTime(
                handle, ctypes.byref(created_ft), ctypes.byref(accessed_ft), ctypes.byref(modified_ft)
            )
        )
    finally:
        k32.CloseHandle(handle)


def inspect(path, entries, accessed, mode):
    core = entries.get("docProps/core.xml")
    app = entries.get("docProps/app.xml")
    _out(f"[docx-meta] {path} ({os.path.getsize(path)} bytes) mode={mode}")
    created, modified = file_times(path)
    _out(
        f"  file times: created={created:%Y-%m-%dT%H:%M:%SZ} "
        f"modified={modified:%Y-%m-%dT%H:%M:%SZ} accessed={accessed:%Y-%m-%dT%H:%M:%SZ}"
    )
    if core:
        root = ET.fromstring(core)
        for label, ns, tag in (
            ("author", DC, "creator"),
            ("lastModifiedBy", CP, "lastModifiedBy"),
            ("revision", CP, "revision"),
            ("created", DCTERMS, "created"),
            ("modified", DCTERMS, "modified"),
            ("title", DC, "title"),
            ("description", DC, "description"),
        ):
            el = root.find(f"{{{ns}}}{tag}")
            value = el.text if el is not None else None
            _out(f"  core.{label}={value if value else '<empty>'}")
    else:
        _out("  core.xml=<missing>")
    if app:
        root = ET.fromstring(app)
        for tag in ("Application", "AppVersion", "Company", "TotalTime", "Pages", "Words", "Characters"):
            el = root.find(f"{{{APP}}}{tag}")
            value = el.text if el is not None else None
            _out(f"  app.{tag}={value if value else '<empty>'}")
    else:
        _out("  app.xml=<missing>")
    parts = [name for name, _, _, _ in DROP_SPECS if name in entries]
    parts += thumbnail_parts(entries)
    _out(f"  removable parts: {', '.join(parts) if parts else '<none>'}")
    authors = sorted(review_authors(entries, set()))
    _out(f"  review authors: {', '.join(authors) if authors else '<none>'}")


def process(path, args):
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    state_path = baseline_path(path, args.state_file)
    baseline = None if args.mode == "initial" and not args.inspect else read_baseline(state_path)
    if not args.inspect and (args.mode == "update" or args.add_minutes is not None) and baseline is None:
        raise ValueError("baseline missing; first initialize with auto/--edit-minutes, or select the original --state-file")
    if args.inspect or args.dry_run:
        process_document(path, args, state_path, baseline)
        return
    with baseline_lock(state_path):
        baseline = None if args.mode == "initial" else read_baseline(state_path)
        if (args.mode == "update" or args.add_minutes is not None) and baseline is None:
            raise ValueError("baseline disappeared before processing")
        process_document(path, args, state_path, baseline)


def process_document(path, args, state_path, baseline):
    if args.inspect:
        st = os.stat(path)
        infos, entries = load_package(path)
        inspect(path, entries, dt.datetime.fromtimestamp(st.st_atime, dt.timezone.utc),
                "clean" if args.clean else "preserve")
        _out(f"  state.file={state_path}")
        if baseline:
            _out(f"  state.totalTime={baseline['total_minutes']}min source={baseline['source']} estimated={baseline['estimated']}")
        else:
            _out("  state.totalTime=<missing>")
        return

    st = os.stat(path)
    original_accessed = dt.datetime.fromtimestamp(st.st_atime, dt.timezone.utc)
    fs_created, fs_modified = file_times(path)
    infos, entries = load_package(path)

    stats = text_stats(entries.get("word/document.xml", b""))
    snapshot = content_snapshot(entries, stats)
    edit_minutes, source, estimated = resolve_minutes(args, entries, stats, snapshot, baseline)
    explicit_created = parse_dt(args.created)
    explicit_modified = parse_dt(args.modified)
    if args.pages is not None:
        stats["pages"] = args.pages

    requested_minutes = edit_minutes
    if args.clean:
        core = entries.get("docProps/core.xml")
        core_created = read_core_datetime(core, "created")
        baseline_created = parse_dt(baseline["created"]) if baseline else None
        created = (explicit_created or core_created or baseline_created
                   or fs_created.replace(microsecond=0))
        modified = explicit_modified or fs_modified
        edit_minutes, span = clamp_total_to_span(edit_minutes, created, modified)
        if edit_minutes < requested_minutes:
            _out(f"  warning: totalTime {requested_minutes}min exceeds timeline span {span}min; "
                 f"capped to {edit_minutes}min (created time kept)")

        entries["docProps/core.xml"] = build_core_clean(
            entries.get("docProps/core.xml"), args, created, modified)
        entries["docProps/app.xml"] = build_app_clean(
            entries.get("docProps/app.xml"), args, stats, edit_minutes)
        ensure_registration(entries, "docProps/core.xml", CT_CORE, REL_CORE)
        ensure_registration(entries, "docProps/app.xml", CT_APP, REL_APP)

        drops = set()
        removed = []
        for name, rel_files, rel_fragment, ct_part in DROP_SPECS:
            if name == "docProps/custom.xml" and args.keep_custom_properties:
                continue
            if name == "word/people.xml" and args.keep_people:
                continue
            if drop_part(entries, drops, name, rel_files, rel_fragment, ct_part):
                removed.append(name)
        if not args.keep_thumbnail:
            for name in thumbnail_parts(entries):
                if drop_part(entries, drops, name, ["_rels/.rels"], "/metadata/thumbnail", "/" + name):
                    removed.append(name)

        scrubbed = scrub_review_authors(entries, drops, args.author, args.keep_review_authors)
        fs_created_target = explicit_created or fs_created
        fs_accessed_target = original_accessed
        fs_modified_target = modified
    else:
        core = entries.get("docProps/core.xml")
        core_created = read_core_datetime(core, "created")
        core_modified = read_core_datetime(core, "modified")
        fs_modified_seconds = fs_modified.replace(microsecond=0)
        created = explicit_created or core_created or fs_created.replace(microsecond=0)
        modified_update = explicit_modified
        if explicit_modified is not None:
            modified = explicit_modified
        elif core_modified is not None and fs_modified_seconds > core_modified:
            modified = fs_modified_seconds
            modified_update = fs_modified_seconds
        elif core_modified is not None:
            modified = core_modified
        else:
            modified = fs_modified_seconds

        edit_minutes, span = clamp_total_to_span(edit_minutes, created, modified)
        if edit_minutes < requested_minutes:
            _out(f"  warning: totalTime {requested_minutes}min exceeds timeline span {span}min; "
                 f"capped to {edit_minutes}min (created time kept)")

        core = update_core_preserve(core, args, explicit_created, modified_update)
        if core is not None:
            entries["docProps/core.xml"] = core
            ensure_registration(entries, "docProps/core.xml", CT_CORE, REL_CORE)
        entries["docProps/app.xml"] = update_app_preserve(
            entries.get("docProps/app.xml"), args, edit_minutes)
        ensure_registration(entries, "docProps/app.xml", CT_APP, REL_APP)
        drops, removed, scrubbed = set(), [], 0
        fs_created_target = explicit_created or fs_created
        fs_modified_target = explicit_modified or fs_modified
        fs_accessed_target = explicit_modified or original_accessed

    _out(f"[docx-meta] {path}")
    _out(f"  mode={'clean' if args.clean else 'preserve'}")
    _out(f"  created={created:%Y-%m-%dT%H:%M:%SZ} modified={modified:%Y-%m-%dT%H:%M:%SZ}")
    if args.clean:
        if args.copy_style:
            _out(f"  timeline: copy-style, core timestamps kept, span={span}min "
                 f"(fs creation follows rewrite time)")
        else:
            _out(f"  timeline: core timestamps kept, span={span}min totalTime={edit_minutes}min")
    else:
        if explicit_created is not None or explicit_modified is not None:
            _out(f"  timeline: preserve mode with explicit timestamps, span={span}min")
        else:
            _out(f"  timeline: preserved timestamps span={span}min")

    if args.clean:
        author_text = args.author or "<removed>"
        company_text = args.company or "<removed>"
        revision_text = str(args.revision if args.revision is not None else 1)
    else:
        author_text = (args.author if args.author else "<empty>") if args.author is not None else "<preserved>"
        company_text = (args.company if args.company else "<empty>") if args.company is not None else "<preserved>"
        revision_text = str(args.revision) if args.revision is not None else "<preserved>"
    _out(f"  author={author_text} company={company_text}")
    _out(f"  totalTime={edit_minutes}min revision={revision_text} source={source} estimated={estimated}")
    if baseline:
        _out(f"  previousTotal={baseline['total_minutes']}min change={edit_minutes - baseline['total_minutes']:+d}min")
    _out(f"  state.file={state_path}")
    stats_note = "" if args.clean else " (app.xml stats preserved)"
    _out(
        "  stats: "
        f"pages={stats['pages']} words={stats['words']} chars={stats['chars']} "
        f"paragraphs={stats['paragraphs']} tables={stats['tables']} images={stats['images']}"
        + stats_note
    )
    _out(f"  dropped parts: {', '.join(removed) if removed else '<none>'}")
    _out(f"  review author fields scrubbed: {scrubbed}")
    if args.dry_run:
        _out("  dry-run: nothing written")
        return

    state = {
        "version": 1, "total_minutes": edit_minutes, "source": source, "estimated": estimated,
        "created": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modified": modified.strftime("%Y-%m-%dT%H:%M:%SZ"), "snapshot": snapshot,
    }
    fd, pending = tempfile.mkstemp(prefix=".docx-meta-", suffix=".tmp", dir=state_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        if args.backup:
            backup = path + ".bak"
            if os.path.exists(backup):
                backup += dt.datetime.now().strftime(".%Y%m%d%H%M%S%f")
            shutil.copy2(path, backup)
            _out(f"  backup: {backup} (keeps original metadata; do not deliver it)")
        rewrite_package(path, infos, entries, drops, zip_stamp(modified.astimezone()))
        if args.clean:
            if args.copy_style:
                os.utime(path, (original_accessed.timestamp(), modified.timestamp()))
                written = "copy-style: core timestamps kept; fs creation follows rewrite time"
            else:
                os.utime(path, (fs_accessed_target.timestamp(), fs_modified_target.timestamp()))
                times_restored = restore_file_times(
                    path, fs_created_target, fs_accessed_target, fs_modified_target)
                if os.name != "nt":
                    written = "clean: fs mtime/atime restored; birthtime unsupported"
                elif times_restored:
                    written = "clean: file times restored"
                else:
                    written = "clean: fs mtime/atime restored; birthtime not settable"
        else:
            os.utime(path, (fs_accessed_target.timestamp(), fs_modified_target.timestamp()))
            times_restored = restore_file_times(
                path, fs_created_target, fs_accessed_target, fs_modified_target)
            if os.name != "nt":
                written = "preserve: fs mtime/atime restored; birthtime unsupported"
            elif times_restored:
                written = "preserve: file times restored"
            else:
                written = "preserve: fs mtime/atime restored; birthtime not settable"
        try:
            os.replace(pending, state_path)
        except OSError as exc:
            raise OSError(f"DOCX written with TotalTime={edit_minutes}, but baseline save failed; "
                          f"recover with --edit-minutes {edit_minutes} before further editing: {exc}") from exc
    finally:
        if os.path.exists(pending):
            os.remove(pending)
    _out(f"  written ({written})")


def main():
    ap = argparse.ArgumentParser(
        description="Preserve or clean .docx metadata and maintain total editing time.")
    ap.add_argument("paths", nargs="+", help="one or more .docx files")
    property_mode = ap.add_mutually_exclusive_group()
    property_mode.add_argument(
        "--preserve", dest="clean", action="store_false",
        help="keep existing properties and package parts (default)")
    property_mode.add_argument(
        "--clean", dest="clean", action="store_true",
        help="remove personal metadata, as the previous default")
    ap.set_defaults(clean=False)
    ap.add_argument("--inspect", action="store_true", help="print current metadata only")
    ap.add_argument("--author", help="set author; default keeps it with --preserve, removes it with --clean")
    ap.add_argument("--company", default=None,
                    help="company value; default keeps it with --preserve, clears it with --clean")
    ap.add_argument("--title", help="document title; default keeps it with --preserve, removes it with --clean")
    ap.add_argument("--created", help="ISO datetime; default keeps the document value with --preserve")
    ap.add_argument("--modified", help="ISO datetime; default keeps the document value with --preserve")
    ap.add_argument("--mode", choices=("auto", "initial", "update"), default="auto",
                    help="auto initializes or accumulates; initial resets; update requires a baseline")
    duration = ap.add_mutually_exclusive_group()
    duration.add_argument("--edit-minutes", type=int, help="absolute total minutes; replaces the baseline total")
    duration.add_argument("--add-minutes", type=int, help="append a new session's minutes to the saved baseline")
    ap.add_argument("--state-file", help="external JSON baseline; one document only, useful after a rename")
    ap.add_argument("--pages", type=int, help="actual rendered page count; updates the Pages property")
    ap.add_argument(
        "--copy-style",
        action="store_true",
        help="clean mode only: fake a copied file; fs creation stays at write time (> modified)",
    )
    ap.add_argument("--chars-per-min", type=float, default=45.0, help="CJK chars per minute (default 45)")
    ap.add_argument("--words-per-min", type=float, default=32.0, help="Latin words per minute (default 32)")
    ap.add_argument("--revision", type=int,
                    help="revision number; default keeps it with --preserve, sets 1 with --clean")
    ap.add_argument("--keep-thumbnail", action="store_true", help="clean mode only: keep the thumbnail")
    ap.add_argument("--keep-custom-properties", action="store_true",
                    help="clean mode only: keep docProps/custom.xml")
    ap.add_argument("--keep-people", action="store_true", help="clean mode only: keep word/people.xml")
    ap.add_argument("--keep-review-authors", action="store_true",
                    help="clean mode only: keep w:author and w:initials")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--backup", action="store_true")
    args = ap.parse_args()
    if any(not math.isfinite(rate) or rate <= 0 for rate in (args.chars_per_min, args.words_per_min)):
        ap.error("--chars-per-min and --words-per-min must be finite and positive")
    if any(value is not None and value < 0 for value in (args.edit_minutes, args.add_minutes)):
        ap.error("editing minutes must be non-negative")
    if args.pages is not None and args.pages <= 0:
        ap.error("--pages must be a positive integer")
    if args.revision is not None and args.revision <= 0:
        ap.error("--revision must be a positive integer")
    if args.state_file and len(args.paths) != 1:
        ap.error("--state-file requires exactly one document")
    if args.mode == "initial" and args.add_minutes is not None:
        ap.error("--add-minutes cannot be combined with --mode initial")
    if args.copy_style and not args.clean:
        ap.error("--copy-style requires --clean")

    failed = False
    for path in args.paths:
        try:
            process(path, args)
        except Exception as exc:
            failed = True
            _out(f"[docx-meta] ERROR {path}: {exc}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
