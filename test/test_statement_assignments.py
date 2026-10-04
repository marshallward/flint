import io
import sys
import unittest

sys.path.insert(1, '../')
from flint.lexer import Lexer  # noqa: E402


def lex_one(line):
    return next(Lexer(io.StringIO(line)))


class TestStatementAssignments(unittest.TestCase):

    def assignment_roles(self, stmt):
        return [
            (index, token.syntax_role)
            for index, token in enumerate(stmt.tokens)
            if token == '='
        ]

    def test_assignment_and_name_value_roles(self):
        stmt = lex_one('x = foo(a=1, b = bar(c=2))\n')

        self.assertEqual(self.assignment_roles(stmt), [
            (1, 'assignment'),
            (5, 'name_value'),
            (9, 'name_value'),
            (13, 'name_value'),
        ])
        self.assertEqual(stmt.assignment_operator_index(), 1)
        self.assertEqual(stmt.assignment_operator_indices(), [1])
        self.assertEqual(stmt.named_argument_indices(), [5, 9, 13])

    def test_declaration_initialization_is_assignment(self):
        stmt = lex_one('integer, parameter :: i=1\n')

        self.assertEqual(stmt.kind, 'declaration')
        self.assertEqual(self.assignment_roles(stmt), [(5, 'assignment')])
        self.assertEqual(stmt.assignment_operator_indices(), [5])
        self.assertEqual(stmt.named_argument_indices(), [])

    def test_declaration_specifier_is_named_assignment(self):
        stmt = lex_one('character(len=32) :: name\n')

        self.assertEqual(stmt.kind, 'declaration')
        self.assertEqual(self.assignment_roles(stmt), [(3, 'name_value')])
        self.assertEqual(stmt.assignment_operator_indices(), [])
        self.assertEqual(stmt.named_argument_indices(), [3])

    def test_do_control_roles(self):
        stmt = lex_one('do k = 1, nz\n')
        labeled = lex_one('loop: do k = 1, nz\n')
        numbered = lex_one('do 100 k = 1, nz\n')

        self.assertEqual(self.assignment_roles(stmt), [(2, 'do_control')])
        self.assertEqual(self.assignment_roles(labeled), [(4, 'do_control')])
        self.assertEqual(self.assignment_roles(numbered), [(3, 'do_control')])
        self.assertEqual(stmt.do_control_assignment_indices(), [2])
        self.assertEqual(labeled.do_control_assignment_indices(), [4])
        self.assertEqual(numbered.do_control_assignment_indices(), [3])

    def test_generic_assignment_spec_is_not_assignment(self):
        stmt = lex_one(
            'use MOM_coms, only : EFP_type, assignment(=), EFP_sum\n'
        )

        self.assertEqual(self.assignment_roles(stmt), [(9, 'generic_spec')])
        self.assertEqual(stmt.assignment_operator_indices(), [])
        self.assertEqual(stmt.named_argument_indices(), [])

    def test_caller_can_check_token_liminals(self):
        stmt = lex_one('x=foo(a = 1)\n')
        checks = (
            (index, token.syntax_role)
            for index, token in enumerate(stmt.tokens)
            if token.syntax_role is not None
        )

        liminals = [
            (index, role, ''.join(stmt[index].head), ''.join(stmt[index].tail))
            for index, role in checks
        ]

        self.assertEqual(liminals, [
            (1, 'assignment', '', ''),
            (5, 'name_value', ' ', ' '),
        ])


if __name__ == '__main__':
    unittest.main()
