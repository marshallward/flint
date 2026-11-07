"""Type-bound associations retain their identities, source, and documentation."""
import io
from pathlib import Path
import tempfile
import unittest

import flint
from flint.bindings import parse_bindings
from flint.docgen.check import check_documentation
from flint.docgen.model import build_unit_documentation
from flint.lexer import Lexer


class BindingTests(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(text)
            source = flint.parse(str(path)).sources[0]
        rendered = ''.join(source.statements[0][0].head)
        rendered += ''.join(str(t) + ''.join(t.tail) for s in source.statements for t in s)
        self.assertEqual(rendered, text)
        return source

    def test_bindings_are_separate_from_components_and_implementations(self):
        source = self.parse('''module demo
type :: parent
private
procedure(), pointer, nopass :: callback
contains
procedure :: run => implementation, reset
procedure, pass(self), non_overridable :: update => update_impl
generic :: operator(+) => add_scalar, add_array
generic :: assignment(=) => assign
generic :: read(formatted) => read_formatted
final :: finish, finish_array
end type parent
type, extends(parent) :: child
contains
procedure :: run => child_run
end type child
contains
subroutine implementation(self)
class(parent) :: self
end subroutine implementation
end module demo
''')
        module = source.units[0]
        parent, child = module.derived_types
        self.assertEqual([v.name for v in parent.variables], ['callback'])
        self.assertEqual(parent.subprograms, [])
        self.assertEqual([b.name for b in parent.bindings],
                         ['run', 'reset', 'update', 'operator(+)', 'assignment(=)',
                          'read(formatted)', 'finish', 'finish_array'])
        self.assertEqual(parent.bindings[0].targets, ('implementation',))
        self.assertEqual(parent.bindings[1].targets, ('reset',))
        self.assertEqual(parent.bindings[2].attributes,
                         (('pass', '(', 'self', ')'), ('non_overridable',)))
        self.assertEqual(parent.bindings[3].targets, ('add_scalar', 'add_array'))
        self.assertTrue(all(b.public for b in parent.bindings[:-2]))
        self.assertIsNone(parent.bindings[-1].public)
        self.assertEqual(parent.bindings[-1].kind, 'final-binding')
        self.assertEqual([b.name for b in child.bindings], ['run'])
        self.assertEqual(child.bindings[0].targets, ('child_run',))
        self.assertEqual([s.name for s in module.subprograms], ['implementation'])
        self.assertEqual(module.callees, set())
        model = build_unit_documentation(module)
        self.assertEqual(model.derived_types[0].bindings[0].qualified_name, 'demo::parent::run')

    def test_deferred_access_and_documentation_policy(self):
        source = self.parse('''!> Module.
module demo
!> Base.
type, abstract :: base
contains
private
!> Execute work.
procedure(work_interface), deferred, public :: run
procedure, nopass :: helper => implementation
generic, public :: work => run
final :: cleanup
end type base
end module demo
''')
        bindings = source.units[0].derived_types[0].bindings
        self.assertEqual(bindings[0].interface, 'work_interface')
        self.assertEqual(bindings[0].targets, ())
        self.assertEqual([b.public for b in bindings], [True, False, True, None])
        self.assertIn('Execute work.', bindings[0].description)
        self.assertEqual([(i.kind, i.name) for i in check_documentation(source)],
                         [('generic-binding', 'demo::base::work')])
        self.assertEqual([(i.line, i.kind, i.name) for i in check_documentation(source, strict=True)],
                         [(9, 'binding', 'demo::base::helper'),
                          (10, 'generic-binding', 'demo::base::work'),
                          (11, 'final-binding', 'demo::base::cleanup')])

    def test_macro_continuation_association(self):
        source = self.parse('''#define ATTR nopass
!> Module.
module demo
!> State.
type :: state
contains
procedure, ATTR :: missing, &
                  present => impl !< Only present.
generic :: call_all => present !< Public dispatch.
end type state
end module demo
''')
        self.assertEqual([i.name for i in check_documentation(source, strict=True)],
                         ['demo::state::missing'])
        bindings = source.units[0].derived_types[0].bindings
        self.assertEqual(bindings[1].location.line, 8)
        self.assertEqual(bindings[0].attributes, (('nopass',),))

    def test_included_binding_documentation_and_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = root / 'methods.h'
            header.write_text('procedure :: known !< Documented.\nprocedure :: missing\n')
            path = root / 'demo.F90'
            path.write_text('!> Module.\nmodule demo\n!> State.\ntype :: state\ncontains\n'
                            '#include "methods.h"\nend type state\nend module demo\n')
            source = flint.parse(str(path), includes=[str(root)]).sources[0]
            self.assertEqual([(i.path, i.line, i.name)
                              for i in check_documentation(source, strict=True)],
                             [(str(header), 2, 'demo::state::missing')])

    def test_nonbindings_and_incomplete_syntax(self):
        for text in ('procedure(), pointer :: callback', 'procedure(iface), deferred run',
                     'procedure, private run', 'procedure :: run =>',
                     'generic :: operator(+) =>', 'generic :: work => run,', 'final ::'):
            with self.subTest(text=text):
                stmt = next(Lexer(io.StringIO(text + '\n')))
                self.assertEqual(parse_bindings(stmt), ())

    def test_binding_documentation_groups_end_without_leaking(self):
        source = self.parse('''!> Module.
module demo
!> State.
type :: state
contains
!>@{ Shared operations.
procedure :: first, second
procedure :: third
!>@}
procedure :: missing
end type state
end module demo
''')
        self.assertEqual([i.name for i in check_documentation(source, strict=True)],
                         ['demo::state::missing'])


if __name__ == '__main__':
    unittest.main()
