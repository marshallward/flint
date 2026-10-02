import io
import sys
import unittest

sys.path.insert(1, '../')
from flint.lexer import Lexer
from flint.token import TokenKind


def lex_one(line):
    return next(Lexer(io.StringIO(line)))


class TestToken(unittest.TestCase):

    def test_token_kinds(self):
        stmt = lex_one('x = foo(a=1, b=\'str\')\n')

        self.assertEqual(stmt[0].kind, TokenKind.NAME)
        self.assertEqual(stmt[1].kind, TokenKind.ASSIGNMENT)
        self.assertEqual(stmt[3].kind, TokenKind.DELIMITER)
        self.assertEqual(stmt[6].kind, TokenKind.INTEGER)
        self.assertEqual(stmt[10].kind, TokenKind.STRING)
        self.assertTrue(stmt[1].is_operator)
        self.assertTrue(stmt[3].is_punctuation)
        self.assertTrue(stmt[6].is_number)


if __name__ == '__main__':
    unittest.main()
