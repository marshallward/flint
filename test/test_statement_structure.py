import io
import unittest
from unittest.mock import patch

from flint.lexer import Lexer
from flint.statement import Statement
from flint.token import PToken, Token


def lex(text):
    return next(Lexer(io.StringIO(text + '\n')))


def roles(statement):
    return [(tok.syntax_role, tok.operator_role) for tok in statement]


class TestSharedStatementStructure(unittest.TestCase):
    def test_shared_and_generic_classifiers_agree_on_nested_statements(self):
        expressions = [
            'a(i)', 'f(a(i), option=g(j))',
            'f(a=-b, option=g(c=d))',
            '[(f(option=i), i=1,n)]',
            '((f(a=i,b=j),i=1,n),j=1,m)',
            '(/ (i,i=1,n,2) /)',
            '(a + b) * (-c)', '.not.a .and. (b .or. c)',
            'f(a, i=1, n)', 'f(x=[(i,i=1,n)])',
            "f(text='(a=b)', value=x**2)",
        ]
        examples = [f'x = {expr}' for expr in expressions]
        examples += [f'call work({expr}, option=1)' for expr in expressions]
        examples += [
            'do i=1,n', 'outer: do i=1,n', 'do 100 i=1,n',
            'character(len=*), dimension(*) :: name',
            'real :: x = f(option=1)', 'interface operator(+)',
            'use m, only: assignment(=)', 'write(*,*) (a(i),i=1,n)',
        ]
        for text in examples:
            for variant in (text, text.upper()):
                with self.subTest(text=variant):
                    current = lex(variant)
                    with patch.object(Statement, '_classify_token_roles',
                                      Statement._classify_token_roles_generic):
                        reference = lex(variant)
                    self.assertEqual(roles(current), roles(reference))
                    self.assertEqual(current.kind, reference.kind)
                    self.assertEqual(current.source_text(), reference.source_text())

    def test_reclassification_uses_current_tokens(self):
        stmt = lex('call f(option=1)')
        equals = stmt.index('=')
        self.assertEqual(stmt[equals].syntax_role, 'name_value')
        stmt[:] = [Token('x'), Token('='), Token('1')]
        stmt._classify_token_roles()
        self.assertEqual(stmt[1].syntax_role, 'assignment')

    def test_subclasses_use_generic_classifier(self):
        class CustomToken(Token):
            pass

        for token in (CustomToken('x'), PToken('x', pp='FIELD_MACRO')):
            with self.subTest(token_type=type(token).__name__):
                with patch.object(Statement, '_classify_token_roles_generic', autospec=True,
                                  side_effect=Statement._classify_token_roles_generic) as fallback:
                    stmt = Statement([token, Token('='), Token('1')])
                fallback.assert_called_once_with(stmt)
                self.assertEqual(stmt[1].syntax_role, 'assignment')

    def test_classification_preserves_tokens_and_whitespace(self):
        stmt = lex('x = f(a(i), &\n    option=g(j)) ! comment')
        original = stmt.source_text()
        identities = [id(tok) for tok in stmt]
        stmt._classify_token_roles()
        self.assertEqual([id(tok) for tok in stmt], identities)
        self.assertEqual(stmt.source_text(), original)


if __name__ == '__main__':
    unittest.main()
