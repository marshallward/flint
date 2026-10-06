import io
import sys
import unittest

sys.path.insert(1, '../')
from flint.lexer import Lexer  # noqa: E402


def lex_one(line):
    return next(Lexer(io.StringIO(line)))


def operator_roles(stmt):
    return [
        (index, str(token), token.operator_role)
        for index, token in enumerate(stmt.tokens)
        if token.operator_role is not None
    ]


class TestStatementOperators(unittest.TestCase):

    def test_binary_unary_exponent_and_concat_roles(self):
        stmt = lex_one('x = -a+b**2//c .and. .not.d\n')

        self.assertEqual(operator_roles(stmt), [
            (2, '-', 'unary_operator'),
            (4, '+', 'binary_operator'),
            (6, '**', 'exponentiation'),
            (8, '//', 'concatenation'),
            (10, '.and.', 'binary_operator'),
            (11, '.not.', 'unary_operator'),
        ])

    def test_declaration_prefix_operator_roles(self):
        stmt = lex_one('character(len=*), dimension(*) :: name\n')

        self.assertEqual(operator_roles(stmt), [
            (4, '*', 'declaration_specifier'),
            (9, '*', 'declaration_specifier'),
        ])

    def test_generic_operator_spec_role(self):
        stmt = lex_one('interface operator(+)\n')

        self.assertEqual(operator_roles(stmt), [
            (3, '+', 'generic_operator_specifier'),
        ])

    def test_do_control_operator_role(self):
        stmt = lex_one('do i=isc-1,iec+1\n')

        self.assertEqual(operator_roles(stmt), [
            (4, '-', 'do_control_operator'),
            (8, '+', 'do_control_operator'),
        ])

    def test_callable_and_subscript_operator_roles(self):
        stmt = lex_one('x = f(scale=- m_to_L*s_to_T) + h(i+1,j)\n')

        self.assertEqual(operator_roles(stmt), [
            (6, '-', 'callable_or_subscript_operator'),
            (8, '*', 'callable_or_subscript_operator'),
            (11, '+', 'binary_operator'),
            (15, '+', 'callable_or_subscript_operator'),
        ])

    def test_print_format_star_role(self):
        stmt = lex_one('print *, "message"\n')

        self.assertEqual(operator_roles(stmt), [
            (1, '*', 'format_specifier'),
        ])


if __name__ == '__main__':
    unittest.main()
