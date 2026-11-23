"""Comments are whitespace in preprocessing conditions, not operators."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import flint
from flint.lexer import cpp_expr_eval, cpp_scanner


class CPPCommentTests(unittest.TestCase):
    def test_comment_tokenization(self):
        self.assertEqual(cpp_scanner.scan('ONE/**/TWO'), (['ONE', 'TWO'], ''))
        self.assertEqual(cpp_scanner.scan('1/* a */+/* b */2'), (['1', '+', '2'], ''))
        self.assertEqual(cpp_scanner.scan('1 // trailing'), (['1'], ''))
        # Quoted operands are outside this expression scanner's grammar;
        # leave them untouched rather than treating their content as comments.
        for text in ('"/* literal */"', "'/'", '"escaped \\" // literal"'):
            self.assertEqual(cpp_scanner.scan(text), ([], text))
        self.assertEqual(cpp_scanner.scan('8 / 2'), (['8', '/', '2'], ''))
        with self.assertRaisesRegex(ValueError, 'CPP block comment'):
            cpp_scanner.scan('1 /* unfinished')

    def test_evaluated_conditions(self):
        for expression in (
            '1 /* taken */ || defined(MISSING) /* absent */',
            'defined/**/(PRESENT)',
            '8 / 2 == 4 /* division stays division */',
            '1 // trailing comment',
        ):
            with self.subTest(expression=expression):
                self.assertTrue(cpp_expr_eval(expression, {'PRESENT': ['PRESENT', '1']}))
        self.assertFalse(cpp_expr_eval('0 /* not taken */'))

    def test_branches_and_source_preservation(self):
        text = (
            'program test\n#define PRESENT 1\n'
            '#if 0 /* false */\n#error inactive\n'
            '#elif 1 /* true */ || defined(MISSING)\n'
            'integer :: x\n#else\n#error inactive\n#endif\n'
            '#ifdef PRESENT /* comment */\nx = 42\n#endif\n'
            '#ifndef MISSING /* comment */\nprint *, x\n#endif\n'
            'end program\n'
        )
        for ending in ('\n', '\r\n', '\r'):
            with self.subTest(ending=ending), tempfile.TemporaryDirectory() as tmp:
                original = text.replace('\n', ending)
                path = Path(tmp) / 'test.f90'
                path.write_bytes(original.encode('utf-8'))
                diagnostics = io.StringIO()
                with contextlib.redirect_stderr(diagnostics):
                    source = flint.parse(str(path)).sources[0]
                self.assertEqual(diagnostics.getvalue(), '')
                self.assertEqual(source.source_text(), original)
                self.assertEqual([v.name for v in source.units[0].variables], ['x'])
                self.assertTrue(any(s.code_tokens == ['x', '=', '42']
                                    for s in source.statements))
