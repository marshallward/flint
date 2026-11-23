"""Assignment syntax must not turn keyword-shaped names into declarations."""
import io
from pathlib import Path
import tempfile
import unittest

import flint
from flint.construct import Construct
from flint.formatting.indentation import block_event, indentation_issues
from flint.formatting.rules import select_rules
from flint.formatting.runner import check_spacing
from flint.lexer import Lexer
from flint.units.unit import Unit


class KeywordNameTests(unittest.TestCase):
    def test_assignment_designators_and_nonassignment_syntax(self):
        for text in (
            'type = value', 'enum(i) = value', 'type(i)%field(j:k) = value',
            'where[image] = value', 'type%field => target',
            'type(1:n) => target', 'if(i + f(j)) = value',
            'contains = 1', 'end = 1', 'module(i) = 1',
        ):
            with self.subTest(text=text):
                statement = next(Lexer(io.StringIO(text + '\n')))
                self.assertTrue(statement.is_assignment_statement())
                self.assertEqual(statement.kind, 'assignment')
                self.assertFalse(Unit.statement(statement))
                self.assertFalse(Construct.construct_stmt(statement))
                self.assertEqual(block_event(statement), (None, None))
        for text in (
            'integer :: type = 1', 'real, parameter :: enum = 2',
            'type(box) :: value', 'type :: box', 'enum, bind(c)',
            'procedure(), pointer :: p => target',
            'if (if > 0) then', 'if (if > 0) type = 1',
            'where (a > 0) a = 1', 'forall (i=1:n) a(i) = 1',
            'do i = 1, 10', 'call f(type=1)', 'use m, only: local => remote',
            'real(kind=kind(1.0)) function f(x)', 'interface assignment(=)',
            'type(i] = 1', 'type(i = 1', 'type% = 1',
        ):
            with self.subTest(text=text):
                statement = next(Lexer(io.StringIO(text + '\n')))
                self.assertFalse(statement.is_assignment_statement())

    def test_keyword_names_in_first_and_later_executable_statements(self):
        names = (
            'enum', 'type', 'if', 'where', 'forall', 'do', 'block', 'associate',
            'interface', 'contains', 'use', 'implicit', 'integer', 'function',
            'module', 'program', 'select', 'end', 'endsubroutine',
        )
        for name in names:
            for declaration, assignment in (
                (f'integer :: {name}', f'{name} = 1'),
                (f'integer :: {name}(2)', f'{name}(1) = 1'),
                (f'type(box) :: {name}', f'{name}%value = 1'),
                (f'integer, pointer :: {name}', f'{name} => target'),
            ):
                with self.subTest(name=name, assignment=assignment), tempfile.TemporaryDirectory() as tmp:
                    text = (
                        'program sample\n'
                        'type :: box\n'
                        '    integer :: value = 0\n'
                        'end type box\n'
                        'enum, bind(c)\n'
                        '    enumerator :: constant = 1\n'
                        'end enum\n'
                        'integer, target :: target\n'
                        + declaration + '\n'
                        + assignment + '\n'
                        'if (.true.) then\n'
                        '    ' + assignment + '\n'
                        'end if\n'
                        'contains\n'
                        'subroutine after()\n'
                        'end subroutine after\n'
                        'end program sample\n'
                    )
                    path = Path(tmp) / 'test.f90'
                    path.write_text(text, newline='')
                    project = flint.parse(str(path))
                    source = project.sources[0]
                    self.assertEqual(source.source_text(), text)
                    self.assertEqual([u.name for u in source.units[0].derived_types], ['box'])
                    self.assertEqual([u.name for u in source.units[0].subprograms], ['after'])
                    self.assertEqual(indentation_issues(source), [])
                    self.assertEqual(list(check_spacing(project, select_rules().values())), [])

    def test_if_variable_and_construct_in_same_scope(self):
        text = (
            'program sample\ninteger :: if\n'
            'if = 3\nif (if > 0) then\n    print *, if\nend if\nend program\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.f90'
            path.write_text(text, newline='')
            source = flint.parse(str(path)).sources[0]
            self.assertEqual(source.source_text(), text)
            self.assertEqual(indentation_issues(source), [])

    def test_macro_designators_use_expanded_tokens(self):
        for text in (
            '#define NAME type\nNAME = 1\n',
            '#define FIELD field\ntype%FIELD = 1\n',
            '#define INDEX (i)\ntype INDEX = 1\n',
        ):
            with self.subTest(text=text):
                statement = next(Lexer(io.StringIO(text)))
                self.assertTrue(statement.is_assignment_statement())
