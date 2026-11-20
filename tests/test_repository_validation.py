import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys


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

    def write_guides(self):
        fields = (
            "**能做什么**：整理示例内容。\n"
            "**适合谁**：需要整理资料的人。\n"
            "**准备什么**：用户提供的示例文件。\n"
            "**怎么配置**：`python --version`\n"
            "**怎么用**：请整理这份示例。\n"
            "**如何验证**：对照原文核对输出。\n"
            "**注意事项**：不发送真实资料。\n"
        )
        (self.root / "SKILL-GUIDE.md").write_text(
            '<a id="group-documents"></a>\n## 文档\n'
            '<a id="skill-sample"></a>\n### 示例\n'
            '[来源](skills/sample/SKILL.md)\n' + fields, encoding="utf-8")
        (self.root / "MCP-SETUP.md").write_text("".join(
            f'<a id="mcp-{name}"></a>\n## {name}\n' + fields
            for name in ("firecrawl", "chrome-devtools", "snipaste", "claude-mem", "dbx")
        ), encoding="utf-8")
        (self.root / "INSTALL.md").write_text(
            '<a id="choose"></a>\n# 选择\n'
            '[技能](SKILL-GUIDE.md#skill-sample)\n'
            '[工具](MCP-SETUP.md#mcp-dbx)\n'
            '[本节](#choose)\n', encoding="utf-8")

    def guide_errors(self):
        return validation.validate_installation_guides(self.root)

    def test_cli_guide_option_reports_missing_installation_documents(self):
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--root", str(self.root), "--expected-active", "1", "--installation-guide"],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
        )
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertIn("missing installation document: INSTALL.md", result.stdout)

    def test_complete_installation_guides_pass(self):
        self.write_guides()
        self.assertEqual([], self.guide_errors())

    def test_required_installation_guide_cannot_be_missing(self):
        self.write_guides()
        (self.root / "INSTALL.md").unlink()
        self.assertTrue(any("missing installation document: INSTALL.md" in error for error in self.guide_errors()))

    def test_skill_cards_must_cover_actual_skill_directories(self):
        self.write_guides()
        extra = self.root / "skills" / "another"
        extra.mkdir()
        (extra / "SKILL.md").write_text("# Another", encoding="utf-8")
        self.assertTrue(any("card coverage" in error and "skill-another" in error for error in self.guide_errors()))

    def test_stale_skill_card_is_rejected(self):
        self.write_guides()
        card = self.root / "SKILL-GUIDE.md"
        card.write_text(card.read_text(encoding="utf-8").replace("skill-sample", "skill-retired"), encoding="utf-8")
        self.assertTrue(any("card coverage" in error and "skill-retired" in error for error in self.guide_errors()))

    def test_duplicate_skill_cards_are_rejected(self):
        self.write_guides()
        card = self.root / "SKILL-GUIDE.md"
        with card.open("a", encoding="utf-8") as target:
            target.write(card.read_text(encoding="utf-8"))
        self.assertTrue(any("duplicate card: skill-sample" in error for error in self.guide_errors()))

    def test_each_card_requires_its_own_configuration(self):
        self.write_guides()
        card = self.root / "MCP-SETUP.md"
        card.write_text(card.read_text(encoding="utf-8").replace("**怎么配置**：`python --version`", "**怎么配置**：", 1), encoding="utf-8")
        self.assertTrue(any("mcp-firecrawl" in error and "怎么配置" in error for error in self.guide_errors()))

    def test_missing_card_field_is_rejected(self):
        self.write_guides()
        card = self.root / "SKILL-GUIDE.md"
        card.write_text(card.read_text(encoding="utf-8").replace("**怎么用**：请整理这份示例。\n", ""), encoding="utf-8")
        self.assertTrue(any("skill-sample" in error and "怎么用" in error for error in self.guide_errors()))

    def test_duplicate_card_field_is_rejected(self):
        self.write_guides()
        with (self.root / "SKILL-GUIDE.md").open("a", encoding="utf-8") as target:
            target.write("**怎么用**：另一份说明。\n")
        self.assertTrue(any("skill-sample" in error and "怎么用" in error for error in self.guide_errors()))

    def test_commented_out_cards_do_not_satisfy_coverage(self):
        self.write_guides()
        card = self.root / "MCP-SETUP.md"
        card.write_text("<!--\n" + card.read_text(encoding="utf-8") + "\n-->\n", encoding="utf-8")
        self.assertTrue(any("card coverage" in error and "mcp-dbx" in error for error in self.guide_errors()))

    def test_comment_only_field_is_empty(self):
        self.write_guides()
        card = self.root / "SKILL-GUIDE.md"
        card.write_text(card.read_text(encoding="utf-8").replace(
            "**怎么用**：请整理这份示例。", "**怎么用**：<!-- 暂不提供 -->"), encoding="utf-8")
        self.assertTrue(any("skill-sample" in error and "怎么用" in error for error in self.guide_errors()))

    def test_commented_anchor_is_not_a_navigation_target(self):
        self.write_guides()
        guide = self.root / "INSTALL.md"
        guide.write_text(guide.read_text(encoding="utf-8").replace(
            '<a id="choose"></a>', '<!--\n<a id="choose"></a>\n-->'), encoding="utf-8")
        self.assertTrue(any("missing installation anchor" in error and "#choose" in error for error in self.guide_errors()))

    def test_hidden_links_and_duplicate_fields_are_ignored(self):
        self.write_guides()
        with (self.root / "SKILL-GUIDE.md").open("a", encoding="utf-8") as target:
            target.write("<!--\n**怎么用**：旧说明。\n[旧链接](missing.md#old)\n-->\n")
        self.assertEqual([], self.guide_errors())

    def test_same_line_duplicate_field_is_rejected(self):
        self.write_guides()
        card = self.root / "SKILL-GUIDE.md"
        card.write_text(card.read_text(encoding="utf-8").replace(
            "**怎么用**：请整理这份示例。", "**怎么用**：请整理这份示例。 **怎么用**：另一份说明。"), encoding="utf-8")
        self.assertTrue(any("skill-sample" in error and "怎么用" in error for error in self.guide_errors()))

    def test_field_examples_in_inline_code_are_not_duplicates(self):
        self.write_guides()
        with (self.root / "SKILL-GUIDE.md").open("a", encoding="utf-8") as target:
            target.write("字段示例：`**怎么用**：示例`，注释语法：`<!-- example -->`。\n")
        self.assertEqual([], self.guide_errors())

    def test_visible_inline_comment_syntax_can_be_field_content(self):
        self.write_guides()
        card = self.root / "SKILL-GUIDE.md"
        card.write_text(card.read_text(encoding="utf-8").replace(
            "**怎么用**：请整理这份示例。", "**怎么用**：`<!-- example -->`"), encoding="utf-8")
        self.assertEqual([], self.guide_errors())

    def test_card_field_may_include_additional_paragraphs(self):
        self.write_guides()
        card = self.root / "SKILL-GUIDE.md"
        card.write_text(card.read_text(encoding="utf-8").replace(
            "**怎么用**：请整理这份示例。", "**怎么用**：请整理这份示例。\n\n也可先列出原文中的要点。"), encoding="utf-8")
        self.assertEqual([], self.guide_errors())

    def test_mcp_card_coverage_is_independent_of_project_configuration(self):
        self.write_guides()
        card = self.root / "MCP-SETUP.md"
        card.write_text(card.read_text(encoding="utf-8").replace('id="mcp-dbx"', 'id="mcp-unknown"'), encoding="utf-8")
        self.assertTrue(any("card coverage" in error and "mcp-dbx" in error for error in self.guide_errors()))

    def test_guide_anchor_target_must_exist(self):
        self.write_guides()
        with (self.root / "INSTALL.md").open("a", encoding="utf-8") as target:
            target.write("[不存在](SKILL-GUIDE.md#skill-missing)\n")
        self.assertTrue(any("missing installation anchor" in error and "skill-missing" in error for error in self.guide_errors()))

    def test_fragment_only_guide_links_are_checked(self):
        self.write_guides()
        with (self.root / "INSTALL.md").open("a", encoding="utf-8") as target:
            target.write("[不存在](#missing)\n")
        self.assertTrue(any("missing installation anchor" in error and "#missing" in error for error in self.guide_errors()))

    def test_index_links_to_guide_anchors_are_checked(self):
        self.write_guides()
        with (self.root / "INDEX.md").open("a", encoding="utf-8") as target:
            target.write("[新手](SKILL-GUIDE.md#skill-typo)\n")
        self.assertTrue(any("missing installation anchor" in error and "INDEX.md" in error for error in self.guide_errors()))

    def test_guide_links_require_exact_filename_case(self):
        self.write_guides()
        with (self.root / "INSTALL.md").open("a", encoding="utf-8") as target:
            target.write("[错误大小写](skill-guide.md#skill-sample)\n")
        self.assertTrue(any("case-mismatched link" in error for error in self.guide_errors()))

    def test_fenced_cards_and_example_links_do_not_count(self):
        self.write_guides()
        with (self.root / "SKILL-GUIDE.md").open("a", encoding="utf-8") as target:
            target.write('```md\n<a id="skill-example"></a>\n[样例](missing.md#absent)\n```\n')
            target.write('内联样例：`[示例](missing.md#absent)`\n')
        self.assertEqual([], self.guide_errors())

    def test_new_guides_receive_default_local_link_checks(self):
        self.write_guides()
        with (self.root / "SKILL-GUIDE.md").open("a", encoding="utf-8") as target:
            target.write("[缺失来源](skills/sample/absent.md)\n")
        self.assertTrue(any("absent.md" in error for error in self.errors()))


if __name__ == "__main__":
    unittest.main()
