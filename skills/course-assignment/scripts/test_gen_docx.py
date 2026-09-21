"""Run dependency preflight in a scratch directory with controlled module lookup."""
from pathlib import Path
import base64
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).with_name('gen_docx.cjs')


class DependencyPreflightTests(unittest.TestCase):
    def preflight(self, available):
        with tempfile.TemporaryDirectory(prefix='course-deps-') as temp:
            root = Path(temp)
            script = root / SCRIPT.name
            shutil.copyfile(SCRIPT, script)
            preload = root / 'controlled-deps.cjs'
            preload.write_text("""const Module = require('module');
const original = Module._load;
Module._load = function(name, ...args) {
  if (name === 'docx') { %s }
  if (name === 'child_process') return { execSync() { throw new Error('no global deps in fixture'); } };
  return original.call(this, name, ...args);
};
""" % ("return {};" if available else "throw new Error('missing fixture dependency');"), encoding='utf-8')
            env = os.environ.copy()
            env.pop('NODE_PATH', None)
            result = subprocess.run(['node', '--require', str(preload), str(script), '--check-deps'],
                                    cwd=root, env=env, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0 if available else 1, result.stderr)
            self.assertIn('docx', result.stdout if available else result.stderr)
            if not available:
                self.assertIn('NODE_PATH', result.stderr)
            self.assertEqual(sorted(p.name for p in root.iterdir()), [preload.name, script.name])

    def test_available_dependency_preflight_needs_no_input(self):
        self.preflight(True)

    def test_missing_dependency_preflight_fails_without_output(self):
        self.preflight(False)

    def test_generation_with_existing_docx_dependency(self):
        with tempfile.TemporaryDirectory(prefix='course-generation-') as temp:
            root = Path(temp)
            check = subprocess.run(['node', str(SCRIPT), '--check-deps'], cwd=root,
                                   capture_output=True, text=True, encoding='utf-8')
            if check.returncode:
                self.skipTest('Existing docx dependency unavailable: ' + check.stderr)
            image = root / 'evidence.png'
            image.write_bytes(base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aBZkAAAAASUVORK5CYII='))
            markdown, output = root / 'source.md', root / 'generated.docx'
            markdown.write_text('# Fixture report\n\nBody text.\n\n| Field | Value |\n| --- | --- |\n| A | 1 |\n\n![Evidence](evidence.png)\n', encoding='utf-8')
            result = subprocess.run(['node', str(SCRIPT), str(markdown), str(output), '--img-width', '120'],
                                    cwd=root, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(output) as archive:
                self.assertIn(b'Fixture report', archive.read('word/document.xml'))
                self.assertIn(image.read_bytes(), [archive.read(n) for n in archive.namelist()
                                                   if n.startswith('word/media/') and not n.endswith('/')])
            verification = subprocess.run([sys.executable, '-B', str(SCRIPT.with_name('verify_media.py')),
                                           str(output), str(image)], cwd=root, capture_output=True, text=True)
            self.assertEqual(verification.returncode, 0, verification.stderr)
            self.assertIn('missing=0', verification.stdout)


if __name__ == '__main__':
    unittest.main()
