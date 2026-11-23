"""A UTF-8 signature is preserved without becoming a Fortran token."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import flint
from flint.lexer import Lexer
from flint.scanner import Scanner
from flint.token import semantic_tokens
from flint.formatting.rules import select_rules
from flint.formatting.runner import check_spacing, report_spacing


class UTF8BOMTests(unittest.TestCase):
    def test_bom_is_a_leading_liminal_only_at_start_of_file(self):
        scanner = Scanner()
        self.assertEqual(scanner.parse('\ufeffprogram test\r\n'),
                         ['\ufeff', 'program', ' ', 'test', '\r\n'])
        # A later marker inside a literal is character data, not a signature.
        self.assertEqual(scanner.parse('print *, "\ufeff"\n'),
                         ['print', ' ', '*', ',', ' ', '"\ufeff"', '\n'])
        with self.assertRaises(KeyError):
            scanner.parse('\ufeffend program\n')

    def test_roundtrip_and_spacing_writes_preserve_bom_and_unicode(self):
        for ending in ('\n', '\r\n', '\r'):
            with self.subTest(ending=ending), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'test.f90'
                text = '\ufeff' + ending.join([
                    '! π and café',
                    'program test',
                    'integer :: x',
                    'x=42',
                    'print *, "λ and \ufeff"',
                    'end program',
                    '',
                ])
                path.write_bytes(text.encode('utf-8'))
                project = flint.parse(str(path))
                source = project.sources[0]
                self.assertEqual(source.source_text(), text)
                self.assertEqual(source.leading_liminals[0], '\ufeff')
                self.assertEqual(source.units[0].name, 'test')
                changes = list(check_spacing(project, select_rules().values()))
                self.assertEqual(len(changes), 1)
                with contextlib.redirect_stdout(io.StringIO()):
                    report_spacing(changes, write=True)
                self.assertEqual(path.read_bytes(), text.replace('x=42', 'x = 42').encode('utf-8'))
                self.assertEqual(list(check_spacing(
                    flint.parse(str(path)), select_rules().values())), [])

    def test_bom_prefixed_directives_are_processed(self):
        for directive, code, expected in (
            ('#define VALUE 42', 'x = VALUE', ['x', '=', '42']),
            ('#if 0', 'ignored = 1\n#endif\nx = 42', ['x', '=', '42']),
        ):
            with self.subTest(directive=directive):
                text = '\ufeff' + directive + '\n' + code + '\n'
                statements = list(Lexer(io.StringIO(text)))
                self.assertEqual(len(statements), 1)
                self.assertEqual([t[:] for t in semantic_tokens(statements[0])], expected)
                self.assertEqual(statements[0].source_text(), text)

    def test_bom_only_and_comment_only_sources(self):
        for text in ('\ufeff', '\ufeff! π\n', '\ufeff\r\n'):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'test.f90'
                path.write_bytes(text.encode('utf-8'))
                project = flint.parse(str(path))
                self.assertEqual(project.sources[0].statements, [])
                self.assertEqual(project.sources[0].source_text(), text)
                self.assertEqual(list(check_spacing(project, select_rules().values())), [])

    def test_bom_prefixed_include_and_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'vars.h').write_bytes('\ufeffinteger :: x !< π\n'.encode('utf-8'))
            path = root / 'test.f90'
            text = '\ufeff#include "vars.h"\nend\n'
            path.write_bytes(text.encode('utf-8'))
            source = flint.parse(str(path), includes=[tmp]).sources[0]
            self.assertEqual(source.source_text(), text)
            declaration = next(s for s in source.statements if s[0] == 'integer')
            self.assertEqual(declaration.origin_statement[0].head[0], '\ufeff')
