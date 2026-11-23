"""Preserve physical endlines while treating LF, CRLF and CR identically."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import flint
from flint.endlines import is_endline
from flint.scanner import Scanner
from flint.lexer import Lexer
from flint.locations import source_locations
from flint.documentation import declaration_comments
from flint.formatting.rules import select_rules
from flint.formatting.runner import check_spacing, report_spacing
from flint.formatting.spacing import render


class TestEndlines(unittest.TestCase):
    def test_scanner_preserves_single_endline_lexemes(self):
        for ending in ('\n', '\r\n', '\r'):
            with self.subTest(ending=ending):
                scanner = Scanner()
                for line, expected in (
                    ('x = 1', ['x', ' ', '=', ' ', '1', ending]),
                    ('! comment', ['! comment', ending]),
                    ('', [ending]),
                    ('x = "a &', ['x', ' ', '=', ' ', '"a ', '&', ending]),
                    ('! gap', ['! gap', ending]),
                    ('', [ending]),
                    ('  &b"', ['  ', '&', 'b"', ending]),
                ):
                    self.assertEqual(scanner.parse(line + ending), expected)

    def test_roundtrip_locations_and_formatting_preserve_endlines(self):
        lines = [
            '!> Sample', 'program sample', 'implicit none',
            'integer :: x', 'character(20) :: text',
            'text = "a &', '! gap', '', '    &b"',
            'x=1 &', '! keep separator', '; x=x+1',
            'end program sample',
        ]
        for endings in (('\n',), ('\r\n',), ('\r',), ('\r\n', '\r', '\n')):
            for final_endline in (True, False):
                with self.subTest(endings=endings, final_endline=final_endline):
                    text = ''.join(line + (endings[i % len(endings)]
                                   if i < len(lines) - 1 or final_endline else '')
                                   for i, line in enumerate(lines))
                    lexed = list(Lexer(io.StringIO(text, newline='')))
                    self.assertEqual(render(lexed), text)
                    with tempfile.TemporaryDirectory() as directory:
                        path = Path(directory) / 'sample.f90'
                        path.write_bytes(text.encode())
                        project = flint.parse(str(path))
                        source = project.sources[0]
                        self.assertEqual(render(source.statements), text)
                        physical_lines = text.splitlines(keepends=True)
                        offsets = [0]
                        for line in physical_lines:
                            offsets.append(offsets[-1] + len(line))
                        for _, loc in source_locations(source):
                            start = offsets[loc.line - 1] + loc.column - 1
                            end = offsets[loc.end_line - 1] + loc.end_column - 1
                            self.assertEqual(text[start:end], str(loc.token))
                        x = [loc for _, loc in source_locations(source) if loc.token == 'x']
                        self.assertEqual([loc.line for loc in x], [4, 10, 12, 12])
                        changes = list(check_spacing(project, select_rules().values()))
                        self.assertEqual(len(changes), 1)
                        expected = text.replace('x=1', 'x = 1').replace('x=x+1', 'x = x + 1')
                        self.assertEqual(changes[0].formatted, expected)
                        with contextlib.redirect_stdout(io.StringIO()):
                            report_spacing(changes, write=True)
                        self.assertEqual(path.read_bytes(), expected.encode())
                        self.assertEqual(list(check_spacing(
                            flint.parse(str(path)), select_rules().values())), [])

    def test_include_origin_and_documentation_locations(self):
        for ending in ('\n', '\r\n', '\r'):
            with self.subTest(ending=ending), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                header = root / 'vars.h'
                header.write_bytes(ending.join(['!> Value', 'integer :: x', '']).encode())
                path = root / 'sample.f90'
                text = ending.join(['module sample', '#include "vars.h"', 'end module', ''])
                path.write_bytes(text.encode())
                source = flint.parse(str(path), includes=[directory]).sources[0]
                self.assertEqual(render(source.statements), text)
                declaration = next(s for s in source.statements if s[0] == 'integer')
                origin = declaration.origin_statement
                self.assertEqual(origin.line_number, 2)
                self.assertEqual(origin[-1].tail, [ending])
                self.assertTrue(is_endline(origin[-1].tail[0]))
                blocks = declaration_comments(origin)
                self.assertEqual([(b.line, b.comments) for b in blocks], [(1, ('!> Value',))])
