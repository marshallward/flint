import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(1, '../')
from flint.source import Source  # noqa: E402
from flint.lexer import Lexer  # noqa: E402
from flint.statement import Statement  # noqa: E402
from flint.token import PToken, Token  # noqa: E402
from flint.units.unit import Unit  # noqa: E402


def parse_source(text):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'test.F90'
        path.write_text(text)

        source = Source()
        source.parse(str(path))

    return source


class TestUnit(unittest.TestCase):
    def test_case_insensitive_unit_keyword_lookup(self):
        stmt = Statement([Token('PURE'), Token('REAL'), Token('FUNCTION'), Token('demo')])
        self.assertTrue(Unit.statement(stmt))
        unit = Unit()
        unit.parse_header(stmt)
        self.assertEqual(unit.utype, 'function')
        self.assertEqual(unit.name, 'demo')

    def test_preprocessed_unit_keyword_uses_semantic_value(self):
        for display in ('', 'PROCEDURE_MACRO'):
            with self.subTest(display=display):
                stmt = Statement([PToken('SUBROUTINE', pp=display), Token('demo')])
                self.assertTrue(Unit.statement(stmt))
                unit = Unit()
                unit.parse_header(stmt)
                self.assertEqual(unit.utype, 'subroutine')
                self.assertEqual(unit.name, 'demo')

    def test_refresh_callees_builds_variable_names_once(self):
        class Variable:
            accesses = 0

            @property
            def name(self):
                self.accesses += 1
                return 'FIELD'

        variable = Variable()
        unit = Unit()
        unit.utype = 'subroutine'
        unit.variables = [variable]
        unit.statements = list(Lexer(io.StringIO(
            'x = field(i) + first(i)\n'
            'x = field(j) + second(j)\n'
        )))
        unit.refresh_callees()
        self.assertEqual(variable.accesses, 1)
        self.assertEqual({str(name) for name in unit.callees}, {'first', 'second'})

    def test_inline_array_declarations_are_tracked(self):
        source = parse_source('''subroutine demo(i, j)
  integer :: i, j
  real :: A(:), B(10,10), x
  real, dimension(:) :: C, D
  x = A(i) + B(i,j) + C(i) + D(j) + f(i,j)
end subroutine demo
''')

        unit = source.units[0]
        dimensions = {
            str(var.name): var.dimension
            for var in unit.variables
        }

        self.assertEqual(
            dimensions,
            {'i': None, 'j': None, 'A': 1, 'B': 2, 'x': None, 'C': 1, 'D': 1},
        )
        self.assertEqual({str(name) for name in unit.callees}, {'f'})

    def test_class_declaration_does_not_stop_specification_part(self):
        source = parse_source('''subroutine demo(obj, field)
  class(type_name), intent(inout) :: obj
  real, intent(inout) :: field(:,:,:)
  real, allocatable :: work(:,:,:)
  work(:,:,:) = field(:,:,:)
end subroutine demo
''')

        unit = source.units[0]
        dimensions = {
            str(var.name): var.dimension
            for var in unit.variables
        }

        self.assertEqual(
            dimensions,
            {'obj': None, 'field': 3, 'work': 3},
        )
        self.assertEqual({str(name) for name in unit.callees}, set())

    def test_declared_scalar_is_not_callable(self):
        source = parse_source('''subroutine demo(i)
  integer :: i
  real :: value
  value = value(i) + custom_fn(i)
end subroutine demo
''')

        unit = source.units[0]

        self.assertEqual({str(name) for name in unit.callees}, {'custom_fn'})

    def test_unknown_declaration_attribute_before_separator(self):
        source = parse_source('''subroutine demo()
  real ALLOCABLE_, dimension(NI,NJ,NK) :: field
end subroutine demo
''')

        unit = source.units[0]
        variables = {str(var.name): var.dimension for var in unit.variables}

        self.assertEqual(variables, {'field': 3})


if __name__ == '__main__':
    unittest.main()
