"""Q exponents are an explicitly controllable language extension."""
import io
from pathlib import Path
import tempfile
import unittest

import flint
from flint.lexer import Lexer
from flint.scanner import Scanner
from flint.token import Token, TokenKind
from flint.tools.format import format_statements


class QExponentTests(unittest.TestCase):
    def test_q_literals_and_standard_rejection(self):
        for literal in ('1.23q-01', '1.5Q2', '1Q+2', '.5q0', '1.q0'):
            with self.subTest(literal=literal):
                self.assertEqual(Scanner(standard=False).parse(literal + '\n'),
                                 [literal, '\n'])
                with self.assertRaisesRegex(ValueError, 'Q exponent.*nonstandard'):
                    Scanner().parse(literal + '\n')
                self.assertEqual(Token(literal).kind, TokenKind.REAL)
                text = 'x = ' + literal + '\n'
                self.assertEqual(next(Lexer(io.StringIO(text), standard=False)).source_text(), text)
                with self.assertRaisesRegex(ValueError, 'Q exponent.*nonstandard'):
                    list(Lexer(io.StringIO(text)))
                with self.assertRaisesRegex(ValueError, 'Q exponent.*nonstandard'):
                    list(Lexer(io.StringIO(text), standard=True))

    def test_standard_literals_names_strings_and_operators(self):
        text = 'x = 1.e2 + 1D-2 + 1.0_quad + 1_quad\n'
        text += 'if (x.eq.q) print *, "1.0q0", 4_"Q"\n'
        statements = list(Lexer(io.StringIO(text), standard=True))
        self.assertEqual(len(statements), 2)
        self.assertEqual(statements[0][2], '1.e2')
        self.assertTrue(statements[1][-1].is_string)

    def test_split_exponent(self):
        text = 'x = 1.23q-&\n&01\n'
        stmt = next(Lexer(io.StringIO(text), standard=False))
        self.assertEqual(stmt[-1], '1.23q-01')
        self.assertEqual(stmt.source_text(), text)
        with self.assertRaisesRegex(ValueError, 'Q exponent'):
            list(Lexer(io.StringIO(text), standard=True))

    def test_api_includes_macros_and_formatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'test.f90'
            header = root / 'value.h'
            header.write_text('#define VALUE 1.23q-01\n', encoding='utf-8')
            text = '#include "value.h"\nprogram test\nx=VALUE\nend program\n'
            path.write_text(text, encoding='utf-8', newline='')
            project = flint.parse(str(path), includes=[tmp], standard=False)
            self.assertEqual(project.sources[0].source_text(), text)
            with self.assertRaisesRegex(ValueError, 'Q exponent'):
                flint.parse(str(path), includes=[tmp])
            with self.assertRaisesRegex(ValueError, 'Q exponent'):
                format_statements([str(path)], includes=[tmp], write=True)
            self.assertEqual(path.read_text(), text)
