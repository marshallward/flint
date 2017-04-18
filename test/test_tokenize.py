import sys
import unittest

sys.path.insert(1, '../')
from flint.tokenize import tokenize


class Test(unittest.TestCase):

    def setUp(self):
        self.one_word_str = 'abc\n'
        self.one_word = ['abc']

        self.two_word_str = 'abc def\n'
        self.two_word = ['abc', ' ', 'def']

        self.string_str = '\'abc def\'\n'
        self.string = ['\'abc def\'']

        self.string_tok_str = 'abc "def ghi" jkl\n'
        self.string_tok = ['abc', ' ', '"def ghi"', ' ', 'jkl']

        self.escape_delim_str = '\'abc \'\'def\' ghi\n'
        self.escape_delim = ['\'abc \'\'def\'', ' ', 'ghi']

        self.comment_str = 'abc !def ghi\n'
        self.comment = ['abc', ' ', '!def ghi']

        # Need several examples here
        self.float_str = 'x = 2.5e-2\n'
        self.float = ['x', ' ', '=', ' ', '2.5e-2']

    def test_one_word(self):
        test_toks, _ = tokenize(self.one_word_str)
        self.assertEqual(test_toks, self.one_word)

    def test_two_word(self):
        test_toks, _ = tokenize(self.two_word_str)
        self.assertEqual(test_toks, self.two_word)

    def test_string(self):
        test_toks, _ = tokenize(self.string_str)
        self.assertEqual(test_toks, self.string)

        test_toks, _ = tokenize(self.string_tok_str)
        self.assertEqual(test_toks, self.string_tok)

    def test_escape_delim(self):
        test_toks, _ = tokenize(self.escape_delim_str)
        self.assertEqual(test_toks, self.escape_delim)

    def test_comment(self):
        test_toks, _ = tokenize(self.comment_str)
        self.assertEqual(test_toks, self.comment)

    def test_float(self):
        test_toks, _ = tokenize(self.float_str)
        self.assertEqual(test_toks, self.float)


if __name__ == '__main__':
    unittest.main()
