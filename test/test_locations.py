import io
import unittest
from types import SimpleNamespace

from flint.lexer import Lexer
from flint.locations import source_locations, statement_locations


def source(text):
    return SimpleNamespace(statements=list(Lexer(io.StringIO(text))))


class TestLocations(unittest.TestCase):
    def test_source_coordinates_match_original_slices(self):
        for text in (
            '! header\n  x=1;  y=x+2\n',
            'x = f( & ! continuation\n  & x, x)\n',
            'text = "αβ" ! unicode\n',
            "text = 'first &\n  &second'\n",
            '#define VALUE 1+2\nx = VALUE\n',
            '#if 0\nIGNORED = 3\n#endif\nx=1\n',
        ):
            with self.subTest(text=text):
                parsed = source(text)
                lines = text.splitlines(keepends=True)
                offsets = [0]
                for line in lines:
                    offsets.append(offsets[-1] + len(line))
                before = [[vars(t).copy() for t in s] for s in parsed.statements]
                for statement, location in source_locations(parsed):
                    start = offsets[location.line - 1] + location.column - 1
                    end = offsets[location.end_line - 1] + location.end_column - 1
                    self.assertEqual(text[start:end], str(location.token))
                    self.assertIs(statement[location.index], location.token)
                self.assertEqual(before, [[vars(t).copy() for t in s] for s in parsed.statements])

    def test_semicolon_columns_and_isolated_unknown_column(self):
        parsed = source('x=1;  y=2\n')
        y = next(loc for stmt, loc in source_locations(parsed) if loc.token == 'y')
        self.assertEqual((y.line, y.column), (1, 7))
        isolated = next(statement_locations(parsed.statements[1]))
        self.assertEqual(isolated.line, 1)
        self.assertIsNone(isolated.column)

    def test_repeated_name_locations_use_identity(self):
        parsed = source('real, dimension(x) :: &\n  x, y\n')
        locations = [loc for loc in statement_locations(parsed.statements[0]) if loc.token == 'x']
        self.assertEqual([loc.line for loc in locations], [1, 2])
        self.assertEqual(locations[1].column, 3)

    def test_macro_only_has_displayed_invocation_span(self):
        parsed = source('#define VALUE 1+2\nx=VALUE\n')
        displayed = [str(loc.token) for stmt, loc in source_locations(parsed)]
        self.assertEqual(displayed, ['x', '=', 'VALUE'])

    def test_columns_recomputed_after_whitespace_edit(self):
        parsed = source('x=1\n')
        parsed.statements[0][0].tail.append('  ')
        locations = list(source_locations(parsed))
        self.assertEqual(locations[1][1].column, 4)

    def test_repeated_statement_reference_is_one_source_occurrence(self):
        parsed = source('x=1\ny=2\n')
        parsed.statements.insert(1, parsed.statements[0])
        locations = list(source_locations(parsed))
        self.assertEqual(len(locations), 6)
        self.assertEqual((locations[3][1].line, locations[3][1].column), (2, 1))


if __name__ == '__main__':
    unittest.main()
