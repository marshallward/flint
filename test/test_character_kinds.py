"""Kind-prefixed character literals remain single, case-preserving tokens."""
import io
import unittest

from flint.lexer import Lexer
from flint.scanner import Scanner
from flint.token import Token


class CharacterKindTests(unittest.TestCase):
    def test_kind_prefixes_and_escaped_delimiters(self):
        for prefix in ('1', '4', 'CK', 'char_kind'):
            for literal in ('"Abπ"', "'It''s Mixed'", '"Say ""Hi"""'):
                with self.subTest(prefix=prefix, literal=literal):
                    value = prefix + '_' + literal
                    self.assertEqual(Scanner().parse(value + '\n'), [value, '\n'])
                    token = Token(value)
                    self.assertTrue(token.is_string)
                    self.assertEqual(token[:], value)
                    text = 'x = ' + value + '\n'
                    stmt = next(Lexer(io.StringIO(text)))
                    self.assertEqual(stmt[-1][:], value)
                    self.assertEqual(stmt.source_text(), text)

    def test_continued_literals_and_prefixes(self):
        for prefix in ('4', 'CK'):
            for ending in ('\n', '\r\n', '\r'):
                for body in (
                    prefix + '_"Ab&\n! comment\n&Cd&\n&Ef"',
                    prefix + '_&\n&"AbCdEf"',
                ):
                    with self.subTest(prefix=prefix, ending=ending, body=body):
                        text = ('x = ' + body + '\n').replace('\n', ending)
                        stmt = next(Lexer(io.StringIO(text, newline='')))
                        self.assertEqual(stmt[-1][:], prefix + '_"AbCdEf"')
                        self.assertTrue(stmt[-1].is_string)
                        self.assertEqual(stmt.source_text(), text)

    def test_existing_names_and_numeric_kinds(self):
        for value in ('some_name', 'name_', 'a__b', '42_4', '1.0_real_kind'):
            with self.subTest(value=value):
                self.assertEqual(Scanner().parse(value + '\n'), [value, '\n'])
                self.assertFalse(Token(value).is_string)
