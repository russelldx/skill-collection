"""Fail-closed entrypoint and shell tests; no POI/workbook execution."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent
BASH = shutil.which('bash')


class PausedDeletionTests(unittest.TestCase):
    def test_direct_legacy_entrypoints_exit_before_file_access(self):
        for name in ('DeleteColumn', 'VerifyShift'):
            with self.subTest(name=name), tempfile.TemporaryDirectory(prefix='poi-paused-') as temp:
                root = Path(temp)
                source = SCRIPTS / (name + '.java')
                self.assertIn('PAUSED', source.read_text(encoding='utf-8'), 'Legacy entrypoint must fail closed')
                compiled = subprocess.run(['javac', '-encoding', 'UTF-8', '-d', str(root), str(source)],
                                          cwd=root, capture_output=True, text=True)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                src, dst = root / 'input.xlsx', root / 'output.xlsx'
                src.write_bytes(b'input sentinel')
                dst.write_bytes(b'output sentinel')
                for args in ([], [str(src), '1', str(dst)], [str(src), str(dst), '1']):
                    result = subprocess.run(['java', '-cp', str(root), name, *args], cwd=root,
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn('PAUSED', result.stderr)
                    self.assertEqual(src.read_bytes(), b'input sentinel')
                    self.assertEqual(dst.read_bytes(), b'output sentinel')
                reference = SCRIPTS.parent / 'references/paused-delete-column' / (name + '.java.txt')
                self.assertTrue(reference.is_file())
                self.assertIn('WorkbookFactory', reference.read_text(encoding='utf-8'))

    def shell(self, body, classpath=None):
        with tempfile.TemporaryDirectory(prefix='poi-shell-') as temp:
            env = os.environ.copy()
            env.pop('POI_CLASSPATH', None)
            if classpath:
                env['POI_CLASSPATH'] = classpath
            # Stub tools, not workbooks: proves guards and exact argument forwarding.
            script = 'java() { printf "JAVA:%s\\n" "$@"; }; javac() { printf "JAVAC:%s\\n" "$@"; }; source "$1"; ' + body
            return subprocess.run([BASH, '-c', script, 'test', str(SCRIPTS / 'poi_env.sh')],
                                  cwd=temp, env=env, capture_output=True, text=True)

    def test_shell_blocks_paused_classes_even_with_classpath(self):
        for body in ('poi_run DeleteColumn x 1 y', 'poi_run VerifyShift x y 1',
                     'poi_compile DeleteColumn.java', 'poi_compile VerifyShift.java'):
            with self.subTest(body=body):
                result = self.shell(body, 'explicit-dependencies/*')
                self.assertEqual(result.returncode, 2)
                self.assertIn('PAUSED', result.stderr)
                self.assertNotIn('JAVA:', result.stdout)
                self.assertNotIn('JAVAC:', result.stdout)

    def test_missing_classpath_has_actionable_error(self):
        result = self.shell('poi_run DumpStructure file.xls')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('POI_CLASSPATH', result.stderr)
        self.assertNotIn('JAVA:', result.stdout)

    def test_inspection_and_template_commands_still_forward(self):
        for body in ('poi_run DumpStructure "file with spaces.xls"', 'poi_compile MergeTemplate.java'):
            result = self.shell(body, 'local-dependencies/*')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('local-dependencies/*', result.stdout)
            self.assertNotIn('D:/develop', result.stdout)


if __name__ == '__main__':
    unittest.main()
