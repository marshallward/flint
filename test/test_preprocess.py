import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(1, '../')
from flint.lexer import Lexer  # noqa: E402


def statement_codes(source):
    return [
        ''.join(str(token) for token in stmt)
        for stmt in Lexer(io.StringIO(source))
    ]


class TestPreprocess(unittest.TestCase):
    def test_ifdef_false_uses_else_branch(self):
        source = '''#ifdef FOO
x=1
#else
y=2
#endif
z=3
'''

        self.assertEqual(statement_codes(source), ['y=2', 'z=3'])

    def test_ifdef_true_skips_else_branch(self):
        source = '''#define FOO
#ifdef FOO
x=1
#else
y=2
#endif
z=3
'''

        self.assertEqual(statement_codes(source), ['x=1', 'z=3'])

    def test_ifndef_true_uses_first_branch(self):
        source = '''#ifndef FOO
x=1
#else
y=2
#endif
'''

        self.assertEqual(statement_codes(source), ['x=1'])

    def test_if_expression_uses_else_branch(self):
        source = '''#if 0
x=1
#else
y=2
#endif
z=3
'''

        self.assertEqual(statement_codes(source), ['y=2', 'z=3'])

    def test_if_expression_uses_macro_value(self):
        source = '''#define VALUE 2
#if VALUE > 1
x=1
#else
y=2
#endif
'''

        self.assertEqual(statement_codes(source), ['x=1'])

    def test_if_defined_expression(self):
        source = '''#define FOO
#if defined(FOO) && !defined(BAR)
x=1
#else
y=2
#endif
'''

        self.assertEqual(statement_codes(source), ['x=1'])

    def test_elif_uses_first_active_branch(self):
        source = '''#if 0
x=1
#elif 1
y=2
#else
z=3
#endif
w=4
'''

        self.assertEqual(statement_codes(source), ['y=2', 'w=4'])

    def test_inactive_define_is_ignored(self):
        source = '''#if 0
#define FOO
#endif
#ifdef FOO
x=1
#else
y=2
#endif
'''

        self.assertEqual(statement_codes(source), ['y=2'])

    def test_nested_inactive_group_stays_inactive(self):
        source = '''#if 0
#if 1
x=1
#else
y=2
#endif
#else
z=3
#endif
'''

        self.assertEqual(statement_codes(source), ['z=3'])

    def test_include_expansion_is_not_source_visible(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            include = Path(tmpdir) / 'defs.h'
            include.write_text('x=1\n')

            lexer = Lexer(
                io.StringIO('#include "defs.h"\n'),
                include_paths=[tmpdir],
            )
            statement = next(lexer)

        self.assertFalse(statement.source_visible)
        self.assertEqual(statement.source_path, str(include))
        self.assertEqual(statement.source_line_number, 1)
        self.assertIsNone(statement.expansion_path)
        self.assertEqual(statement.expansion_line_number, 1)


if __name__ == '__main__':
    unittest.main()
