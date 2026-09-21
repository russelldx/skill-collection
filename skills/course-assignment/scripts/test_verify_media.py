"""Generated ZIP/DOCX fixtures only; no Office application required."""
from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).with_name('verify_media.py')


class MediaVerificationTests(unittest.TestCase):
    def run_fixture(self, entries, expected_code, expected_missing):
        self.assertTrue(SCRIPT.is_file(), 'Reusable byte-hash verifier is missing')
        with tempfile.TemporaryDirectory(prefix='course-media-') as temp:
            root = Path(temp)
            image = root / 'source image.png'
            image.write_bytes(b'original evidence bytes')
            other = root / 'second.png'
            other.write_bytes(b'second evidence')
            docx = root / 'fixture.docx'
            with zipfile.ZipFile(docx, 'w') as z:
                z.writestr('word/document.xml', '<document/>')
                for name, value in entries:
                    z.writestr(name, value)
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), str(docx), str(image), str(other)],
                                    cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, expected_code, result.stderr + result.stdout)
            self.assertIn(f'missing={expected_missing}', result.stdout)

    def test_match_uses_embedded_bytes_not_filenames(self):
        self.run_fixture([('word/media/', b''), ('word/media/renamed.png', b'original evidence bytes'),
                          ('word/media/other-name.png', b'second evidence')], 0, 0)

    def test_missing_counts_and_fails(self):
        self.run_fixture([('word/media/renamed.png', b'original evidence bytes')], 1, 1)

    def test_hash_filename_cannot_fake_content_match(self):
        digest = hashlib.sha1(b'original evidence bytes').hexdigest()
        self.run_fixture([('word/media/' + digest, b'wrong image'),
                          ('elsewhere/second.png', b'second evidence')], 1, 2)

    def test_invalid_archive_is_nonzero(self):
        self.assertTrue(SCRIPT.is_file(), 'Reusable byte-hash verifier is missing')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'broken.docx'
            path.write_bytes(b'not a zip')
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), str(path), str(path)],
                                    cwd=temp, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('ERROR', result.stderr)


if __name__ == '__main__':
    unittest.main()
