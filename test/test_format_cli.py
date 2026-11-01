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
from flint.formatting.rules import ALL_RULES, RULES, select_rules
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
        self.config = Path(self.tmp.name) / 'flint.toml'
        self.config.write_text('[format.indentation]\nwidth = 2\n')

    def cli(self, *args):
        if '--config' not in args:
            args = (*args, '--config', self.config)
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
            self.assertEqual(self.cli('--list-rules'), (0, '\n'.join(ALL_RULES) + '\n'))
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

    def test_indentation_reports_in_all_modes_and_preserves_source(self):
        source = FORMATTED.replace('  x =', ' x =')
        for mode in ((), ('--diff',), ('--write',)):
            with self.subTest(mode=mode):
                self.path.write_text(source)
                status, output = self.cli(self.path, '--only', 'indentation', *mode)
                self.assertEqual(status, 1)
                self.assertIn(':3: indentation: expected 2 spaces, found 1', output)
                self.assertEqual(self.path.read_text(), source)

    def test_custom_indent_width_and_continuations(self):
        source = '''module demo
contains
subroutine work(a)
    logical :: a
    real :: &
        x
    if (a) &
        call task(1, &
            2)
    select case (1)
        case (1)
            call task()
    end select
end subroutine work
end module demo
'''
        self.path.write_text(source)
        config = Path(self.tmp.name) / 'flint.toml'
        config.write_text('[format.indentation]\nwidth = 4\n')
        args = (self.path, '--only', 'indentation', '--config', config)
        self.assertEqual(self.cli(*args), (0, ''))
        status, output = self.cli(*args, '--strict')
        self.assertEqual(status, 1)
        self.assertIn(':6: indentation: continuation: expected at least 12 spaces', output)
        self.assertEqual(output.count('indentation:'), 1)
        self.assertEqual(self.path.read_text(), source)

    def test_combined_write_reports_unfixed_indentation_with_one_parse(self):
        self.path.write_text(SOURCE.replace('  x=', ' x='))
        with patch.object(flint, 'parse', wraps=flint.parse) as parsing:
            status, output = self.cli(self.path, '--write')
        parsing.assert_called_once()
        self.assertEqual(status, 1)
        self.assertIn('indentation:', output)
        self.assertEqual(self.path.read_text(), FORMATTED.replace('  x =', ' x ='))
        self.assertEqual(self.cli(self.path, '--skip', 'indentation'), (0, ''))
