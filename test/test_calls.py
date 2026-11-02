import io
import unittest
from types import SimpleNamespace

from flint.calls import get_callable_symbols
from flint.lexer import Lexer
from flint.token import PToken


def statement(text):
    return next(Lexer(io.StringIO(text + '\n')))


class TestCallableSymbols(unittest.TestCase):
    def test_io_statements_are_not_calls(self):
        for text, expected in (
            ('write(unit,*) value()', ['value']),
            ('if (ready(check())) write(unit,*) value()', ['ready', 'check', 'value']),
            ('100 if (ready()) write(unit,*) value()', ['ready', 'value']),
            ('if (ready()) read(unit,fmt=format_for()) x', ['ready', 'format_for']),
            ('if (ready()) open(unit=unit, file=filename())', ['ready', 'filename']),
            ('if (ready()) close(unit)', ['ready']),
            ('if (ready()) inquire(unit, opened=opened)', ['ready']),
            ('if (ready()) flush(unit)', ['ready']),
        ):
            with self.subTest(text=text):
                self.assertEqual(get_callable_symbols(statement(text), []), expected)

    def test_io_names_remain_callable_in_expressions_and_calls(self):
        for text, expected in (
            ('x = write(value)', ['write']),
            ('call write(value)', ['write']),
            ('if (ready()) call write(value)', ['ready', 'write']),
            ('if (write(value)) x = read(value)', ['write', 'read']),
            ('if (ready()) write(unit,*) write(value)', ['ready', 'write']),
        ):
            with self.subTest(text=text):
                self.assertEqual(get_callable_symbols(statement(text), []), expected)

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
