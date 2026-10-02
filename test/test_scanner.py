import sys
import unittest

sys.path.insert(1, '../')
from flint.scanner import Scanner


class TestScanner(unittest.TestCase):

    def setUp(self):
        self.scanner = Scanner()

    def assert_scan(self, line, tokens):
        self.assertEqual(self.scanner.parse(line), tokens)

    def assert_cases(self, cases):
        for line, tokens in cases:
            with self.subTest(line=line):
                self.assert_scan(line, tokens)

    def test_names_and_whitespace(self):
        self.assert_cases([
            ('abc\n', ['abc', '\n']),
            ('abc def\n', ['abc', ' ', 'def', '\n']),
            ('abc\tdef\n', ['abc', '\t', 'def', '\n']),
            ('_cpp_name value\n', ['_cpp_name', ' ', 'value', '\n']),
        ])

    def test_string(self):
        self.assert_cases([
            ("'abc def'\n", ["'abc def'", '\n']),
            (
                'abc "def ghi" jkl\n',
                ['abc', ' ', '"def ghi"', ' ', 'jkl', '\n'],
            ),
            (
                's = "Lennon & McCartney"\n',
                ['s', ' ', '=', ' ', '"Lennon & McCartney"', '\n'],
            ),
            (
                'x = "a ""quote"""\n',
                ['x', ' ', '=', ' ', '"a ""quote"""', '\n'],
            ),
            (
                "x = 'a ''quote'''\n",
                ['x', ' ', '=', ' ', "'a ''quote'''", '\n'],
            ),
            (
                "'abc ''def' ghi\n",
                ["'abc ''def'", ' ', 'ghi', '\n'],
            ),
        ])

    def test_comments_and_preprocessor_lines(self):
        self.assert_cases([
            ('abc !def ghi\n', ['abc', ' ', '!def ghi', '\n']),
            ('! whole line\n', ['! whole line', '\n']),
            ('#define FOO 1\n', ['#define FOO 1', '\n']),
            ('#include "foo.h"\n', ['#include "foo.h"', '\n']),
        ])

    def test_numeric_literals(self):
        self.assert_cases([
            ('x = .25\n', ['x', ' ', '=', ' ', '.25', '\n']),
            ('x = 2.5e-2\n', ['x', ' ', '=', ' ', '2.5e-2', '\n']),
            ('x = 1.0e+3\n', ['x', ' ', '=', ' ', '1.0e+3', '\n']),
            ('x = 1d-3\n', ['x', ' ', '=', ' ', '1d-3', '\n']),
            ('x = 10_8\n', ['x', ' ', '=', ' ', '10_8', '\n']),
            ('x = 1.0_8\n', ['x', ' ', '=', ' ', '1.0_8', '\n']),
            ('x = 1.0_r8\n', ['x', ' ', '=', ' ', '1.0_r8', '\n']),
            ('x = -1.0\n', ['x', ' ', '=', ' ', '-', '1.0', '\n']),
            ('x = +inf\n', ['x', ' ', '=', ' ', '+', 'inf', '\n']),
        ])

    def test_operators_and_punctuation(self):
        self.assert_cases([
            ('abc .and. def\n', ['abc', ' ', '.and.', ' ', 'def', '\n']),
            ('x = .true. .and. .not. y\n', [
                'x', ' ', '=', ' ', '.true.', ' ', '.and.', ' ', '.not.',
                ' ', 'y', '\n',
            ]),
            ('x=1;y=2\n', ['x', '=', '1', ';', 'y', '=', '2', '\n']),
            ('a=>b\n', ['a', '=>', 'b', '\n']),
            ('a==b; c/=d; e<=f; g>=h\n', [
                'a', '==', 'b', ';', ' ', 'c', '/=', 'd', ';', ' ',
                'e', '<=', 'f', ';', ' ', 'g', '>=', 'h', '\n',
            ]),
            ('x = a**2 + b//c\n', [
                'x', ' ', '=', ' ', 'a', '**', '2', ' ', '+', ' ', 'b',
                '//', 'c', '\n',
            ]),
            ('x = [1, 2]\n', [
                'x', ' ', '=', ' ', '[', '1', ',', ' ', '2', ']', '\n',
            ]),
            ('call f(a=1,b = 2)\n', [
                'call', ' ', 'f', '(', 'a', '=', '1', ',', 'b', ' ', '=',
                ' ', '2', ')', '\n',
            ]),
            ('type(foo) :: x\n', [
                'type', '(', 'foo', ')', ' ', '::', ' ', 'x', '\n',
            ]),
            ('x = a%b%c\n', [
                'x', ' ', '=', ' ', 'a', '%', 'b', '%', 'c', '\n',
            ]),
        ])

    def test_numeric_followed_by_keyword_operator(self):
        self.assert_scan('x = 1.and.y\n', ['x', ' ', '=', ' ', '1', '.and.', 'y', '\n'])

    def test_string_continue(self):
        self.assert_scan(
            "s = 'This is a &\n",
            ['s', ' ', '=', ' ', "'This is a ", '&', '\n'],
        )
        self.assert_scan(
            "     single string.'\n",
            ['     ', "single string.'", '\n'],
        )

    def test_statement_continuation(self):
        self.assert_cases([
            ('x = a &\n', ['x', ' ', '=', ' ', 'a', ' ', '&', '\n']),
            ('& + b\n', ['&', ' ', '+', ' ', 'b', '\n']),
        ])

    def test_unicode_string(self):
        self.assert_scan('x = "alpha α"\n', ['x', ' ', '=', ' ', '"alpha α"', '\n'])

    def test_unicode_comment(self):
        self.assert_scan('x = 1 ! alpha α\n', ['x', ' ', '=', ' ', '1', ' ', '! alpha α', '\n'])
        self.assert_scan('! α comment\n', ['! α comment', '\n'])

    def test_unicode_continued_string(self):
        self.assert_scan("x = 'alpha &\n", ['x', ' ', '=', ' ', "'alpha ", '&', '\n'])
        self.assert_scan("     β gamma'\n", ['     ', "β gamma'", '\n'])

    def test_prior_delim_alias(self):
        self.scanner.prior_delim = 'str_a'
        self.assertEqual(self.scanner.delim, 'str_a')

        tokens = self.scanner.parse("     continued'\n")
        self.assertEqual(tokens, ['     ', "continued'", '\n'])
        self.assertIsNone(self.scanner.prior_delim)

    def test_unicode_outside_string_fails(self):
        with self.assertRaises(KeyError):
            self.scanner.parse('x = café\n')

    def test_incomplete_array_constructor_start(self):
        self.assert_scan('x = (/\n', ['x', ' ', '=', ' ', '(/', '\n'])
        self.assert_scan('x = (/ \n', ['x', ' ', '=', ' ', '(/', ' ', '\n'])

    def test_lparen_slash_ambiguity(self):
        self.assert_cases([
            ('x = (/1, 2/)\n', [
                'x', ' ', '=', ' ', '(/', '1', ',', ' ', '2', '/)', '\n',
            ]),
            ('x = ( / 1, 2 / )\n', [
                'x', ' ', '=', ' ', '(', ' ', '/', ' ', '1', ',', ' ',
                '2', ' ', '/', ' ', ')', '\n',
            ]),
            ('x = (/=\n', ['x', ' ', '=', ' ', '(', '/=', '\n']),
            ('x = operator(/)(a, b)\n', [
                'x', ' ', '=', ' ', 'operator', '(', '/', ')', '(', 'a',
                ',', ' ', 'b', ')', '\n',
            ]),
        ])


if __name__ == '__main__':
    unittest.main()
