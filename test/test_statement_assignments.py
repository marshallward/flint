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

    def test_implied_do_control_roles(self):
        examples = [
            'dimids(:) = [(axes(i)%dimid, i = 1, size(axes))]\n',
            'x = [0, (i, i=1,n), 42]\n',
            'x = (/ (i, i = 1, n, 2) /)\n',
            'write(*,*) (a(i), i = 1, n)\n',
            'read(*,*) (a(i), i = 1, n)\n',
            'data a / (i, i = 1, 3) /\n',
        ]
        for text in examples:
            with self.subTest(text=text):
                stmt = lex_one(text)
                controls = stmt.do_control_assignment_indices()
                self.assertEqual(len(controls), 1)
                self.assertEqual(str(stmt[controls[0] - 1]), 'i')
                self.assertEqual(stmt.named_argument_indices(), [])

    def test_nested_implied_do_and_named_arguments(self):
        stmt = lex_one('x = [((f(a = i, b = j), i = 1,n), j = 1,m)]\n')

        self.assertEqual(
            [role for _, role in self.assignment_roles(stmt)],
            ['assignment', 'name_value', 'name_value', 'do_control', 'do_control'],
        )

    def test_parenthesized_expressions_are_not_implied_do(self):
        for text in ['x = [(a + b)]\n', 'x = [(f(i)), 42]\n']:
            with self.subTest(text=text):
                self.assertEqual(lex_one(text).do_control_assignment_indices(), [])

    def test_named_argument_followed_by_positional_arguments(self):
        stmt = lex_one('x = f(a, i = 1, n)\n')

        self.assertEqual(stmt.do_control_assignment_indices(), [])
        self.assertEqual(
            [role for _, role in self.assignment_roles(stmt)],
            ['assignment', 'name_value'],
        )

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
