import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


PAUSED = (
    "superpowers-using-superpowers",
    "superpowers-finishing-a-development-branch",
    "pua-pua",
    "pua-pua-loop",
)
MERGED = (
    "skills/superpowers-systematic-debugging/references/diagnosing-bugs/REFERENCE.md",
    "skills/claude-mem-smart-explore/references/learn-codebase/REFERENCE.md",
    "archive/disabled/pua-pua/references/styles/pua-mama/REFERENCE.md",
    "archive/disabled/pua-pua/references/styles/pua-yes/REFERENCE.md",
)


def prose(text):
    fence = None
    lines = []
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return re.sub(r"(?<!`)(`+)(?!`).*?(?<!`)\1(?!`)", "", "\n".join(lines), flags=re.DOTALL)


def exact_path_exists(path):
    path = Path(os.path.abspath(path))
    if not path.exists():
        return False
    for parent, part in zip(path.parents, reversed(path.parts[1:])):
        if part not in {entry.name for entry in parent.iterdir()}:
            return False
    return True


def local_links(text):
    for match in re.finditer(r"\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+\"[^\"]*\")?\)", prose(text)):
        target = match.group(1).strip("<>")
        if target.startswith("#") or target.startswith("//") or urlsplit(target).scheme:
            continue
        target = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if target and not any(char in target for char in "{}*<>"):
            yield target


def frontmatter_field(header, key):
    match = re.search(rf"^{key}:[ \t]*(.*)$", header, re.MULTILINE)
    if not match:
        return ""
    value = match.group(1).strip()
    if value in {"|", "|-", "|+", ">", ">-", ">+"}:
        remaining = header[match.end():].splitlines()
        block = []
        for line in remaining:
            if line and not line[0].isspace():
                break
            block.append(line.strip())
        return " ".join(block).strip()
    return value.strip("\"'")


def validate(root, expected_active=55, require_archives=True):
    root = Path(root).resolve()
    errors = []
    if not (root / "skills").is_dir():
        return [f"missing skills directory: {root}"]
    active = sorted((root / "skills").glob("*/SKILL.md"))
    if len(active) != expected_active:
        errors.append(f"active skill count: expected {expected_active}, got {len(active)}")
    for directory in (root / "skills").iterdir():
        if directory.is_dir() and not (directory / "SKILL.md").is_file():
            errors.append(f"missing entry: skills/{directory.name}/SKILL.md")
    nested = set((root / "skills").rglob("SKILL.md")) - set(active)
    errors.extend(f"nested active entry: {path.relative_to(root)}" for path in sorted(nested))
    names = []
    for path in active:
        text = path.read_text(encoding="utf-8-sig")
        match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
        if not match:
            errors.append(f"frontmatter missing or unclosed: {path.relative_to(root)}")
            continue
        name = frontmatter_field(match.group(1), "name")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            errors.append(f"invalid name: {path.relative_to(root)}")
        if not frontmatter_field(match.group(1), "description"):
            errors.append(f"empty description: {path.relative_to(root)}")
        names.append(name)
    errors.extend(f"duplicate skill name: {name}" for name, count in Counter(names).items() if count > 1)

    documents = active + [root / name for name in ("README.md", "INDEX.md", "MCP-SETUP.md", "TEST-SUMMARY.md") if (root / name).is_file()]
    for path in documents:
        for target in local_links(path.read_text(encoding="utf-8-sig")):
            # Keep lexical case: Windows resolves paths case-insensitively.
            candidate = path.parent / target
            if not exact_path_exists(candidate):
                errors.append(f"missing or case-mismatched link: {path.relative_to(root)} -> {target}")
    index = root / "INDEX.md"
    if index.is_file():
        indexed = Counter(re.findall(r"\]\((?:\./)?skills/([^/]+)/SKILL\.md\)", prose(index.read_text(encoding="utf-8-sig"))))
        actual = {path.parent.name for path in active}
        if set(indexed) != actual:
            errors.append(f"index coverage: missing={sorted(actual - set(indexed))}, stale={sorted(set(indexed) - actual)}")
        if any(count != 1 for count in indexed.values()):
            errors.append("index contains repeated active entries")
    else:
        errors.append("index missing: INDEX.md")

    if require_archives:
        for name in PAUSED:
            if not (root / "archive" / "disabled" / name / "REFERENCE.md").is_file():
                errors.append(f"archive missing: {name}")
        for target in MERGED:
            if not (root / target).is_file():
                errors.append(f"merged reference missing: {target}")
        for path in (root / "archive").rglob("SKILL.md"):
            errors.append(f"archive exposes active entry: {path.relative_to(root)}")
    try:
        config = json.loads((root / ".mcp.json").read_text(encoding="utf-8-sig"))
        servers = config["mcpServers"]
        chrome = servers["chrome-devtools"]
        args = chrome.get("args", [])
        if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            errors.append("chrome-devtools: args must be a list of strings")
        else:
            operands = args[1:] if args and args[0] in {"-y", "--yes"} else args
            if chrome.get("command") not in {"npx", "npx.cmd"} or not operands or not re.fullmatch(r"chrome-devtools-mcp(?:@[^\s]+)?", operands[0]):
                errors.append("chrome-devtools: expected npx and the actual chrome-devtools-mcp package operand")
        if "@anthropic-ai/claude-mem" in json.dumps(config):
            errors.append("claude-mem: nonexistent npm package")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"invalid MCP configuration: {exc}")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Read-only skill structure, index and local link checks; no runtime or full YAML validation.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--expected-active", type=int, default=55)
    args = parser.parse_args()
    errors = validate(args.root, args.expected_active)
    for error in errors:
        print(f"ERROR: {error}")
    print(f"Active entries: {len(list((args.root / 'skills').glob('*/SKILL.md')))}; errors: {len(errors)}")
    print("Scope: structure, required frontmatter fields, index, local links and MCP package declarations; not end-to-end execution.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
