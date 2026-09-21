"""Isolated regression tests; no LibreOffice or user macros are executed."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.parse import unquote, urlparse

from openpyxl import Workbook
import recalc


class RecalcIsolationTests(unittest.TestCase):
    def exercise(self, system="Linux", failure=None, marker=True):
        with tempfile.TemporaryDirectory(prefix="recalc-test-") as temp:
            root = Path(temp)
            source = root / 'book with spaces.xlsx'
            wb = Workbook()
            wb.active['A1'] = '=1+1'
            wb.save(source)
            wb.close()
            user_module = root / 'real-user' / 'Module1.xba'
            user_module.parent.mkdir()
            user_module.write_text('USER MACROS - DO NOT CHANGE', encoding='utf-8')
            calls, profiles = [], []

            def inspect(cmd):
                calls.append(cmd)
                options = [a for a in cmd if a.startswith('-env:UserInstallation=')]
                if not options:  # Let the old implementation fail the assertions safely.
                    return
                self.assertEqual(len(options), 1)
                parsed = urlparse(options[0].split('=', 1)[1])
                path = unquote(parsed.path)
                if os.name == 'nt':
                    path = path.lstrip('/')
                profile = Path(path)
                profiles.append(profile)
                self.assertTrue(profile.is_dir())
                self.assertNotEqual(profile, user_module.parent)
                module = profile / 'user/basic/Standard/Module1.xba'
                text = module.read_text(encoding='utf-8')
                self.assertIn('MacroExecutionMode', text)
                self.assertIn('Value = 0', text)
                self.assertIn(source.as_uri(), text)
                for relative in ('user/basic/script.xlc', 'user/basic/Standard/script.xlb'):
                    self.assertTrue((profile / relative).is_file())
                if marker and not failure:
                    (profile / 'recalculated.ok').write_text('done', encoding='utf-8')

            def old_run(cmd, **kwargs):
                inspect(cmd)
                return subprocess.CompletedProcess(cmd, 124 if failure else 0, '', '')

            process = Mock(pid=12345, returncode=1 if failure == 'exit' else 0)
            process.communicate.side_effect = (
                [subprocess.TimeoutExpired('soffice', 2), ('', '')]
                if failure == 'timeout' else None
            )
            if failure != 'timeout':
                process.communicate.return_value = ('', 'failed' if failure else '')

            def popen(cmd, **kwargs):
                inspect(cmd)
                self.assertTrue(kwargs['start_new_session'])
                if failure == 'spawn':
                    raise FileNotFoundError('soffice unavailable')
                return process

            with patch.object(recalc.platform, 'system', return_value=system), \
                 patch.object(recalc.os.path, 'expanduser', return_value=str(user_module.parent)), \
                 patch.object(recalc, 'get_soffice_env', return_value=os.environ.copy()), \
                 patch.object(recalc.subprocess, 'run', side_effect=old_run), \
                 patch.object(recalc.subprocess, 'Popen', side_effect=popen), \
                 patch.object(recalc.signal, 'SIGKILL', 9, create=True), \
                 patch.object(recalc.os, 'killpg', create=True) as killpg:
                result = recalc.recalc(source, timeout=2)
            self.assertEqual(user_module.read_text(encoding='utf-8'), 'USER MACROS - DO NOT CHANGE')
            if system == 'Windows':
                self.assertIn('disabled', result.get('error', '').lower())
                self.assertEqual(calls, [])
            else:
                self.assertTrue(calls)
                self.assertTrue(all(any(a.startswith('-env:UserInstallation=file:') for a in c) for c in calls))
                self.assertTrue(profiles)
                self.assertTrue(all(not p.exists() for p in profiles))
                self.assertEqual('error' in result, bool(failure or not marker), result)
                if failure == 'timeout':
                    killpg.assert_called_once()
            return result

    def test_linux_isolation_and_cleanup(self):
        self.exercise()

    def test_macos_isolation_and_cleanup(self):
        self.exercise('Darwin')

    def test_windows_fails_closed_without_touching_profile(self):
        self.exercise('Windows')

    def test_failures_clean_profile_and_do_not_report_success(self):
        for failure in ('spawn', 'exit', 'timeout'):
            with self.subTest(failure=failure):
                self.exercise(failure=failure)

    def test_exit_zero_without_macro_completion_is_not_success(self):
        self.exercise(marker=False)

    def test_legacy_no_argument_setup_cannot_touch_user_profile(self):
        with patch.object(recalc.os.path, 'expanduser', side_effect=AssertionError('user profile access')):
            with self.assertRaises(TypeError):
                recalc.setup_libreoffice_macro()

    def test_setup_write_failure_cleans_temporary_profile(self):
        with tempfile.TemporaryDirectory(prefix='recalc-parent-') as temp:
            real_temporary_directory = tempfile.TemporaryDirectory
            with patch.object(recalc.tempfile, 'TemporaryDirectory',
                              side_effect=lambda **kw: real_temporary_directory(dir=temp, **kw)), \
                 patch.object(Path, 'write_text', side_effect=OSError('fixture disk full')):
                with self.assertRaises(OSError):
                    with recalc.setup_libreoffice_macro(Path(temp) / 'workbook.xlsx'):
                        self.fail('setup failure must not yield a usable profile')
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_cli_errors_are_nonzero_without_running_libreoffice(self):
        script = Path(recalc.__file__).resolve()
        with tempfile.TemporaryDirectory(prefix='recalc-cli-') as temp:
            path = Path(temp) / 'missing.xlsx'
            result = subprocess.run([sys.executable, '-B', str(script), str(path)],
                                    cwd=temp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn('error', result.stdout)


if __name__ == '__main__':
    unittest.main()
