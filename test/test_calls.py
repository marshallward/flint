import io
import unittest
from pathlib import Path
import tempfile
from types import SimpleNamespace

from flint.calls import get_callable_symbols
from flint.lexer import Lexer
from flint.token import PToken
import flint


def statement(text):
    return next(Lexer(io.StringIO(text + '\n')))


class TestCallableSymbols(unittest.TestCase):
    def test_host_arrays_are_not_calls_and_local_procedures_can_shadow_them(self):
        text = '''module demo
real :: module_array(3), shared_name(3)
contains
subroutine outer()
real :: host_array(3), value
value = module_array(1) + host_array(1) + real_call()
contains
subroutine inner()
real :: value
value = module_array(1) + host_array(1) + shared_name()
end subroutine inner
function shared_name() result(value)
real :: value
value = module_array(1)
end function shared_name
end subroutine outer
subroutine imported()
use library, only: module_array => work
real :: value
value = module_array()
end subroutine imported
subroutine external_call()
external :: shared_name
real, external :: module_array
real :: value
call shared_name()
value = module_array()
end subroutine external_call
subroutine sibling()
real :: value
value = module_array(1) + shared_name(1) + host_array()
end subroutine sibling
end module demo
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(text)
            project = flint.parse(str(path))
        outer, imported, external, sibling = project.modules[0].subprograms
        inner, shadow = outer.subprograms
        self.assertEqual(outer.callees, {'real_call'})
        self.assertEqual(inner.callees, {'shared_name'})
        self.assertEqual(shadow.callees, set())
        self.assertEqual(imported.callees, {'module_array'})
        self.assertEqual(external.callees, {'shared_name', 'module_array'})
        self.assertEqual(sibling.callees, {'host_array'})
        self.assertEqual(project.graph['module_array'], {'imported', 'external_call'})
        self.assertEqual(project.graph['shared_name'], {'inner', 'external_call'})
        self.assertEqual(project.graph['host_array'], {'sibling'})

    def test_select_case_keywords_are_not_calls(self):
        for text, expected in (
            ('select case (uppercase(value))', ['uppercase']),
            ('choice: select case (case(value))', ['case']),
            ('100 select case (selector())', ['selector']),
            ('case (lower(), upper())', ['lower', 'upper']),
            ('100 case (kind(value)) choice', ['kind']),
            ('case default', []),
        ):
            with self.subTest(text=text):
                self.assertEqual(get_callable_symbols(statement(text), []), expected)

    def test_procedures_named_case_remain_callable(self):
        for text in ('x = case(value)', 'call case(value)',
                     'if (ready()) call case(value)'):
            with self.subTest(text=text):
                self.assertIn('case', get_callable_symbols(statement(text), []))

    def test_block_objects_do_not_swallow_following_procedures(self):
        text = '''module demo
type node
  integer :: value
end type node
contains
subroutine first()
  type(node), pointer :: block
  type(node), target :: other
  block => other
  block%value = compute()
  block
    call inside_block()
  end block
end subroutine first
subroutine second()
  integer :: block(2)
  block(1) = 1
  call second_only()
end subroutine second
end module demo
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(text)
            module = flint.parse(str(path)).modules[0]
        self.assertEqual([str(unit.name) for unit in module.subprograms], ['first', 'second'])
        first, second = module.subprograms
        self.assertEqual(first.statements[-1], ['end', 'subroutine', 'first'])
        self.assertEqual(first.callees, {'compute', 'inside_block'})
        self.assertEqual(second.callees, {'second_only'})

    def test_do_while_is_control_syntax_but_condition_calls_are_retained(self):
        for prefix in ('do', 'do 100', 'do 100,', 'do,', 'loop: do', '10 do'):
            with self.subTest(prefix=prefix):
                line = statement(prefix + ' while (ready(check()) .and. while(value))')
                self.assertEqual(get_callable_symbols(line, []), ['ready', 'check', 'while'])

    def test_procedures_named_while_remain_callable(self):
        for text in ('x = while(value)', 'call while(value)',
                     'if (ready()) call while(value)', 'do i = 1, while(value)'):
            with self.subTest(text=text):
                result = get_callable_symbols(statement(text), [])
                self.assertIn('while', result)

    def test_call_graph_attributes_calls_to_their_own_scope(self):
        text = '''module demo
contains
function lowercase(input)
  character(len=*), intent(in) :: input
  character(len=len(input)) :: lowercase
  lowercase = input
  lowercase(1:1) = 'a'
end function lowercase
subroutine outer()
  call inner()
contains
  subroutine inner()
    real :: local(2)
    local(1) = compute()
    call leaf()
  end subroutine inner
end subroutine outer
end module demo
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(text)
            project = flint.parse(str(path))
        module = project.modules[0]
        lowercase, outer = module.subprograms
        inner = outer.subprograms[0]
        self.assertEqual(module.callees, set())
        self.assertEqual(lowercase.callees, set())
        self.assertEqual(outer.callees, {'inner'})
        self.assertEqual(inner.callees, {'compute', 'leaf'})
        self.assertEqual(project.graph, {'inner': {'outer'}, 'compute': {'inner'}, 'leaf': {'inner'}})

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
