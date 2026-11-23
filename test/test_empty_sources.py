"""Source text must survive even when it contains no semantic statements."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import flint
from flint.lexer import Lexer
from flint.formatting.rules import select_rules
from flint.formatting.runner import check_spacing
from flint.formatting.spacing import render
from flint.tools.format import format_statements


class TestEmptySources(unittest.TestCase):
    def test_statementless_sources_survive_parsing_and_formatting(self):
        cases = (
            '',
            '   \t',
            '\n \t\n\n',
            '! comment without final endline',
            '! first\n\n  ! second\n',
            '#define UNUSED 1\n',
            '#if 0\nprogram inactive\nend program\n#endif\n',
        )
        for ending in ('\n', '\r\n', '\r'):
            for case in cases:
                text = case.replace('\n', ending)
                with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                    lexer = Lexer(io.StringIO(text, newline=''))
                    leading = lexer.prior_tail
                    statements = list(lexer)
                    self.assertEqual(statements, [])
                    self.assertEqual(render(statements, leading_liminals=leading), text)
                    path = Path(directory) / 'empty.f90'
                    path.write_bytes(text.encode())
                    project = flint.parse(str(path))
                    source = project.sources[0]
                    self.assertEqual(source.units, [])
                    self.assertEqual(source.statements, [])
                    self.assertEqual(source.source_text(), text)
                    self.assertEqual(
                        [''.join(map(str, line)) for line in source.lines], text.splitlines())
                    self.assertEqual(source.source_text(), text)
                    self.assertEqual(list(check_spacing(project, select_rules().values())), [])
                    with contextlib.redirect_stdout(io.StringIO()):
                        status = format_statements([str(path)], write=True)
                    self.assertEqual(status, 0)
                    self.assertEqual(path.read_bytes(), text.encode())

    def test_leading_comments_emitted_once_for_normal_source(self):
        text = '! heading\nprogram sample\nend program\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.f90'
            path.write_bytes(text.encode())
            source = flint.parse(str(path)).sources[0]
            self.assertIs(source.leading_liminals, source.statements[0][0].head)
            self.assertEqual(source.source_text(), text)
            self.assertEqual(render(source.statements, leading_liminals=source.leading_liminals), text)
