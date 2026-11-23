"""Real-only addition diagnostics and command-line integration."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import flint
from flint.formatting.addition import addition_issues
from flint.tools.format import format_statements


class AdditionParentheses(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'demo.F90'

    def check(self, body, declarations='real :: a, b, c, d, s\ninteger :: i, j, k'):
        self.path.write_text(f'subroutine demo\n{declarations}\n{body}\nend subroutine\n')
        return addition_issues(flint.parse(str(self.path)).sources[0])

    def test_grouping_and_integer_exemption(self):
        for expression, expected in [
            ('a + b + c', 1), ('(a + b + c)', 1),
            ('(a + b) + c', 0), ('a + (b + c)', 0),
            ('a + b + c + d', 1), ('i + j + k', 0),
            ('i + j + a', 1), ('a*b + c/d + s', 1),
            ('a - b - c', 0), ('a*b*c', 0), ('a/b/c', 0),
            ('a + b - c', 0), ('a - b + c', 0),
            ('a - b + c + d', 1), ('i - j + k + 1', 0),
            ('-a + b + c', 1), ('1 + 2 + 3', 0),
            ('1_index + 2_index + 3_index', 0),
            ('1.d0 + 2.0 + 3.0', 1), ('a + unknown + c', 0),
            ('int(a) + int(b) + int(c)', 0),
            ('real(i) + real(j) + real(k)', 1),
        ]:
            with self.subTest(expression=expression):
                self.assertEqual(len(self.check('s = ' + expression)), expected)

    def test_nested_arguments_and_multiple_chains(self):
        issues = self.check('call consume(a+b+c, (a+b+c), i+j+k)')
        self.assertEqual(len(issues), 2)
        self.assertEqual([issue.line_number for issue in issues], [4, 4])

    def test_arrays_and_components(self):
        declarations = '''type :: data
real :: x
integer :: n
end type
type(data) :: obj
real :: a(10), b(10), c(10), s
integer :: i, j, k'''
        self.assertEqual(len(self.check('s = a(i+j+k) + b(i) + c(i)', declarations)), 1)
        self.assertEqual(len(self.check('s = obj%x + obj%x + obj%x', declarations)), 1)
        self.assertEqual(self.check('s = obj%n + obj%n + obj%n', declarations), [])

    def test_complex_and_unknown_calls(self):
        self.assertEqual(self.check('s = a+b+c', 'complex :: a,b,c,s'), [])
        self.assertEqual(self.check('s = f(a)+b+c'), [])

    def test_initializer_and_continuation(self):
        issues = self.check('s = &\n  a + b &\n  + c',
                            'real, parameter :: p = 1. + 2. + 3.\nreal :: a,b,c,s')
        self.assertEqual([issue.line_number for issue in issues], [2, 5])

    def test_host_association_and_shadowing(self):
        self.path.write_text('''module demo
real :: a,b,c,s
contains
subroutine one
s = a+b+c
end subroutine
subroutine two
integer :: a,b,c
s = a+b+c
end subroutine
end module
''')
        issues = addition_issues(flint.parse(str(self.path)).sources[0])
        self.assertEqual([issue.line_number for issue in issues], [5])

    def test_cli_reports_without_rewriting(self):
        self.check('s = a + b + c')
        before = self.path.read_text()
        config = Path(self.tmp.name) / 'flint.toml'
        config.write_text('[format]\nrules = ["real-addition-parentheses"]\n')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = format_statements([str(self.path)], config=config, write=True)
        self.assertEqual(status, 1)
        self.assertIn(f'{self.path}:4: real-addition-parentheses:', output.getvalue())
        self.assertEqual(self.path.read_text(), before)


if __name__ == '__main__':
    unittest.main()
