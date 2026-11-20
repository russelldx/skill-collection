import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('handoff.py')


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / '交接 space'
        self.root.mkdir()
        self.state = {
            'schemaVersion': 2, 'session': 'example', 'title': '示例',
            'phase': '实现', 'status': 'in-progress',
            'updatedAt': '2026-11-17T10:00:00',
            'goal': '保留准确约束', 'constraints': ['只读数据库，不提交'],
            'acceptance': ['独立核验'], 'openBlockers': [],
            'nextActions': [], 'fileOwnership': {'main': ['src/']},
            'artifacts': [], 'keyDecisions': [
                {'id': 'D1', 'decision': '采用本地文件', 'source': '用户原文 §1'}
            ], 'tags': [], 'tasks': [],
        }
        self.body = '## 1、2026-11-17 会话：未完成\n\n尚未完成；需要复核。\n'
        self.write_doc()

    def write_doc(self):
        text = '# 示例\n\n## 当前态\n\n```handoff-state\n'
        text += json.dumps(self.state, ensure_ascii=False, indent=2)
        text += '\n```\n\n## 0、滚动摘要\n\n旧摘要\n\n' + self.body
        (self.root / 'HANDOFF.md').write_text(text, encoding='utf-8')

    def run_cli(self, command, *args, ok=None):
        p = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(SCRIPT),
                            command, str(self.root), *map(str, args)],
                           capture_output=True, encoding='utf-8')
        if ok is not None:
            self.assertEqual(p.returncode, ok, p.stdout + p.stderr)
        return p

    def refresh(self):
        self.run_cli('refresh', ok=0)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def task(self):
        self.state['tasks'] = [{
            'id': 'T1', 'title': '第一批', 'status': 'done',
            'verified': True, 'openItems': [],
            'evidence': ['python test.py: PASS'], 'summary': '已核验第一批',
        }]
        self.body = ('## 1、2026-11-17 会话：第一批\n\n**task**: T1\n'
                     '原始结论，不能被摘要替代。\n\n'
                     '```text\n## 90、这只是工具输出\n```\n\n'
                     '## 2、2026-11-17 会话：继续\n\n**task**: T2\n未完成\n')
        self.write_doc()

    def test_refresh_derives_state_and_rollup(self):
        self.refresh()
        state = json.loads((self.root / 'STATE.json').read_text(encoding='utf-8'))
        self.assertEqual(state['goal'], '保留准确约束')
        self.assertEqual(state['constraints'], ['只读数据库，不提交'])
        self.assertEqual(len(state['source']['sha256']), 64)
        doc = (self.root / 'HANDOFF.md').read_text(encoding='utf-8')
        self.assertNotIn('旧摘要', doc)
        self.assertIn('尚未完成；需要复核。', doc)
        self.run_cli('validate', ok=0)

    def test_refresh_is_idempotent(self):
        self.refresh()
        before = self.snapshot()
        self.refresh()
        self.assertEqual(before, self.snapshot())

    def test_same_day_edit_is_detected_without_relying_on_mtime(self):
        self.refresh()
        p = self.root / 'HANDOFF.md'
        stat = p.stat()
        p.write_text(p.read_text(encoding='utf-8') + '\n同日新增裁决\n', encoding='utf-8')
        os.utime(p, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertNotEqual(self.run_cli('validate').returncode, 0)
        self.assertNotEqual(self.run_cli('context').returncode, 0)

    def test_tampered_view_is_rejected(self):
        self.refresh()
        p = self.root / 'STATE.json'
        state = json.loads(p.read_text(encoding='utf-8'))
        state['constraints'] = ['允许提交']
        p.write_text(json.dumps(state), encoding='utf-8')
        self.assertNotEqual(self.run_cli('context').returncode, 0)

    def test_context_is_read_only_and_does_not_load_unrelated_archive(self):
        self.refresh()
        (self.root / 'archive').mkdir()
        (self.root / 'archive' / 'old.md').write_text('## 7、旧任务\n不相关内容', encoding='utf-8')
        before = self.snapshot()
        p = self.run_cli('context', '--max-bytes', 6000, ok=0)
        data = json.loads(p.stdout)
        self.assertEqual(data['contract']['constraints'], ['只读数据库，不提交'])
        self.assertNotIn('不相关内容', p.stdout)
        self.assertLessEqual(len(p.stdout.encode('utf-8')), 6000)
        self.assertEqual(before, self.snapshot())

    def test_required_context_never_silently_truncated(self):
        self.state['constraints'] = ['不得删除' * 4000]
        self.write_doc()
        self.refresh()
        p = self.run_cli('context', '--max-bytes', 2000)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(p.stdout, '')
        self.assertIn('budget', p.stderr)

    def test_legacy_validate_remains_available_but_context_requires_current_block(self):
        (self.root / 'HANDOFF.md').write_text('## 1、2026-11-17\n遗留文档\n', encoding='utf-8')
        legacy = dict(self.state, schemaVersion=1, fileOwnership={})
        (self.root / 'STATE.json').write_text(json.dumps(legacy), encoding='utf-8')
        self.run_cli('validate', ok=0)
        self.assertNotEqual(self.run_cli('context').returncode, 0)

    def test_explicit_existing_doc_is_accepted(self):
        self.run_cli('search', '复核', '--doc', 'HANDOFF.md', ok=0)

    def test_index_does_not_call_unfinished_section_closed(self):
        p = self.run_cli('index', '--max-bytes', 1)
        self.assertNotEqual(p.returncode, 2, p.stdout + p.stderr)
        index = (self.root / 'INDEX.md').read_text(encoding='utf-8')
        self.assertNotIn('- §1 ', index)
        self.assertIn(str((self.root / 'HANDOFF.md').stat().st_size) + 'B', index)

    def test_fenced_h2_is_not_a_real_section(self):
        self.task()
        self.run_cli('index', ok=0)
        index = (self.root / 'INDEX.md').read_text(encoding='utf-8')
        self.assertNotIn('| 90 |', index)

    def test_index_keeps_manual_index(self):
        (self.root / 'INDEX.md').write_text('手维护索引', encoding='utf-8')
        self.run_cli('index', ok=0)
        self.assertEqual((self.root / 'INDEX.md').read_text(encoding='utf-8'), '手维护索引')
        self.assertTrue((self.root / 'INDEX.generated.md').exists())

    def test_search_returns_match_window_and_bounds_entire_output(self):
        self.body = '## 1、长文\n\n' + '无关前言 ' * 800 + '\n唯一锚点 NEEDLE 证据\n'
        self.write_doc()
        p = self.run_cli('search', 'NEEDLE', '--max-bytes', 1400, ok=0)
        self.assertIn('NEEDLE', p.stdout)
        self.assertIn('唯一锚点', p.stdout)
        self.assertLessEqual(len(p.stdout.encode('utf-8')), 1400)

    def test_search_excludes_superseded_and_filters_task(self):
        self.body = ('## 1、旧结论\n**task**: T1\n**superseded-by**: D2\nNEEDLE old\n'
                     '## 2、新结论\n**task**: T1\nNEEDLE new\n'
                     '## 3、另一个任务\n**task**: T2\nNEEDLE other\n')
        self.write_doc()
        p = self.run_cli('search', 'NEEDLE', '--task', 'T1', ok=0)
        self.assertIn('new', p.stdout)
        self.assertNotIn('old', p.stdout)
        self.assertNotIn('other', p.stdout)

    def test_search_does_not_match_chinese_shared_single_character(self):
        self.body = '## 1、网络\n响应缓慢\n'
        self.write_doc()
        p = self.run_cli('search', '缓存')
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)

    def test_invalid_limits_are_rejected(self):
        for args in [('-k', '0'), ('-k', '-1'), ('-k', '100000'), ('--max-bytes', '0')]:
            with self.subTest(args=args):
                self.assertEqual(self.run_cli('search', '复核', *args).returncode, 2)

    def test_archive_preview_has_no_writes(self):
        self.task()
        self.refresh()
        before = self.snapshot()
        p = self.run_cli('archive', 'T1', ok=0)
        preview = json.loads(p.stdout)
        self.assertEqual(preview['sections'], [1])
        self.assertEqual(before, self.snapshot())

    def test_archive_requires_closed_verified_and_no_open_items(self):
        for key, value in [('status', 'in-progress'), ('verified', False),
                           ('evidence', []), ('summary', ''), ('openItems', ['待验收'])]:
            with self.subTest(key=key):
                self.task()
                self.state['tasks'][0][key] = value
                self.write_doc()
                self.refresh()
                before = self.snapshot()
                self.assertNotEqual(self.run_cli('archive', 'T1', '--apply').returncode, 0)
                self.assertEqual(before, self.snapshot())

    def test_archive_preserves_raw_section_backup_and_reference(self):
        self.task()
        self.refresh()
        old = (self.root / 'HANDOFF.md').read_bytes()
        section = old[old.index('## 1、'.encode()):old.index('## 2、'.encode())]
        self.run_cli('archive', 'T1', '--apply', ok=0)
        archive = self.root / 'archive' / 'T1.md'
        self.assertIn(section, archive.read_bytes())
        doc = (self.root / 'HANDOFF.md').read_text(encoding='utf-8')
        self.assertNotIn('原始结论', doc)
        self.assertIn('archive/T1.md', doc)
        self.assertIn('**task**: T2', doc)
        self.assertTrue(any(p.read_bytes() == old for p in (self.root / '.backup').rglob('*') if p.is_file()))
        self.run_cli('validate', ok=0)
        self.run_cli('search', '原始结论', '--task', 'T1', ok=0)
        before = self.snapshot()
        self.run_cli('archive', 'T1', '--apply', ok=0)
        self.assertEqual(before, self.snapshot())

    def test_archive_rejects_existing_different_target(self):
        self.task()
        self.refresh()
        (self.root / 'archive').mkdir()
        (self.root / 'archive' / 'T1.md').write_text('他人的存档', encoding='utf-8')
        before = self.snapshot()
        self.assertNotEqual(self.run_cli('archive', 'T1', '--apply').returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_writer_lock_is_not_removed_or_bypassed(self):
        self.task()
        self.refresh()
        (self.root / '.handoff.lock').write_text('someone else', encoding='utf-8')
        before = self.snapshot()
        self.assertNotEqual(self.run_cli('archive', 'T1', '--apply').returncode, 0)
        self.assertEqual(before, self.snapshot())

    def write_recent(self, count=6):
        records = [{'id': 'r' + str(i), 'messages': [
            {'role': 'user', 'content': '用户原文 ' + str(i)},
            {'role': 'assistant', 'content': '回答原文 ' + str(i)}]} for i in range(count)]
        (self.root / 'RECENT.jsonl').write_text(
            ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records), encoding='utf-8')
        return records

    def test_recent_requires_opt_in_and_keeps_last_complete_turns(self):
        self.refresh()
        records = self.write_recent()
        p = self.run_cli('context', ok=0)
        self.assertEqual(json.loads(p.stdout)['recent'], [])
        self.assertNotIn('用户原文 0', p.stdout)
        p = self.run_cli('context', '--recent', ok=0)
        data = json.loads(p.stdout)
        self.assertEqual(data['recent'], records[2:])
        p = self.run_cli('context', '--recent', '--after-id', 'r4', ok=0)
        self.assertEqual(json.loads(p.stdout)['recent'], records[5:])

    def test_oversized_turn_is_not_mislabeled_complete(self):
        self.refresh()
        records = self.write_recent(1)
        records[0]['messages'][0]['content'] = '大' * 10000
        (self.root / 'RECENT.jsonl').write_text(json.dumps(records[0]), encoding='utf-8')
        p = self.run_cli('context', '--recent', '--max-bytes', 5000, ok=0)
        data = json.loads(p.stdout)
        self.assertEqual(data['recent'], [])
        self.assertGreater(data['omittedRecent'], 0)
        self.assertLessEqual(len(p.stdout.encode('utf-8')), 5000)

    def test_recent_rejects_hidden_roles_and_broken_tool_pairs(self):
        self.refresh()
        for messages in [
            [{'role': 'system', 'content': 'private'}],
            [{'role': 'user', 'content': 'hi'}, {'role': 'tool', 'content': 'result', 'tool_call_id': 'x'}],
            [{'role': 'user', 'content': 'hi'}, {'role': 'assistant', 'content': '',
              'tool_calls': [{'id': 'x', 'name': 'Read', 'arguments': {}}]}],
        ]:
            with self.subTest(messages=messages):
                (self.root / 'RECENT.jsonl').write_text(json.dumps({'id': 'r', 'messages': messages}), encoding='utf-8')
                self.assertNotEqual(self.run_cli('context', '--recent').returncode, 0)

    def test_isolation_gate_precedes_loading_main_context(self):
        self.refresh()
        (self.root / 'TEAM.md').write_text('## 隔离模式\n```yaml\nisolation: on\nmain-role: developer\nisolated-roles: [qa]\n```\n', encoding='utf-8')
        for args in [(), ('--role', 'qa')]:
            p = self.run_cli('context', *args)
            self.assertNotEqual(p.returncode, 0)
            self.assertNotIn('保留准确约束', p.stdout + p.stderr)
        self.run_cli('context', '--role', 'developer', ok=0)
        self.assertNotEqual(self.run_cli('search', '复核').returncode, 0)
        self.assertNotEqual(self.run_cli('status').returncode, 0)

    def test_doc_cannot_escape_authorized_root(self):
        outside = self.root.parent / 'outside.md'
        outside.write_text('## 1、外部\n复核 secret\n', encoding='utf-8')
        p = self.run_cli('search', '复核', '--doc', outside)
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn('secret', p.stdout)

    def test_bullet_isolation_template_is_enforced(self):
        self.refresh()
        (self.root / 'TEAM.md').write_text(
            '## 隔离模式\n- isolation: on（保持隔离）\n- main-role: developer（主角色）\n', encoding='utf-8')
        self.assertNotEqual(self.run_cli('context').returncode, 0)
        self.run_cli('context', '--role', 'developer', ok=0)

    def test_archive_rejects_duplicate_section_numbers(self):
        self.task()
        self.body += '\n## 1、另一个第一节\n**task**: T1\n额外内容\n'
        self.write_doc()
        self.refresh()
        before = self.snapshot()
        self.assertNotEqual(self.run_cli('archive', 'T1', '--apply').returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_archive_only_rewrites_the_actual_current_block(self):
        self.task()
        p = self.root / 'HANDOFF.md'
        example = '# 引用示例\n\n## 示例\n```handoff-state\n{"example": true}\n```\n\n'
        p.write_text(example + p.read_text(encoding='utf-8'), encoding='utf-8')
        self.refresh()
        self.run_cli('archive', 'T1', '--apply', ok=0)
        self.assertIn('{"example": true}', p.read_text(encoding='utf-8'))
        state = json.loads((self.root / 'STATE.json').read_text(encoding='utf-8'))
        self.assertEqual(state['tasks'], [])

    def test_recent_malformed_messages_fail_cleanly_without_traceback(self):
        self.refresh()
        for messages in [[1], [{'role': 'user', 'content': 'unfinished'}]]:
            (self.root / 'RECENT.jsonl').write_text(json.dumps({'id': 'r', 'messages': messages}), encoding='utf-8')
            p = self.run_cli('context', '--recent')
            self.assertEqual(p.returncode, 2)
            self.assertNotIn('Traceback', p.stderr)

    def test_recent_preserves_valid_tool_chain_verbatim(self):
        self.refresh()
        record = {'id': 'tools', 'messages': [
            {'role': 'user', 'content': '读取结果'},
            {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'x', 'name': 'Read', 'arguments': {'path': 'a'}}]},
            {'role': 'tool', 'content': '原始结果', 'tool_call_id': 'x'},
            {'role': 'assistant', 'content': '完成'},
        ]}
        (self.root / 'RECENT.jsonl').write_text(json.dumps(record), encoding='utf-8')
        self.assertEqual(json.loads(self.run_cli('context', '--recent', ok=0).stdout)['recent'], [record])

    def test_archive_keeps_crlf_event_bytes(self):
        self.task()
        p = self.root / 'HANDOFF.md'
        p.write_bytes(p.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
        self.refresh()
        old = p.read_bytes()
        event = old[old.index('## 1、'.encode()):old.index('## 2、'.encode())]
        self.run_cli('archive', 'T1', '--apply', ok=0)
        self.assertIn(event, (self.root / 'archive' / 'T1.md').read_bytes())

    def test_context_retrieval_uses_total_and_hit_limits(self):
        self.body = ''.join('## %d、证据\n**task**: T1\nNEEDLE %d\n' % (i, i) for i in range(1, 8))
        self.write_doc()
        self.refresh()
        p = self.run_cli('context', '--query', 'NEEDLE', '--task', 'T1', '--max-bytes', 5000, ok=0)
        packet = json.loads(p.stdout)
        self.assertEqual(len(packet['retrieved']), 3)
        self.assertEqual(packet['omittedHits'], 4)
        self.assertLessEqual(len(p.stdout.encode('utf-8')), 5000)

    def test_budget_counts_actual_stdout_bytes(self):
        self.refresh()
        for command, extra in [('context', []), ('search', ['复核'])]:
            args = [sys.executable, '-X', 'utf8', '-B', str(SCRIPT), command, str(self.root), *extra]
            first = subprocess.run(args, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            budget = len(first.stdout) - 8
            result = subprocess.run([*args, '--max-bytes', str(budget)], capture_output=True)
            self.assertTrue(result.returncode != 0 or len(result.stdout) <= budget,
                            'raw stdout %d exceeds budget %d' % (len(result.stdout), budget))

    def test_false_string_cannot_authorize_removing_unfinished_action(self):
        self.task()
        self.state['nextActions'] = [{'task': 'T1', 'desc': '未完成', 'done': 'false'}]
        self.write_doc()
        self.assertEqual(self.run_cli('refresh').returncode, 2)
        self.assertIn('未完成', (self.root / 'HANDOFF.md').read_text(encoding='utf-8'))

    def test_nested_doc_cannot_bypass_isolation(self):
        protected = self.root / 'isolated'
        (protected / 'main').mkdir(parents=True)
        (protected / 'TEAM.md').write_text('- isolation: on\n- main-role: developer\n', encoding='utf-8')
        (protected / 'main' / 'HANDOFF.md').write_bytes((self.root / 'HANDOFF.md').read_bytes())
        p = self.run_cli('search', '复核', '--doc', 'isolated/main/HANDOFF.md')
        self.assertEqual(p.returncode, 2)
        self.assertNotIn('尚未完成', p.stdout)
        self.run_cli('search', '复核', '--doc', 'isolated/main/HANDOFF.md', '--role', 'developer', ok=0)
        self.assertEqual(self.run_cli('refresh', '--doc', 'isolated/main/HANDOFF.md').returncode, 2)

    def test_backup_names_do_not_collide_with_state_view(self):
        self.task()
        (self.root / 'sub').mkdir()
        document = self.root / 'sub' / 'STATE.json'
        document.write_bytes((self.root / 'HANDOFF.md').read_bytes())
        self.run_cli('refresh', '--doc', 'sub/STATE.json', ok=0)
        before = document.read_bytes()
        self.run_cli('archive', 'T1', '--apply', '--doc', 'sub/STATE.json', ok=0)
        self.assertTrue(any(p.read_bytes() == before for p in (self.root / '.backup').rglob('*') if p.is_file()))

    def test_near_window_waits_for_final_assistant_reply(self):
        self.refresh()
        record = {'id': 'inflight', 'messages': [
            {'role': 'user', 'content': '读取'},
            {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'x', 'name': 'Read', 'arguments': {}}]},
            {'role': 'tool', 'content': '结果', 'tool_call_id': 'x'},
        ]}
        (self.root / 'RECENT.jsonl').write_text(json.dumps(record), encoding='utf-8')
        self.assertEqual(self.run_cli('context', '--recent').returncode, 2)

    def test_fallback_index_does_not_overwrite_second_manual_file(self):
        for name in ('INDEX.md', 'INDEX.generated.md'):
            (self.root / name).write_text('人工整理 ' + name, encoding='utf-8')
        before = self.snapshot()
        self.assertEqual(self.run_cli('index').returncode, 2)
        self.assertEqual(before, self.snapshot())

    def test_bracket_directory_retains_archive_search(self):
        bracket = self.root / '[1]'
        bracket.mkdir()
        self.root = bracket
        self.task()
        self.refresh()
        self.run_cli('archive', 'T1', '--apply', ok=0)
        p = self.run_cli('search', '原始结论', '--task', 'T1', ok=0)
        self.assertIn('archive/T1.md', p.stdout)

    def test_current_date_and_ownership_types_are_validated(self):
        self.state['updatedAt'] = 'not-a-date'
        self.write_doc()
        self.assertEqual(self.run_cli('refresh').returncode, 2)
        self.state['updatedAt'] = '2026-11-17T20:00:00'
        self.state['fileOwnership'] = {'main': [123]}
        self.write_doc()
        self.assertEqual(self.run_cli('refresh').returncode, 2)

    def test_same_basename_does_not_confuse_source_identity(self):
        self.refresh()
        for name in ('one', 'two'):
            (self.root / name).mkdir()
            (self.root / name / 'HANDOFF.md').write_bytes((self.root / 'HANDOFF.md').read_bytes())
        self.run_cli('refresh', '--doc', 'one/HANDOFF.md', ok=0)
        self.run_cli('context', '--doc', 'one/HANDOFF.md', ok=0)
        self.assertEqual(self.run_cli('context', '--doc', 'two/HANDOFF.md').returncode, 2)

    def test_malformed_tool_result_id_is_rejected_cleanly(self):
        self.refresh()
        record = {'id': 'bad-result', 'messages': [
            {'role': 'user', 'content': '读取'},
            {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'x', 'name': 'Read', 'arguments': {}}]},
            {'role': 'tool', 'content': '结果', 'tool_call_id': ['x']},
            {'role': 'assistant', 'content': '完成'},
        ]}
        (self.root / 'RECENT.jsonl').write_text(json.dumps(record), encoding='utf-8')
        p = self.run_cli('context', '--recent')
        self.assertEqual(p.returncode, 2)
        self.assertNotIn('Traceback', p.stderr)

    def test_default_context_budget_rejects_oversized_required_content(self):
        self.state['constraints'] = ['必须保留' * 1100]
        self.write_doc()
        self.refresh()
        p = self.run_cli('context')
        self.assertEqual(p.returncode, 2)
        self.assertEqual(p.stdout, '')
        self.assertIn('budget', p.stderr)
        self.run_cli('context', '--max-bytes', 24000, ok=0)

    def test_default_optional_budgets_bound_recent_and_search(self):
        self.refresh()
        records = self.write_recent(1)
        records[0]['messages'][0]['content'] = '大' * 2200
        (self.root / 'RECENT.jsonl').write_text(json.dumps(records[0]), encoding='utf-8')
        packet = json.loads(self.run_cli('context', '--recent', ok=0).stdout)
        self.assertEqual(packet['recent'], [])
        self.assertEqual(packet['omittedRecent'], 1)
        self.body = ''.join('## %d、证据\nNEEDLE %s\n' % (i, '数据' * 180) for i in range(1, 8))
        self.write_doc()
        self.refresh()
        packet = json.loads(self.run_cli('context', '--query', 'NEEDLE', ok=0).stdout)
        self.assertLessEqual(len(json.dumps(packet['retrieved'], ensure_ascii=False, indent=2).encode()) + 1, 3000)
        p = self.run_cli('search', 'NEEDLE', '-k', 20, ok=0)
        self.assertLessEqual(len(p.stdout.encode()), 3000)
        self.assertGreater(json.loads(p.stdout)['omittedHits'], 0)

    def test_feature_directories_keep_state_archives_indexes_and_locks_separate(self):
        parent = self.root
        roots = [parent / 'feature-a', parent / 'feature-b']
        snapshots = {}
        for root in roots:
            root.mkdir()
            self.root = root
            self.task()
            self.state['goal'] = root.name
            self.body += '\n' + root.name + '-private-evidence\n'
            self.write_doc()
            self.refresh()
            self.run_cli('index', ok=0)
            snapshots[root] = self.snapshot()
        self.root = roots[0]
        (roots[1] / '.handoff.lock').write_text('other-session', encoding='utf-8')
        self.run_cli('archive', 'T1', '--apply', ok=0)
        self.run_cli('index', ok=0)
        result = self.run_cli('context', '--query', 'private-evidence', ok=0)
        self.assertIn('feature-a-private-evidence', result.stdout)
        self.assertNotIn('feature-b', result.stdout)
        for path, data in snapshots[roots[1]].items():
            self.assertEqual((roots[1] / path).read_bytes(), data)
        self.assertEqual((roots[1] / '.handoff.lock').read_text(), 'other-session')
        (roots[1] / '.handoff.lock').unlink()
        archive_a = (roots[0] / 'archive/T1.md').read_bytes()
        self.root = roots[1]
        self.run_cli('archive', 'T1', '--apply', ok=0)
        self.assertEqual((roots[0] / 'archive/T1.md').read_bytes(), archive_a)
        self.assertTrue((roots[1] / 'archive/T1.md').is_file())
        self.root = parent
        packet = json.loads(self.run_cli('status', '--max-depth', 1, '--format', 'json', ok=0).stdout)
        self.assertEqual({str(Path(row['path']).parent) for row in packet['sessions']}, {str(r) for r in roots})

    def test_status_is_bounded_and_table_locates_feature_directories(self):
        self.refresh()
        data = (self.root / 'STATE.json').read_bytes()
        for i in range(25):
            directory = self.root / ('feature-%02d' % i)
            directory.mkdir()
            (directory / 'STATE.json').write_bytes(data)
        p = self.run_cli('status', '--max-depth', 1, '--format', 'json', ok=0)
        packet = json.loads(p.stdout)
        self.assertEqual(packet['count'], 26)
        self.assertEqual(len(packet['sessions']), 20)
        self.assertEqual(packet['omitted'], 6)
        table = self.run_cli('status', '--limit', 2, ok=0).stdout
        self.assertIn('feature-00', table)
        self.assertNotIn('feature-24', table)
        # 排序键打平时必须按路径升序兜底，top-2 恒为根目录 + feature-00，不依赖 readdir 顺序
        limited = json.loads(self.run_cli('status', '--limit', '2', '--format', 'json', ok=0).stdout)
        self.assertEqual([Path(r['path']).parent.name for r in limited['sessions']],
                         [self.root.name, 'feature-00'])
        for args in [('--limit', 0), ('--limit', 201), ('--max-depth', -1)]:
            self.assertEqual(self.run_cli('status', *args).returncode, 2)

    def test_sibling_isolation_is_not_read_by_parent_status(self):
        self.refresh()
        directory = self.root / 'protected'
        directory.mkdir()
        (directory / 'TEAM.md').write_text('- isolation: on\n- main-role: owner\n', encoding='utf-8')
        (directory / 'STATE.json').write_text('{"title": "DO_NOT_LOAD"}', encoding='utf-8')
        p = self.run_cli('status', '--format', 'json')
        self.assertEqual(p.returncode, 1)
        self.assertNotIn('DO_NOT_LOAD', p.stdout)
        self.assertEqual(json.loads(p.stdout)['count'], 1)

    def test_init_produces_usable_current_state(self):
        new = self.root / 'new'
        p = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(SCRIPT),
                            'init', str(new), '--title', '新任务'], capture_output=True, encoding='utf-8')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.root = new
        self.run_cli('validate', ok=0)
        self.run_cli('context', ok=0)


class CoordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.coord = Path(self.tmp.name) / '_coord'
        self.coord.mkdir()

    def run_cli(self, command, *args, ok=None):
        p = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(SCRIPT),
                            command, str(self.coord), *map(str, args)],
                           capture_output=True, encoding='utf-8')
        if ok is not None:
            self.assertEqual(p.returncode, ok, p.stdout + p.stderr)
        return p

    def test_claim_non_overlapping_succeeds(self):
        self.run_cli('claim', '--session', 's1', '--feature', 'login', '--files', 'src/a.ts', ok=0)
        self.run_cli('claim', '--session', 's2', '--feature', 'export', '--files', 'src/b.ts', ok=0)
        data = json.loads((self.coord / 'COORD.json').read_text(encoding='utf-8'))
        self.assertEqual(data['claims']['s1']['status'], 'active')
        self.assertEqual(data['claims']['s2']['status'], 'active')
        self.assertEqual(data['conflicts'], {})

    def test_claim_overlap_creates_conflict(self):
        self.run_cli('claim', '--session', 's1', '--feature', 'login', '--files', 'src/common.ts', ok=0)
        p = self.run_cli('claim', '--session', 's2', '--feature', 'export', '--files', 'src/common.ts', ok=0)
        result = json.loads(p.stdout)
        self.assertIn('conflict', result)
        data = json.loads((self.coord / 'COORD.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data['conflicts']), 1)
        conflict = list(data['conflicts'].values())[0]
        self.assertEqual(conflict['state'], 'open')
        self.assertIn('s1', conflict['participants'])
        self.assertIn('s2', conflict['participants'])

    def test_release_frees_files_for_new_claim(self):
        self.run_cli('claim', '--session', 's1', '--feature', 'login', '--files', 'src/a.ts', ok=0)
        self.run_cli('release', '--session', 's1', ok=0)
        self.run_cli('claim', '--session', 's2', '--feature', 'export', '--files', 'src/a.ts', ok=0)
        data = json.loads((self.coord / 'COORD.json').read_text(encoding='utf-8'))
        self.assertEqual(data['conflicts'], {})
        self.assertEqual(data['claims']['s2']['status'], 'active')

    def test_handoff_requires_all_participants_before_ready(self):
        self.run_cli('claim', '--session', 's1', '--feature', 'login', '--files', 'src/c.ts', ok=0)
        p = self.run_cli('claim', '--session', 's2', '--feature', 'export', '--files', 'src/c.ts', ok=0)
        cid = json.loads(p.stdout)['conflict']
        self.run_cli('handoff', '--conflict', cid, '--session', 's1', '--coordinator', ok=0)
        data = json.loads((self.coord / 'COORD.json').read_text(encoding='utf-8'))
        self.assertEqual(data['conflicts'][cid]['state'], 'open')
        self.run_cli('handoff', '--conflict', cid, '--session', 's2', ok=0)
        data = json.loads((self.coord / 'COORD.json').read_text(encoding='utf-8'))
        self.assertEqual(data['conflicts'][cid]['state'], 'ready')
        self.assertEqual(data['conflicts'][cid]['coordinator'], 's1')

    def test_only_one_coordinator_per_conflict(self):
        self.run_cli('claim', '--session', 's1', '--feature', 'login', '--files', 'src/c.ts', ok=0)
        p = self.run_cli('claim', '--session', 's2', '--feature', 'export', '--files', 'src/c.ts', ok=0)
        cid = json.loads(p.stdout)['conflict']
        self.run_cli('handoff', '--conflict', cid, '--session', 's1', '--coordinator', ok=0)
        p = self.run_cli('handoff', '--conflict', cid, '--session', 's2', '--coordinator')
        self.assertNotEqual(p.returncode, 0)

    def test_verify_closes_only_when_all_done(self):
        self.run_cli('claim', '--session', 's1', '--feature', 'login', '--files', 'src/c.ts', ok=0)
        p = self.run_cli('claim', '--session', 's2', '--feature', 'export', '--files', 'src/c.ts', ok=0)
        cid = json.loads(p.stdout)['conflict']
        self.run_cli('handoff', '--conflict', cid, '--session', 's1', '--coordinator', ok=0)
        self.run_cli('handoff', '--conflict', cid, '--session', 's2', ok=0)
        self.run_cli('verify', '--conflict', cid, '--session', 's1', ok=0)
        data = json.loads((self.coord / 'COORD.json').read_text(encoding='utf-8'))
        self.assertNotEqual(data['conflicts'][cid]['state'], 'closed')
        self.run_cli('verify', '--conflict', cid, '--session', 's2', ok=0)
        data = json.loads((self.coord / 'COORD.json').read_text(encoding='utf-8'))
        self.assertEqual(data['conflicts'][cid]['state'], 'closed')
        self.assertEqual(data['claims']['s1']['status'], 'released')
        self.assertEqual(data['claims']['s2']['status'], 'released')

    def test_coord_query_filters_by_session(self):
        self.run_cli('claim', '--session', 's1', '--feature', 'login', '--files', 'src/a.ts', ok=0)
        self.run_cli('claim', '--session', 's2', '--feature', 'export', '--files', 'src/b.ts', ok=0)
        p = self.run_cli('coord', '--session', 's1', ok=0)
        result = json.loads(p.stdout)
        self.assertIn('s1', result['claims'])
        self.assertNotIn('s2', result['claims'])

    def test_coord_query_is_bounded(self):
        for i in range(30):
            self.run_cli('claim', '--session', 's%d' % i, '--feature', 'f%d' % i,
                         '--files', 'src/f%d.ts' % i, ok=0)
        p = self.run_cli('coord', '--max-bytes', 2000, ok=0)
        self.assertLessEqual(len(p.stdout.encode('utf-8')), 2000)
        result = json.loads(p.stdout)
        self.assertIn('omitted', result)


if __name__ == '__main__':
    unittest.main()
