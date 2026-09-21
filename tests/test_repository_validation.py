import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "validate-skills.py"
spec = importlib.util.spec_from_file_location("repository_validation", SCRIPT)
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


class RepositoryValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / "skills" / "sample"
        self.skill.mkdir(parents=True)
        self.source = self.skill / "SKILL.md"
        self.source.write_text("---\nname: sample\ndescription: A sample skill.\n---\n# Sample\n", encoding="utf-8")
        (self.root / "INDEX.md").write_text("[sample](skills/sample/SKILL.md)\n", encoding="utf-8")
        (self.root / ".mcp.json").write_text(json.dumps({"mcpServers": {
            "chrome-devtools": {"command": "npx", "args": ["-y", "chrome-devtools-mcp@latest"]}
        }}), encoding="utf-8")

    def errors(self):
        return validation.validate(self.root, expected_active=1, require_archives=False)

    def test_valid_repository(self):
        self.assertEqual([], self.errors())

    def test_missing_frontmatter_fails(self):
        self.source.write_text("# Sample\nname: sample\ndescription: Outside YAML\n", encoding="utf-8")
        self.assertTrue(any("frontmatter" in error for error in self.errors()))

    def test_description_must_have_content(self):
        self.source.write_text("---\nname: sample\ndescription: |-\n---\n# Sample\n", encoding="utf-8")
        self.assertTrue(any("description" in error for error in self.errors()))

    def test_block_description_is_supported(self):
        self.source.write_text("---\nname: sample\ndescription: |-\n  First line.\n  Second line.\n---\n# Sample\n", encoding="utf-8")
        self.assertEqual([], self.errors())

    def test_missing_live_link_fails(self):
        with self.source.open("a", encoding="utf-8") as target:
            target.write("[missing](references/absent.md)\n")
        self.assertTrue(any("absent.md" in error for error in self.errors()))

    def test_fenced_examples_and_remote_links_are_not_local_files(self):
        with self.source.open("a", encoding="utf-8") as target:
            target.write("```md\n[example](missing.md)\n```\n[external](https://example.com/docs)\n[section](#sample)\n")
        self.assertEqual([], self.errors())

    def test_inline_code_examples_are_not_local_links(self):
        with self.source.open("a", encoding="utf-8") as target:
            target.write("Use `[download](output-file)` to show the result.\n")
        self.assertEqual([], self.errors())

    def test_links_use_case_sensitive_paths(self):
        (self.skill / "reference.md").write_text("# Reference", encoding="utf-8")
        with self.source.open("a", encoding="utf-8") as target:
            target.write("[reference](REFERENCE.md)\n")
        self.assertTrue(any("REFERENCE.md" in error for error in self.errors()))

    def test_parent_relative_link_exists(self):
        shared = self.root / "skills" / "guide.md"
        shared.write_text("# Guide", encoding="utf-8")
        with self.source.open("a", encoding="utf-8") as target:
            target.write("[guide](../guide.md)\n")
        self.assertEqual([], self.errors())

    def test_nested_skill_entry_fails(self):
        nested = self.skill / "references" / "old"
        nested.mkdir(parents=True)
        (nested / "SKILL.md").write_text(self.source.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertTrue(any("nested" in error for error in self.errors()))

    def test_index_must_cover_each_active_skill(self):
        (self.root / "INDEX.md").write_text("# Empty", encoding="utf-8")
        self.assertTrue(any("index" in error for error in self.errors()))

    def test_invalid_mcp_package_fails(self):
        (self.root / ".mcp.json").write_text(json.dumps({"mcpServers": {
            "chrome-devtools": {"command": "npx", "args": ["@anthropic-ai/chrome-devtools-mcp@latest"]}
        }}), encoding="utf-8")
        self.assertTrue(any("chrome-devtools" in error for error in self.errors()))

    def test_empty_description_cannot_consume_next_field(self):
        self.source.write_text("---\nname: sample\ndescription:\nlicense: MIT\n---\n# Sample\n", encoding="utf-8")
        self.assertTrue(any("description" in error for error in self.errors()))

    def test_correct_package_as_argument_to_wrong_package_fails(self):
        (self.root / ".mcp.json").write_text(json.dumps({"mcpServers": {
            "chrome-devtools": {"command": "npx", "args": ["-y", "wrong-package", "chrome-devtools-mcp@latest"]}
        }}), encoding="utf-8")
        self.assertTrue(any("chrome-devtools" in error for error in self.errors()))

    def test_missing_mcp_command_fails(self):
        (self.root / ".mcp.json").write_text(json.dumps({"mcpServers": {
            "chrome-devtools": {"args": ["-y", "chrome-devtools-mcp@latest"]}
        }}), encoding="utf-8")
        self.assertTrue(any("chrome-devtools" in error for error in self.errors()))

    @unittest.skipUnless(os.name == "nt", "case-insensitive root spelling applies to Windows")
    def test_windows_root_spelling_does_not_change_link_checks(self):
        alternate_root = Path(str(self.root).swapcase())
        self.assertTrue(alternate_root.exists())
        self.assertEqual([], validation.validate(alternate_root, expected_active=1, require_archives=False))

    def test_missing_archive_fails_when_required(self):
        errors = validation.validate(self.root, expected_active=1, require_archives=True)
        self.assertTrue(any("archive" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
