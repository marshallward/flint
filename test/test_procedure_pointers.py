"""Procedure pointers are declarations, not their target implementations."""
from pathlib import Path
import tempfile
import unittest

import flint
from flint.docgen.check import check_documentation
from flint.docgen.model import _scope_metadata


class ProcedurePointerTests(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(text)
            source = flint.parse(str(path)).sources[0]
            rendered = ''.join(source.statements[0][0].head)
            rendered += ''.join(str(t) + ''.join(t.tail)
                                for s in source.statements for t in s)
            self.assertEqual(rendered, text)
            return source

    def test_module_and_component_metadata(self):
        source = self.parse('''module demo
private
procedure(handler), pointer, save :: prior => null(), next => implementation
type :: state
private
procedure(), nopass, pointer, public :: cleanup => null()
contains
procedure :: run => implementation
end type state
end module demo
''')
        module = source.units[0]
        self.assertEqual([v.name for v in module.variables], ['prior', 'next'])
        prior, following = module.variables
        self.assertEqual(prior.type, 'procedure')
        self.assertFalse(prior.is_array)
        self.assertEqual(prior.attributes, [('pointer',), ('save',)])
        self.assertEqual(prior.declaration.type_tokens, ('procedure', '(', 'handler', ')'))
        self.assertEqual(following.declaration_tokens, ('next', '=>', 'implementation'))
        self.assertEqual(prior.location.line, 3)
        dtype = module.derived_types[0]
        self.assertEqual([v.name for v in dtype.variables], ['cleanup'])
        self.assertEqual(dtype.variables[0].attributes, [('nopass',), ('pointer',), ('public',)])
        _, default, access = _scope_metadata(dtype)
        self.assertFalse(default)
        self.assertTrue(dict(access)['cleanup'])

    def test_documentation_and_policy_do_not_exempt_pointers(self):
        source = self.parse('''!> A module.
module demo
private
procedure(handler), pointer :: documented
!< The previous handler.
procedure(handler), pointer :: missing
!> State.
type :: state
procedure(), nopass, pointer :: cleanup => null() !< Cleanup callback.
procedure(), nopass, pointer :: absent => null()
end type state
contains
!> Work.
subroutine work(callback)
procedure(handler), pointer, intent(in) :: callback
procedure(), pointer :: local
end subroutine work
end module demo
''')
        for strict in (False, True):
            issues = check_documentation(source, strict=strict)
            self.assertEqual([(i.line, i.kind, i.name) for i in issues], [
                (6, 'variable', 'demo::missing'), (10, 'component', 'demo::state::absent')])
        issues = check_documentation(source, arguments=True)
        self.assertEqual([i.name for i in issues],
                         ['demo::missing', 'demo::state::absent', 'demo::work::callback'])

    def test_macro_and_continuation_comment_association(self):
        source = self.parse('''#define ATTR pointer
!> A module.
module demo
procedure(), ATTR :: missing, &
                    documented => null() !< Only this callback.
end module demo
''')
        self.assertEqual([i.name for i in check_documentation(source)], ['demo::missing'])

    def test_included_pointer_keeps_header_location_and_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = root / 'callbacks.h'
            header.write_text('procedure(), pointer :: good !< A callback.\n'
                              'procedure(), pointer :: missing\n')
            path = root / 'demo.F90'
            path.write_text('!> A module.\nmodule demo\n#include "callbacks.h"\nend module demo\n')
            source = flint.parse(str(path), includes=[str(root)]).sources[0]
            issues = check_documentation(source)
            self.assertEqual([(i.path, i.line, i.name) for i in issues],
                             [(str(header), 2, 'demo::missing')])


if __name__ == '__main__':
    unittest.main()
