import io
import unittest
from pathlib import Path

from flint.lexer import Lexer
from flint.formatting.assignment import format_statements


def format_source(text, **options):
    return format_statements(Path('test.F90'), list(Lexer(io.StringIO(text))), **options)


class TestAssignmentSpacing(unittest.TestCase):
    def test_implied_do_spacing_is_preserved(self):
        source = 'dimids(:) = [(axes(i)%dimid, i = 1, size(axes))]\n'
        for strict in (False, True):
            with self.subTest(strict=strict):
                formatted, changes = format_source(source, strict=strict)
                self.assertEqual(formatted, source)
                self.assertEqual(changes, [])

    def test_outer_assignment_and_inner_named_arguments_are_checked(self):
        source = 'x=[(f(a = i), i = 1,n)]\n'
        formatted, changes = format_source(source)
        self.assertEqual(formatted, 'x = [(f(a=i), i = 1,n)]\n')
        self.assertEqual(len(changes), 1)

    def test_optional_do_control_policy(self):
        source = 'x = [(i, i = 1, n)]\n'
        formatted, _ = format_source(source, do_controls=True)
        self.assertEqual(formatted, 'x = [(i, i=1, n)]\n')

    def test_nested_legacy_and_continued_implied_do(self):
        examples = [
            'x = (/ ((i*j, i = 1,n), j = 1,m) /)\n',
            'x = [0, (i, &\n  & i = 1,n)]\n',
            'write(*,*) (a(i), i = 1, n)\n',
        ]
        for source in examples:
            with self.subTest(source=source):
                formatted, changes = format_source(source)
                self.assertEqual(formatted, source)
                self.assertEqual(changes, [])


if __name__ == '__main__':
    unittest.main()
