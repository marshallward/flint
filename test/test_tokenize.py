import sys
import unittest

sys.path.insert(1, '../')
from flint.tokenizer import Tokenizer


class Test(unittest.TestCase):

    def setUp(self):
        self.tokenizer = Tokenizer()

        self.one_word_str = 'abc\n'
        self.one_word = ['abc']

        self.two_word_str = 'abc def\n'
        self.two_word = ['abc', ' ', 'def']

        self.string_str = '\'abc def\'\n'
        self.string = ['\'abc def\'']

        self.string_tok_str = 'abc "def ghi" jkl\n'
        self.string_tok = ['abc', ' ', '"def ghi"', ' ', 'jkl']

        self.string_ampersand_str = 's = "Lennon & McCartney"\n'
        self.string_ampersand = ['s', ' ', '=', ' ', '"Lennon & McCartney"']

        self.escape_delim_str = '\'abc \'\'def\' ghi\n'
        self.escape_delim = ['\'abc \'\'def\'', ' ', 'ghi']

        self.comment_str = 'abc !def ghi\n'
        self.comment = ['abc', ' ', '!def ghi']

        self.defined_op_str = 'abc .and. def\n'
        self.defined_op = ['abc', ' ', '.and.', ' ', 'def']

        self.decimal_str = 'x = .25\n'
        self.decimal = ['x', ' ', '=', ' ', '.25']

        self.float_str = 'x = 2.5e-2\n'
        self.float = ['x', ' ', '=', ' ', '2.5e-2']

        self.numeric_kind_str = 'x = 1.0_r8\n'
        self.numeric_kind = ['x', ' ', '=', ' ', '1.0_r8']

        self.str_continue_str = [
                "s = 'This is a &\n",
                "     single string.'\n"
        ]
        self.str_continue = [
                ['s', ' ', '=', ' ', "'This is a ", '&'],
                ['     ', "single string.'"]
        ]

    def test_one_word(self):
        test_toks = self.tokenizer.parse(self.one_word_str)
        self.assertEqual(test_toks, self.one_word)

    def test_two_word(self):
        test_toks = self.tokenizer.parse(self.two_word_str)
        self.assertEqual(test_toks, self.two_word)

    def test_string(self):
        test_toks = self.tokenizer.parse(self.string_str)
        self.assertEqual(test_toks, self.string)

        test_toks = self.tokenizer.parse(self.string_tok_str)
        self.assertEqual(test_toks, self.string_tok)

    def test_string_ampersand(self):
        test_toks = self.tokenizer.parse(self.string_ampersand_str)
        self.assertEqual(test_toks, self.string_ampersand)

    def test_escape_delim(self):
        test_toks = self.tokenizer.parse(self.escape_delim_str)
        self.assertEqual(test_toks, self.escape_delim)

    def test_comment(self):
        test_toks = self.tokenizer.parse(self.comment_str)
        self.assertEqual(test_toks, self.comment)

    def test_defined_op(self):
        test_toks = self.tokenizer.parse(self.defined_op_str)
        self.assertEqual(test_toks, self.defined_op)

    def test_decimal(self):
        test_toks = self.tokenizer.parse(self.decimal_str)
        self.assertEqual(test_toks, self.decimal)

    def test_float(self):
        test_toks = self.tokenizer.parse(self.float_str)
        self.assertEqual(test_toks, self.float)

    def test_numeric_kind(self):
        test_toks = self.tokenizer.parse(self.numeric_kind_str)
        self.assertEqual(test_toks, self.numeric_kind)

    def test_string_continue(self):
        for (line, toks) in zip(self.str_continue_str, self.str_continue):
            test_toks = self.tokenizer.parse(line)
            self.assertEqual(test_toks, toks)

if __name__ == '__main__':
    unittest.main()
