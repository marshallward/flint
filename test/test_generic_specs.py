"""Preserve generic identities and their separate USE-associated contributors."""
from pathlib import Path
import tempfile
import unittest

import flint
from flint.docgen.check import check_documentation
from flint.docgen.model import build_unit_documentation, _scope_metadata
from flint.docgen.references import ReferenceIndex, anchor


class GenericSpecTests(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(text)
            source = flint.parse(str(path)).sources[0]
        rendered = ''.join(source.statements[0][0].head)
        rendered += ''.join(str(t) + ''.join(t.tail) for s in source.statements for t in s)
        self.assertEqual(rendered, text)
        return source

    def test_full_generic_names_members_docs_and_access(self):
        source = self.parse('''!> Module.
module demo
private
public :: operator(+), assignment(=), ordinary
interface OPERATOR ( + )
module procedure add
end interface operator(+)
interface operator(-)
module procedure subtract
endinterface operator(-)
!> Copy a value.
interface assignment(=)
module procedure assign
end interface assignment(=)
interface read(formatted)
module procedure read_value
end interface read(formatted)
interface write(unformatted)
module procedure write_value
end interface write(unformatted)
end module demo
''')
        unit = source.units[0]
        self.assertEqual([i.name for i in unit.interfaces],
                         ['operator(+)', 'operator(-)', 'assignment(=)', 'read(formatted)', 'write(unformatted)'])
        self.assertEqual(unit.interfaces[0].name.original, 'OPERATOR(+)')
        self.assertEqual(unit.interfaces[0].procedures, ['add'])
        self.assertEqual(unit.interfaces[1].procedures, ['subtract'])
        _, default, access = _scope_metadata(unit)
        self.assertFalse(default)
        self.assertEqual(dict(access), {'operator(+)': True, 'assignment(=)': True, 'ordinary': True})
        self.assertEqual([i.name for i in check_documentation(source)],
                         ['demo::OPERATOR(+)', 'demo::operator(-)', 'demo::read(formatted)',
                          'demo::write(unformatted)'])
        self.assertEqual(len(build_unit_documentation(unit).interfaces), 5)

    def test_end_spec_must_match_opening_spec(self):
        with self.assertRaises(AssertionError):
            self.parse('module demo\ninterface operator(+)\nend interface operator(-)\nend module demo\n')
        with self.assertRaises(AssertionError):
            self.parse('module demo\ninterface operator(+)\nendinterface operator(-)\nend module demo\n')

    def test_multiple_imports_reexports_and_local_extensions(self):
        source = self.parse('''module vectors
private
public :: operator(+)
type :: vector
integer :: value
end type
interface operator(+)
module procedure add_vector
end interface
contains
function add_vector(a,b) result(c)
type(vector), intent(in) :: a,b
type(vector) :: c
end function
end module vectors
module matrices
private
public :: operator(+)
type :: matrix
real :: value
end type
interface operator(+)
module procedure add_matrix
end interface
contains
function add_matrix(a,b) result(c)
type(matrix), intent(in) :: a,b
type(matrix) :: c
end function
end module matrices
module combined
use vectors, only : operator(+)
use matrices, only : operator(+)
private
public :: operator(+)
end module combined
module client
use combined, only : operator(+)
use vectors, only : operator(+)
type :: local_type
complex :: value
end type
interface operator(+)
module procedure add_local
end interface
contains
function add_local(a,b) result(c)
type(local_type), intent(in) :: a,b
type(local_type) :: c
end function
subroutine work()
end subroutine
end module client
''')
        models = [build_unit_documentation(u) for u in source.units]
        self.assertEqual(models[2].uses[0].names, (('operator(+)', 'operator(+)'),))
        index = ReferenceIndex(models)
        contributors = index.generic_interfaces('client::work', 'operator(+)')
        self.assertEqual(contributors.interfaces,
                         ('client::interface::operator(+)', 'matrices::interface::operator(+)',
                          'vectors::interface::operator(+)'))
        self.assertFalse(contributors.incomplete)
        self.assertEqual(index.implementations['vectors::interface::operator(+)'][0].target,
                         'vectors::add_vector')
        # This API tracks contributions, not whether operand signatures would
        # constitute a valid Fortran overload set, nor which specific to invoke.
        self.assertEqual(index.generic_interfaces('combined', 'operator(-)').interfaces, ())

    def test_defined_operator_rename_and_unknown_contributor(self):
        source = self.parse('''module origin
private
public :: operator(.join.)
interface operator(.join.)
module procedure combine
end interface
contains
function combine(a,b) result(c)
integer :: a,b,c
end function
end module origin
module client
use origin, only : operator(.merge.) => operator(.join.)
use unavailable, only : operator(.merge.)
end module client
''')
        models = [build_unit_documentation(u) for u in source.units]
        self.assertEqual(models[1].uses[0].names, (('operator(.merge.)', 'operator(.join.)'),))
        result = ReferenceIndex(models).generic_interfaces('client', 'operator(.merge.)')
        self.assertEqual(result.interfaces, ('origin::interface::operator(.join.)',))
        self.assertTrue(result.incomplete)

    def test_generic_anchors_are_distinct_and_html_safe(self):
        names = ['operator(+)', 'operator(-)', 'operator(==)', 'operator(.eq.)',
                 'operator(.mine.)', 'assignment(=)', 'read(formatted)']
        anchors = [anchor('demo::interface::' + n) for n in names]
        self.assertEqual(len(set(anchors)), len(names))
        for target in anchors:
            self.assertRegex(target, r'^flint-[a-z0-9-]+$')
        self.assertEqual(anchor('some_module::work'), 'flint-some-0module-1work')

    def test_macro_operator_and_equivalent_relational_spelling(self):
        source = self.parse('''#define OP .eq.
module demo
private
public :: operator(OP)
interface operator(OP)
module procedure equals
end interface operator(==)
contains
function equals(a,b) result(c)
integer :: a,b
logical :: c
end function
end module demo
module client
use demo, only : operator(==)
end module client
''')
        module = source.units[0]
        self.assertEqual(module.interfaces[0].name, 'operator(==)')
        models = [build_unit_documentation(u) for u in source.units]
        index = ReferenceIndex(models)
        self.assertEqual(index.generic_interfaces('client', 'operator(.EQ.)').interfaces,
                         ('demo::interface::operator(==)',))
        self.assertFalse(index.generic_interfaces('client', 'operator(.eq.)').incomplete)

    def test_cyclic_reexports_terminate_and_report_incompleteness(self):
        source = self.parse('''module first
use second, only : operator(+)
end module first
module second
use first, only : operator(+)
end module second
''')
        result = ReferenceIndex([build_unit_documentation(u) for u in source.units]).generic_interfaces(
            'first', 'operator(+)')
        self.assertEqual(result.interfaces, ())
        self.assertTrue(result.incomplete)


if __name__ == '__main__':
    unittest.main()
