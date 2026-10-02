import io
import sys
import unittest

sys.path.insert(1, '../')
from flint.lexer import Lexer


def lex_one(line):
    return next(Lexer(io.StringIO(line)))


class TestStatement(unittest.TestCase):

    def test_unlabeled_statement_metadata(self):
        stmt = lex_one('do k = 1, nz\n')

        self.assertIsNone(stmt.label)
        self.assertEqual(stmt.code_index, 0)
        self.assertEqual(stmt.kind, 'do')
        self.assertIs(stmt.tokens, stmt)
        self.assertEqual(stmt.code_tokens, stmt[:])

    def test_labeled_statement_metadata(self):
        stmt = lex_one('loop: do k = 1, nz\n')

        self.assertEqual(stmt.label, 'loop')
        self.assertEqual(stmt.code_index, 2)
        self.assertEqual(stmt.kind, 'do')
        self.assertEqual(stmt.code_tokens, stmt[2:])

    def test_statement_kinds(self):
        self.assertEqual(lex_one('call f(a=1)\n').kind, 'call')
        self.assertEqual(lex_one('do k = 1, nz\n').kind, 'do')
        self.assertEqual(lex_one('integer :: i=1\n').kind, 'declaration')
        self.assertEqual(lex_one('x = 1\n').kind, 'assignment')
        self.assertEqual(lex_one('target = 1\n').kind, 'assignment')
        self.assertEqual(lex_one('end if\n').kind, 'other')

    def test_statement_queries(self):
        do_stmt = lex_one('do k = 1, nz\n')
        call_stmt = lex_one('call f(a=1)\n')
        assignment = lex_one('x = 1\n')

        self.assertTrue(do_stmt.is_do_statement())
        self.assertFalse(do_stmt.is_call_statement())
        self.assertTrue(call_stmt.is_call_statement())
        self.assertFalse(call_stmt.is_do_statement())
        self.assertFalse(assignment.is_do_statement())
        self.assertFalse(assignment.is_call_statement())

    def test_statement_source_text(self):
        stmt = lex_one('  x = 1\n')

        self.assertEqual(stmt.source_text(), '  x = 1\n')
        self.assertEqual(stmt.source_line(), '  x = 1')
        self.assertEqual(stmt.compact_text(), 'x = 1')


if __name__ == '__main__':
    unittest.main()
