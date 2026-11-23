"""Numeric labels and construct names retain source and structural boundaries."""
import io
from pathlib import Path
import tempfile
import unittest

import flint
from flint.calls import get_callable_symbols
from flint.construct import Construct
from flint.formatting.runner import check_spacing
from flint.formatting.rules import select_rules
from flint.lexer import Lexer
from flint.units.unit import Unit


def statement(text):
    return next(Lexer(io.StringIO(text + '\n')))


class LabelTests(unittest.TestCase):
    def parse(self, text):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'test.f90'
        path.write_text(text, newline='')
        project = flint.parse(str(path))
        source = project.sources[0]
        self.assertEqual(source.source_text(), text)
        # Rendering an unchanged spacing pass must also preserve all prefixes.
        self.assertEqual(list(check_spacing(project, select_rules().values())), [])
        return source

    def test_statement_label_and_construct_name_are_separate(self):
        for text, number, name, start in (
            ('0010 continue', '0010', None, 1),
            ('Outer: do i = 1, 2', None, 'Outer', 2),
            ('0010 Outer: do i = 1, 2', '0010', 'Outer', 3),
            ('integer :: value', None, None, 0),
            ('10 type(i) = 1', '10', None, 1),
        ):
            with self.subTest(text=text):
                stmt = statement(text)
                self.assertEqual(stmt.statement_label, number)
                self.assertEqual(stmt.construct_name, name)
                self.assertEqual(stmt.label, name)  # Historical API.
                self.assertEqual(stmt.code_index, start)
                self.assertEqual(stmt.source_text(), text + '\n')

    def test_named_constructs_and_labelled_endings(self):
        for opener, body, closer in (
            ('do i = 1, 2', 'call work()', 'end do'),
            ('if (.true.) then', 'call work()', 'end if'),
            ('associate (a => x)', 'call work()', 'end associate'),
            ('block', 'integer :: local', 'end block'),
            ('select case (i)', 'case (1)\ncall work()', 'end select'),
            ('select type (a => obj)', 'type is (integer)\ncall work()', 'end select'),
            ('where (a > 0)', 'a = 1', 'end where'),
            ('forall (i=1:2)', 'a(i) = 1', 'end forall'),
            ('critical', 'call work()', 'end critical'),
            ('change team (team)', 'call work()', 'end team'),
            ('change team (team)', 'call work()', 'end team(stat=status)'),
        ):
            for prefix in ('', '0010 '):
                with self.subTest(opener=opener, prefix=prefix):
                    source = self.parse(
                        'program sample\ninteger :: i, x, a(2)\n'
                        + prefix + 'Outer: ' + opener + '\n'
                        + body + '\n'
                        + '20 ' + closer + ' oUTer\n'
                        + 'call after()\nend program sample\n'
                        + 'subroutine after()\nend subroutine after\n'
                    )
                    self.assertEqual([u.name for u in source.units], ['sample', 'after'])
                    self.assertIn('after', source.units[0].callees)

    def test_nested_named_constructs(self):
        source = self.parse(
            'program sample\ninteger :: i\n'
            'Outer: do i = 1, 2\n'
            'Inner: if (i == 1) then\n'
            'cycle outer\n'
            'end if inner\n'
            'end do outer\n'
            'call after()\nend program\n'
        )
        self.assertIn('after', source.units[0].callees)

    def test_labelled_declarations_calls_interfaces_and_unit_headers(self):
        source = self.parse(
            '10 module sample\n'
            '20 integer :: value\n'
            '30 interface\n'
            '40 subroutine work()\n'
            '50 end subroutine work\n'
            '60 end interface\n'
            'contains\n'
            '70 subroutine run()\n'
            '80 call work()\n'
            '90 end subroutine run\n'
            '100 end module sample\n'
        )
        root = source.units[0]
        self.assertEqual([v.name for v in root.variables], ['value'])
        self.assertEqual(root.interfaces[0].subprograms[0].name, 'work')
        self.assertEqual(root.subprograms[0].name, 'run')
        self.assertIn('work', root.subprograms[0].callees)
        self.assertEqual(Unit.header_index(statement('10 pure subroutine f()')), 2)

    def test_shared_do_terminal_labels_and_unrelated_continue(self):
        for terminal in ('continue', 'total = total + 1'):
            with self.subTest(terminal=terminal):
                source = self.parse(
                    'program sample\ninteger :: i, j, total\n'
                    'total = 0\n'
                    'do 010 i = 1, 2\n'
                    '20 continue\n'
                    'do 10 j = 1, 2\n'
                    '10 ' + terminal + '\n'
                    'call after()\n'
                    'end program\n'
                )
                self.assertEqual(sum(s.statement_label == '10' for s in source.statements), 1)
                self.assertIn('after', source.units[0].callees)

    def test_end_names_and_labels_match_the_open_construct(self):
        block = Construct(Unit())
        block.ctype = 'do'
        block.name = 'Outer'
        block.terminal_label = 10
        self.assertTrue(block.end_statement(statement('0010 continue')))
        self.assertFalse(block.end_statement(statement('20 continue')))
        self.assertTrue(block.end_statement(statement('end do outer')))
        self.assertTrue(block.end_statement(statement('enddo OUTER')))
        self.assertFalse(block.end_statement(statement('end do other')))
        self.assertFalse(block.end_statement(statement('end if outer')))

    def test_labelled_format_and_assignment_call_detection(self):
        self.assertEqual(get_callable_symbols(statement('10 format(f10.3)'), []), [])
        calls = get_callable_symbols(statement('10 format(i) = f(i)'), [], variable_names={'format'})
        self.assertEqual(calls, ['f'])
