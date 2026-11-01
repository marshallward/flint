"""High-level declared-variable inspection for custom scripts."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import flint
from flint.documentation import documentation_pass, _analyze_declaration


class VariableSourceTests(unittest.TestCase):
    def test_documentation_pass_reuses_only_latest_declaration(self):
        source = self.parse('subroutine demo()\nreal :: x, y !< Length [m]\n'
                            'real :: z !< Time [s]\nend subroutine demo\n')
        x, y, z = source.units[0].variables
        expected = [v.documentation for v in (x, y, z)]
        with patch('flint.documentation._analyze_declaration', wraps=_analyze_declaration) as analyze:
            with documentation_pass():
                self.assertEqual([v.documentation for v in (x, y, z)], expected)
                self.assertEqual(analyze.call_count, 2)
                self.assertEqual(x.documentation, expected[0])
                self.assertEqual(analyze.call_count, 3)
                with documentation_pass():
                    self.assertEqual(y.documentation, expected[1])
                self.assertEqual(x.documentation, expected[0])
                self.assertEqual(analyze.call_count, 4)

    def test_documentation_pass_releases_snapshot_after_exception_and_edits(self):
        source = self.parse('subroutine demo()\nreal :: x !< Length [m]\nend subroutine demo\n')
        x = source.units[0].variables[0]
        with self.assertRaisesRegex(ValueError, 'stop'):
            with documentation_pass():
                self.assertEqual(x.documentation[0].comments, ('!< Length [m]',))
                raise ValueError('stop')
        x.stmt[-1].tail[:] = [' ', '!< Time [s]', '\n']
        self.assertEqual(x.documentation[0].comments, ('!< Time [s]',))
        with documentation_pass():
            self.assertEqual(x.documentation[0].comments, ('!< Time [s]',))

    def parse(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(text)
            return flint.parse(str(path)).sources[0]

    def test_shape_initializer_and_attribute_extraction(self):
        source = self.parse('''subroutine demo()
  real, dimension(2), intent(in) :: a, b(2,3)
  real :: x = max(1,2), y(2) = [1,2], z
  double precision d, e
end subroutine demo
''')
        variables = source.units[0].variables
        self.assertEqual([str(v.name) for v in variables], ['a', 'b', 'x', 'y', 'z', 'd', 'e'])
        self.assertEqual([v.dimension for v in variables], [1, 2, None, 1, None, None, None])
        self.assertEqual([v.intent for v in variables[:2]], ['in', 'in'])
        self.assertTrue(all(v.type == 'real' for v in variables))
        self.assertEqual([str(t) for t in variables[2].declaration_tokens],
                         ['x', '=', 'max', '(', '1', ',', '2', ')'])

    def test_variable_comments_and_locations(self):
        source = self.parse('''subroutine demo()
  real, dimension(x) :: &
    x, & !< Length [m]
    y !< No units
end subroutine demo
''')
        x, y = source.units[0].variables
        self.assertEqual((x.location.line, y.location.line), (3, 4))
        self.assertIs(x.location.token, x.name)
        self.assertEqual(x.documentation[0].comments, ('!< Length [m]',))
        self.assertEqual(y.documentation[0].comments, ('!< No units',))
        self.assertIs(x.declaration.name, x.name)

    def test_macro_attributes_shapes_and_documentation(self):
        source = self.parse('''#define ATTR , allocatable
#define EXTENT :
#define SHAPE (2,3)
subroutine demo()
  real ATTR, dimension(EXTENT,EXTENT) :: &
    x, & !< Length [m]
    y !< Time [s]
  real :: z SHAPE
end subroutine demo
''')
        x, y, z = source.units[0].variables
        self.assertEqual([v.dimension for v in (x, y, z)], [2, 2, 2])
        self.assertEqual((x.location.line, y.location.line), (6, 7))
        self.assertEqual(x.documentation[0].comments, ('!< Length [m]',))
        self.assertEqual(y.documentation[0].comments, ('!< Time [s]',))

    def test_included_macro_declaration_retains_anchor_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'decl.h').write_text('real ATTR :: x\n')
            path = root / 'demo.F90'
            path.write_text('#define ATTR , allocatable\nsubroutine demo()\n'
                            '#include "decl.h"\nend subroutine demo\n')
            source = flint.parse(str(path), includes=[str(root)]).sources[0]
            variable = source.units[0].variables[0]
            self.assertIsNotNone(variable.declaration)
            self.assertEqual(variable.type, 'real')
            self.assertIsNone(variable.location)
            self.assertFalse(variable.stmt.source_visible)

    def test_header_definitions_and_leading_conditionals_share_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'decl.h').write_text('#ifdef ENABLED\n#define ATTR , allocatable\n'
                                       'real ATTR :: x\n#endif\n')
            path = root / 'demo.F90'
            path.write_text('#define ENABLED 1\nsubroutine demo()\n#include "decl.h"\n'
                            'real ATTR :: y !< Length [m]\nend subroutine demo\n')
            source = flint.parse(str(path), includes=[str(root)]).sources[0]
            x, y = source.units[0].variables
            self.assertEqual([str(v.name) for v in (x, y)], ['', 'y'])
            self.assertEqual(x.name, 'x')
            self.assertIsNotNone(x.declaration)
            self.assertIsNotNone(y.declaration)
            self.assertEqual(y.documentation[0].comments, ('!< Length [m]',))

    def test_nested_procedures_and_type_components(self):
        source = self.parse('''module demo
type :: item
  real :: field
end type item
real :: global
contains
subroutine outer()
  real :: local
contains
  subroutine inner()
    real :: nested
  end subroutine inner
end subroutine outer
end module demo
''')
        module = source.units[0]
        self.assertEqual([str(v.name) for v in module.variables], ['global'])
        self.assertEqual([str(v.name) for v in module.derived_types[0].variables], ['field'])
        outer = module.subprograms[0]
        self.assertEqual([str(v.name) for v in outer.variables], ['local'])
        nested = outer.subprograms[0].variables[0]
        self.assertEqual(str(nested.name), 'nested')
        self.assertEqual(nested.documentation, ())
