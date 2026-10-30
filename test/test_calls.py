import io
import unittest
from types import SimpleNamespace

from flint.calls import get_callable_symbols
from flint.lexer import Lexer
from flint.token import PToken


def statement(text):
    return next(Lexer(io.StringIO(text + '\n')))


class TestCallableSymbols(unittest.TestCase):
    def test_no_candidates_does_not_inspect_variables(self):
        def unavailable_variables():
            raise AssertionError('Variable names are unnecessary without candidates')
            yield

        for text in ('x = a + b', 'x = obj%field(i)', 'return'):
            with self.subTest(text=text):
                self.assertEqual(
                    get_callable_symbols(statement(text), unavailable_variables()), [],
                )

    def test_candidates_exclude_declared_objects_case_insensitively(self):
        variables = [SimpleNamespace(name='FIELD')]
        result = get_callable_symbols(
            statement('x = field(i) + compute(i) + compute(j)'), variables,
        )
        self.assertEqual(list(map(str, result)), ['compute', 'compute'])

    def test_precomputed_empty_names_are_respected(self):
        variables = [SimpleNamespace(name='compute')]
        result = get_callable_symbols(
            statement('x = compute(i)'), variables, variable_names=set(),
        )
        self.assertEqual(list(map(str, result)), ['compute'])

    def test_mixed_case_candidates_keep_source_spelling(self):
        result = get_callable_symbols(
            statement('x = FiElD(i) + CoMpUtE(i)'),
            [SimpleNamespace(name='FIELD')],
        )
        self.assertEqual(list(map(str, result)), ['CoMpUtE'])

    def test_macro_variable_exclusion_uses_expanded_name(self):
        line = statement('x = Field(i) + Compute(i)')
        line[2] = PToken('FIELD', pp=['ARRAY_MACRO'])
        variables = [SimpleNamespace(name=PToken('field', pp=['DECL_MACRO']))]
        result = get_callable_symbols(line, variables)
        self.assertEqual(list(map(str, result)), ['Compute'])


if __name__ == '__main__':
    unittest.main()
