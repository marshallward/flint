"""CPP null directives are ignored semantically and retained as source."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import flint
from flint.lexer import Lexer


class NullDirectiveTests(unittest.TestCase):
    def test_null_directives_roundtrip(self):
        for directive in ('#', '#  \t', '# /* comment */',
                          '#/**/ /* another */', '# // comment'):
            for ending in ('\n', '\r\n', '\r'):
                with self.subTest(directive=directive, ending=ending):
                    with tempfile.TemporaryDirectory() as tmp:
                        path = Path(tmp) / 'test.f90'
                        text = ending.join(('program test', directive,
                                            'integer :: x', 'x = 42',
                                            'end program', ''))
                        path.write_bytes(text.encode('utf-8'))
                        diagnostics = io.StringIO()
                        with contextlib.redirect_stderr(diagnostics):
                            source = flint.parse(str(path)).sources[0]
                        self.assertEqual(diagnostics.getvalue(), '')
                        self.assertEqual(source.source_text(), text)
                        self.assertEqual(source.units[0].name, 'test')

    def test_null_only_at_eof(self):
        for text in ('#', '# /* comment */'):
            diagnostics = io.StringIO()
            with contextlib.redirect_stderr(diagnostics):
                lexer = Lexer(io.StringIO(text))
                self.assertEqual(list(lexer), [])
            self.assertEqual(''.join(lexer.prior_tail), text)
            self.assertEqual(diagnostics.getvalue(), '')

    def test_non_null_directives_are_not_silently_ignored(self):
        for text in ('# blablab\n', '# /* comment */ blablab\n', '# /* unclosed\n'):
            diagnostics = io.StringIO()
            with contextlib.redirect_stderr(diagnostics):
                list(Lexer(io.StringIO(text)))
            self.assertIn('unsupported preprocess directive', diagnostics.getvalue())
