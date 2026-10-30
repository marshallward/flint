import copy
import io
import pickle
import sys
import unittest

sys.path.insert(1, '../')
from flint.lexer import Lexer
from flint.token import PToken, Token, TokenKind, classify_lexeme, _token_from_lexeme


def lex_one(line):
    return next(Lexer(io.StringIO(line)))


class TestToken(unittest.TestCase):

    def test_normalized_comparisons_and_hashing(self):
        token = Token('Field')
        self.assertEqual(token, 'field')
        self.assertEqual('field', token)
        self.assertEqual(token, Token('FIELD'))
        self.assertFalse(token != Token('FIELD'))
        self.assertNotEqual(token, 'FIELD')
        self.assertNotEqual('FIELD', token)
        self.assertNotEqual(token, None)
        self.assertEqual(hash(token), hash('field'))
        self.assertEqual({token: 42}['field'], 42)
        self.assertEqual({'field': 42}[token], 42)
        self.assertEqual(len({token, Token('FIELD'), 'field'}), 1)
        self.assertEqual(str(token), 'Field')
        self.assertEqual(token[:], 'field')

    def test_string_literal_case_is_semantic(self):
        for value in ("'MiXeD'", '"MiXeD"'):
            for token in (Token(value), _token_from_lexeme(value, [])):
                self.assertEqual(token, value)
                self.assertNotEqual(token, value.lower())
                self.assertEqual(str(token), value)

    def test_original_spelling_is_preserved(self):
        for value in ('field', '123', '(', '+', "'MiXeD'", ''):
            for token in (Token(value), _token_from_lexeme(value, [])):
                self.assertEqual(token.original, value)
                self.assertEqual(str(token), value)
        for value in ('Field', '.AND.', '1.0E3'):
            for token in (Token(value), _token_from_lexeme(value, [])):
                self.assertEqual(token.original, value)
                self.assertEqual(token, value.lower())

    def test_unchanged_macro_semantics_keep_macro_display(self):
        token = PToken('field', pp=['FIELD_MACRO'])
        self.assertEqual(token.original, 'field')
        self.assertEqual(str(token), 'FIELD_MACRO')
        self.assertEqual(token, 'field')

    def test_preprocessed_token_uses_semantic_hash(self):
        token = PToken('Field', pp=['FIELD_MACRO'])
        self.assertEqual(token, 'field')
        self.assertEqual(hash(token), hash('field'))
        self.assertEqual(str(token), 'FIELD_MACRO')
        self.assertEqual(token.original, 'Field')
        token.pp = ['OTHER_MACRO']
        self.assertEqual({token: 42}['field'], 42)
        self.assertEqual(str(token), 'OTHER_MACRO')

    def test_normalized_tokens_copy_and_pickle(self):
        for token in (Token('Field'), PToken('Field', pp=['MACRO'])):
            token.head = ['  ']
            for duplicate in (copy.copy(token), copy.deepcopy(token),
                              pickle.loads(pickle.dumps(token))):
                self.assertEqual(duplicate, token)
                self.assertEqual(str(duplicate), str(token))
                self.assertEqual(duplicate.original, token.original)
                self.assertEqual(duplicate.head, token.head)

    def test_mixed_case_source_round_trip(self):
        text = 'Field = Func(Arg="MiXeD") ! Comment\n'
        stmt = lex_one(text)
        self.assertEqual(stmt.source_text(), text)
        self.assertEqual(stmt[0], 'field')
        self.assertEqual(stmt[2], 'func')

    def test_lexer_factory_matches_public_constructor(self):
        for value in ('FIELD', '1', '3.14', "'text'", '+', '=', '(', '.AND.', ''):
            with self.subTest(value=value):
                head = ['  ', '! comment', '\n']
                token = _token_from_lexeme(value, head)
                reference = Token(value)
                reference.head = head
                self.assertIs(type(token), Token)
                self.assertEqual(str(token), str(reference))
                self.assertEqual(vars(token), vars(reference))
                self.assertIs(token.head, head)

    def test_lexer_factory_keeps_per_token_state_independent(self):
        first = _token_from_lexeme('x', [])
        second = _token_from_lexeme('x', [])
        first.tail.append(' ')
        first.syntax_role = 'assignment'
        first.operator_role = 'binary_operator'
        self.assertEqual(second.tail, [])
        self.assertIsNone(second.syntax_role)
        self.assertIsNone(second.operator_role)

    def test_lexer_factory_preserves_shared_liminals(self):
        text = 'x = f(a=1) ! comment\n'
        stmt = lex_one(text)
        for left, right in zip(stmt, stmt[1:]):
            self.assertIs(left.tail, right.head)
        self.assertEqual(stmt.source_text(), text)

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
