import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import flint
from flint.lexer import Lexer
from flint.formatting.spacing import (
    LineChange, SpacingEdit, edit_replacements, format_spacing, render,
    spacing_edits,
)
from flint.formatting import assignment as assignments
from flint.formatting import callables as commas
from flint.formatting import operators


def snapshot(statements):
    """Include liminal identities: a checker must not replace lists either."""
    return [
        (str(token), id(token.head), tuple(token.head), id(token.tail),
         tuple(token.tail), token.syntax_role, token.operator_role)
        for statement in statements for token in statement
    ]


class TestSpacingEdits(unittest.TestCase):
    source = '''subroutine demo(a, b, c)
  real :: a, b, c
  a=b+ - c
  call f(a,b = c,     &
         c)
end subroutine demo
'''

    def parse_source(self, directory):
        path = Path(directory) / 'test.F90'
        path.write_text(self.source)
        project = flint.parse(str(path))
        return path, project, project.sources[0]

    def test_all_formatters_leave_shared_parse_unchanged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path, _, source = self.parse_source(tmpdir)
            statements = source.statements
            original = snapshot(statements)
            contexts = commas.statement_contexts(source)
            checks = [
                lambda: assignments.format_statements(path, statements, strict=True),
                lambda: operators.format_statements(path, statements, strict=True),
                lambda: commas.format_statements(path, statements, contexts),
            ]
            results = [check() for check in checks]
            self.assertTrue(all(changes for _, changes in results))
            self.assertEqual(snapshot(statements), original)
            # Repeated checks and reversed execution order see original input.
            self.assertEqual([check() for check in reversed(checks)], results[::-1])
            self.assertEqual(render(statements), self.source)
            self.assertEqual(snapshot(statements), original)

    def test_proposals_from_multiple_checks_can_be_rendered_together(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _, _, source = self.parse_source(tmpdir)
            contexts = commas.statement_contexts(source)
            original = snapshot(source.statements)
            edits = []
            for statement in source.statements:
                edits.extend(assignments.collect_spacing_edits(statement))
                edits.extend(operators.collect_spacing_edits(statement))
                edits.extend(commas.collect_spacing_edits(
                    statement, contexts.get(id(statement), commas.Context(set(), set())),
                    strict=True,
                ))
            self.assertTrue(edits)
            self.assertTrue(all(isinstance(edit, SpacingEdit) for edit in edits))
            self.assertEqual(render(source.statements, edits), '''subroutine demo(a, b, c)
  real :: a, b, c
  a = b + -c
  call f(a, b=c, &
         c)
end subroutine demo
''')
            self.assertEqual(snapshot(source.statements), original)

    def test_reports_diffs_and_writes_do_not_mutate_tokens(self):
        reporters = [
            assignments.run,
            operators.run,
            commas.run,
        ]
        for reporter in reporters:
            for mode in ('report', 'diff', 'write'):
                with self.subTest(reporter=reporter.__name__, mode=mode):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        path, project, source = self.parse_source(tmpdir)
                        original = snapshot(source.statements)
                        output = io.StringIO()
                        with patch.object(flint, 'parse', return_value=project):
                            with contextlib.redirect_stdout(output):
                                status = reporter([path], **{mode: True})
                        self.assertEqual(status, 0 if mode == 'write' else 1)
                        self.assertEqual(snapshot(source.statements), original)
                        if mode == 'write':
                            self.assertNotEqual(path.read_text(), self.source)
                        else:
                            self.assertEqual(path.read_text(), self.source)
                            self.assertIn(str(path), output.getvalue())

    def test_shared_gap_is_edited_once(self):
        statement = next(Lexer(io.StringIO('x=y\n')))
        self.assertIs(statement[0].tail, statement[1].head)
        edits = spacing_edits(statement[0], after=' ')
        edits.extend(spacing_edits(statement[1], before=' '))
        self.assertEqual(len(edit_replacements(edits)), 1)
        self.assertEqual(render([statement], edits), 'x =y\n')
        self.assertEqual(statement.source_text(), 'x=y\n')

    def test_library_diagnostics_do_not_require_a_path(self):
        statements = list(Lexer(io.StringIO('x=y\n')))
        formatted, changes = format_spacing(
            statements, assignments.collect_spacing_edits,
        )
        self.assertEqual(formatted, 'x = y\n')
        self.assertEqual(changes, [LineChange(1, 'x=y')])
        self.assertFalse(hasattr(changes[0], 'path'))
        self.assertEqual(render(statements), 'x=y\n')

    def test_script_attaches_path_to_library_diagnostics(self):
        statements = list(Lexer(io.StringIO('x=y\n')))
        path = Path('example.F90')
        _, changes = assignments.format_statements(path, statements)
        self.assertEqual(changes, [assignments.Change(path, 1, 'x=y')])

    def test_conflicting_proposals_are_rejected(self):
        statement = next(Lexer(io.StringIO('x=y\n')))
        edits = spacing_edits(statement[1], before=' ')
        edits.extend(spacing_edits(statement[1], before='  '))
        with self.assertRaisesRegex(ValueError, 'Conflicting spacing edits'):
            render([statement], edits)

    def test_complex_liminals_are_preserved(self):
        source = 'x = & ! retain comment\n  & y+z\n'
        statement = next(Lexer(io.StringIO(source)))
        edits = assignments.collect_spacing_edits(statement, strict=True)
        self.assertEqual(edits, [])
        self.assertEqual(render([statement], edits), source)


if __name__ == '__main__':
    unittest.main()
