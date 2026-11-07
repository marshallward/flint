"""Dummy procedure declarations retain their interfaces and comment evidence."""
from pathlib import Path
import tempfile
import unittest

import flint
from flint.docgen.check import check_documentation
from flint.token import semantic_tokens


class ProcedureArgumentTests(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(text)
            source = flint.parse(str(path)).sources[0]
        rendered = ''.join(source.statements[0][0].head)
        rendered += ''.join(str(t) + ''.join(t.tail) for s in source.statements for t in s)
        self.assertEqual(rendered, text)
        return source

    def test_metadata_and_optional_argument(self):
        source = self.parse('''!> Execute a test.
subroutine execute(test, cleanup, other)
procedure(test_interface) :: test !< The test to execute.
procedure(), optional :: cleanup !< Optional cleanup action.
procedure(real(kind=8)) other !< A real-valued callback.
call test()
if (present(cleanup)) call cleanup()
end subroutine execute
''')
        unit = source.units[0]
        self.assertEqual([v.name for v in unit.variables], ['test', 'cleanup', 'other'])
        self.assertTrue(all(v.is_procedure and not v.is_pointer and not v.is_array for v in unit.variables))
        self.assertEqual(unit.variables[0].declaration.type_tokens, ('procedure', '(', 'test_interface', ')'))
        self.assertEqual(unit.variables[1].attributes, [('optional',)])
        self.assertIsNone(unit.variables[2].declaration.declaration.separator)
        self.assertEqual(check_documentation(source, arguments=True, strict=True), [])

    def test_argument_checks_use_declaration_comments_and_locations(self):
        source = self.parse('''!> Execute a test.
subroutine execute(documented, missing)
procedure() :: documented
!< The test callback.
procedure() :: missing
end subroutine execute
''')
        self.assertEqual(check_documentation(source), [])
        self.assertEqual(check_documentation(source, strict=True), [])
        self.assertEqual([(i.line, i.kind, i.name) for i in check_documentation(source, arguments=True)],
                         [(5, 'argument', 'execute::missing')])

    def test_dummy_procedure_shadows_host_data_in_call_analysis(self):
        source = self.parse('''module demo
real :: callback(10)
contains
real function evaluate(callback)
procedure(real) :: callback
evaluate = callback()
end function evaluate
end module demo
''')
        worker = source.units[0].subprograms[0]
        self.assertEqual(worker.callees, {'callback'})

    def test_macro_continuations_do_not_share_unrelated_comments(self):
        source = self.parse('''#define IFACE callback_interface
!> Execute callbacks.
subroutine execute(missing, present)
procedure(IFACE) :: missing, &
                   present !< Only this callback.
end subroutine execute
''')
        self.assertEqual([i.name for i in check_documentation(source, arguments=True)], ['execute::missing'])
        type_tokens = list(semantic_tokens(source.units[0].variables[0].declaration.type_tokens))
        self.assertEqual(type_tokens[2], 'callback_interface')

    def test_nonpointer_external_procedure_is_not_a_data_variable_policy(self):
        source = self.parse('''!> Module.
module demo
procedure(iface) :: external_callback
procedure(iface), pointer :: stored_callback
end module demo
''')
        self.assertEqual([(i.kind, i.name) for i in check_documentation(source)],
                         [('variable', 'demo::stored_callback')])
        self.assertEqual([(i.kind, i.name) for i in check_documentation(source, strict=True)],
                         [('procedure', 'demo::external_callback'), ('variable', 'demo::stored_callback')])

    def test_include_procedure_argument_comments_and_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = root / 'callbacks.h'
            header.write_text('procedure() :: documented !< A callback.\nprocedure() :: missing\n')
            path = root / 'demo.F90'
            path.write_text('!> Execute.\nsubroutine execute(documented, missing)\n'
                            '#include "callbacks.h"\nend subroutine execute\n')
            source = flint.parse(str(path), includes=[str(root)]).sources[0]
            self.assertEqual([(i.path, i.line, i.name)
                              for i in check_documentation(source, arguments=True)],
                             [(str(header), 2, 'execute::missing')])


if __name__ == '__main__':
    unittest.main()
