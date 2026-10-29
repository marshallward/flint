import io
import sys
import unittest

sys.path.insert(1, '../')
from flint.lexer import Lexer
from flint.token import Token, TokenKind, classify_lexeme


def lex_one(line):
    return next(Lexer(io.StringIO(line)))


class TestToken(unittest.TestCase):

    def test_lexeme_classification_cache_is_bounded(self):
        classify_lexeme.cache_clear()
        self.addCleanup(classify_lexeme.cache_clear)
        self.assertEqual(classify_lexeme('.AND.'), TokenKind.LOGICAL_OPERATOR)
        self.assertEqual(classify_lexeme('.and.'), TokenKind.LOGICAL_OPERATOR)
        before = classify_lexeme.cache_info().hits
        self.assertEqual(classify_lexeme('.AND.'), TokenKind.LOGICAL_OPERATOR)
        self.assertEqual(classify_lexeme.cache_info().hits, before + 1)
        for index in range(4200):
            self.assertEqual(classify_lexeme(f'field_{index}'), TokenKind.NAME)
        info = classify_lexeme.cache_info()
        self.assertEqual(info.maxsize, 4096)
        self.assertLessEqual(info.currsize, info.maxsize)

    def test_cached_classification_does_not_share_token_state(self):
        first = Token('field')
        second = Token('field')
        first.tail.append(' ')
        first.syntax_role = 'assignment'
        first.operator_role = 'binary_operator'
        self.assertEqual(second.tail, [])
        self.assertIsNone(second.syntax_role)
        self.assertIsNone(second.operator_role)

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
