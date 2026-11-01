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
from flint.formatting.spacing import render


def parse_source(text):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'test.F90'
        path.write_text(text)

        source = Source()
        source.parse(str(path))

    return source


class TestUnit(unittest.TestCase):
    def test_non_header_rejected_before_later_keyword(self):
        for text in ('call work(function)\n', 'x = function(1)\n'):
            with self.subTest(text=text):
                stmt = next(Lexer(io.StringIO(text)))
                self.assertFalse(Unit.statement(stmt))
        self.assertFalse(Unit.statement([]))

    def test_prefixed_unit_headers_pass_fast_rejection(self):
        for text in (
            'PURE REAL FUNCTION demo(x)\n',
            'recursive subroutine demo(x)\n',
            'character(len=20) function demo(x)\n',
        ):
            with self.subTest(text=text):
                stmt = next(Lexer(io.StringIO(text)))
                self.assertTrue(Unit.statement(stmt))

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

    def test_function_header_skips_return_type_selectors(self):
        for text in ('type(time_type) function demo(x)',
                     'pure type(box(k=kind(1))) function demo(x) result(value)',
                     'class(box) function demo(x)',
                     'real(kind=selected_real_kind(12)) function demo(x)',
                     'module pure real function demo(x)'):
            with self.subTest(text=text):
                statement = next(Lexer(io.StringIO(text + '\n')))
                self.assertTrue(Unit.statement(statement))
                unit = Unit()
                unit.parse_header(statement)
                self.assertEqual(unit.utype, 'function')
                self.assertEqual(unit.name, 'demo')
        for text in ('type(time_type) :: value', 'class(box) :: value',
                     'real :: function', 'real function(2)', 'module procedure demo'):
            with self.subTest(text=text):
                self.assertFalse(Unit.statement(next(Lexer(io.StringIO(text + '\n')))))

    def test_derived_return_function_does_not_swallow_siblings(self):
        source = parse_source('''module demo
contains
type(time_type) function real_to_time(x) result(value)
  real :: x
end function real_to_time
real function time_to_real(t)
  type(time_type) :: t
  real :: scale
end function time_to_real
end module demo
''')
        module = source.units[0]
        self.assertEqual([str(u.name) for u in module.subprograms], ['real_to_time', 'time_to_real'])
        self.assertEqual([str(v.name) for v in module.subprograms[1].variables], ['t', 'scale'])

    def test_unit_names_can_be_procedure_keywords(self):
        for text, kind in [('module function', 'module'), ('type function', 'type'),
                           ('program subroutine', 'program')]:
            with self.subTest(text=text):
                unit = Unit()
                unit.parse_header(next(Lexer(io.StringIO(text + '\n'))))
                self.assertEqual(unit.utype, kind)
                self.assertEqual(unit.name, text.split()[1])

    def test_interface_bodies_have_scoped_variables_and_roundtrip_source(self):
        text = '''module demo
abstract interface
  type(box) function first(x) result(value)
    import :: box
    real :: x !< Position [m]
  end function first
  subroutine second(x)
    real :: x !< Velocity [m s-1]
  end subroutine second
end interface
real :: outside
contains
subroutine implementation()
  real :: local
end subroutine implementation
end module demo
'''
        source = parse_source(text)
        module = source.units[0]
        interface = module.interfaces[0]
        self.assertTrue(interface.abstract)
        self.assertEqual([str(u.name) for u in interface.subprograms], ['first', 'second'])
        first, second = [u.variables[0] for u in interface.subprograms]
        self.assertEqual(first.documentation[0].comments, ('!< Position [m]',))
        self.assertEqual(second.documentation[0].comments, ('!< Velocity [m s-1]',))
        self.assertEqual((first.location.line, second.location.line), (5, 8))
        self.assertEqual([str(v.name) for v in module.variables], ['outside'])
        self.assertEqual([str(u.name) for u in module.subprograms], ['implementation'])
        self.assertEqual([str(u.name) for u in module.walk()], ['demo', 'implementation', 'first', 'second'])
        self.assertEqual([str(u.name) for u in module.walk(include_interfaces=False)], ['demo', 'implementation'])
        self.assertEqual(render(source.statements), text)

    def test_generic_procedure_references_are_not_interface_bodies(self):
        source = parse_source('''module demo
interface generic
  module procedure first, second
  procedure :: external_one, external_two
end interface generic
end module demo
''')
        interface = source.units[0].interfaces[0]
        self.assertEqual([str(name) for name in interface.procedures],
                         ['first', 'second', 'external_one', 'external_two'])
        self.assertEqual(interface.subprograms, [])

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
