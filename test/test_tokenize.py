import sys
import unittest

sys.path.insert(1, '../')
from flint.tokenize import tokenize

class Test(unittest.TestCase):

    # TODO
    def setUp(self):
        self.one_word_str = 'abc\n'
        self.one_word = ['abc']

        self.two_word_str = 'abc def\n'
        self.two_word = ['abc', ' ', 'def']

        self.string_str = '\'abc def\'\n'
        self.string = ['\'abc def\'']

        self.comment_str = 'abc !def ghi\n'
        self.comment = ['abc', ' ', '!def ghi']

    def test_one_word(self):
        test_toks = tokenize(self.one_word_str)
        self.assertEqual(test_toks, self.one_word)

    def test_two_word(self):
        test_toks = tokenize(self.two_word_str)
        self.assertEqual(test_toks, self.two_word)

    def test_string(self):
        test_toks = tokenize(self.string_str)
        self.assertEqual(test_toks, self.string)

    def test_comment(self):
        test_toks = tokenize(self.comment_str)
        self.assertEqual(test_toks, self.comment)


if __name__ == '__main__':
    unittest.main()
