"""Integration checks for named spacing rules and CLI output modes."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import flint
from flint.cli import parse
from flint.formatting.rules import RULES, select_rules
from flint.formatting.runner import check_spacing


SOURCE = '''subroutine demo(a, b, x)
  real :: a, b, x
  x=a+b
  call f(a,b)
end subroutine demo
'''
FORMATTED = SOURCE.replace('x=a+b', 'x = a + b').replace('f(a,b)', 'f(a, b)')


class FormatCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'demo.F90'
        self.path.write_text(SOURCE)

    def cli(self, *args):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['flint', 'format', *map(str, args)]):
            with contextlib.redirect_stdout(output):
                status = parse()
        return status, output.getvalue()

    def test_default_reports_names_and_parses_once(self):
        with patch.object(flint, 'parse', wraps=flint.parse) as parsing:
            status, output = self.cli(self.path)
        self.assertEqual(status, 1)
        parsing.assert_called_once()
        for name in RULES:
            self.assertIn(f': {name}: ', output)
        self.assertIn(f'{self.path}:3:', output)
        self.assertEqual(self.path.read_text(), SOURCE)

    def test_diff_write_and_idempotence(self):
        status, output = self.cli(self.path, '--diff')
        self.assertEqual(status, 1)
        self.assertIn('+  x = a + b', output)
        self.assertEqual(self.path.read_text(), SOURCE)
        status, output = self.cli(self.path, '--diff', '--write')
        self.assertEqual(status, 0)
        self.assertIn('+  call f(a, b)', output)
        self.assertEqual(self.path.read_text(), FORMATTED)
        self.assertEqual(self.cli(self.path), (0, ''))
        self.assertEqual(self.cli(self.path, '--write'), (0, ''))

    def test_selectors(self):
        status, output = self.cli(
            self.path, '--only', 'assignment-spacing,operator-spacing',
            '--only', 'callable-comma-spacing', '--skip', 'operator-spacing',
            '--skip', 'callable-comma-spacing', '--write',
        )
        self.assertEqual(status, 0)
        self.assertEqual(self.path.read_text(), SOURCE.replace('x=a+b', 'x = a+b'))

    def test_list_and_invalid_arguments_do_not_parse(self):
        with patch.object(flint, 'parse') as parsing:
            self.assertEqual(self.cli('--list-rules'), (0, '\n'.join(RULES) + '\n'))
            for args in [(), (self.path, '--only', 'unknown'),
                         (self.path, '--skip', 'unknown')]:
                with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        self.cli(*args)
                    self.assertEqual(error.exception.code, 2)
            parsing.assert_not_called()

    def test_options(self):
        source = SOURCE.replace('x=a+b', 'x  =  a  +  b').replace(
            '  call f(a,b)', '  do i = 1, 2\n    call f(a,b)\n  enddo')
        self.path.write_text(source)
        self.cli(self.path, '--write', '--strict', '--do-controls',
                 '--exclude-function', 'F')
        self.assertEqual(self.path.read_text(), source.replace(
            'x  =  a  +  b', 'x = a + b').replace('i = 1, 2', 'i=1,2'))

    def test_python_rules_reuse_project_without_writing(self):
        project = flint.parse(str(self.path))
        results = list(check_spacing(project, select_rules().values()))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].formatted, FORMATTED)
        self.assertEqual(self.path.read_text(), SOURCE)
        self.assertEqual(list(check_spacing(project, select_rules(only=[]).values())), [])

    def test_module_exit_status(self):
        result = subprocess.run(
            [sys.executable, '-m', 'flint', 'format', str(self.path)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('assignment-spacing', result.stdout)
