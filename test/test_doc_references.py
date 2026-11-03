"""Cross-file references must resolve symbols before choosing output URLs."""
import importlib.util
from dataclasses import replace
import io
from pathlib import Path
import tempfile
import unittest

import flint
from flint.docgen.model import iter_module_documentation
from flint.docgen.references import HtmlDestinations, ReferenceIndex, anchor
from flint.docgen.rst import write_module, write_unit


SOURCES = {
    'argument_api': '''module argument_api
contains
subroutine run(fn)
real, external :: fn !< Function supplied by the caller.
real, external :: missing_external
real :: x
x = fn(1.) + missing_external(1.)
contains
subroutine inner()
real :: y
y = fn(2.)
end subroutine inner
end subroutine run
end module argument_api
''',
    'array_library': '''module array_library
private
public :: values
real :: values(4), hidden(4)
end module array_library
''',
    'array_facade': '''module array_facade
use array_library, only: exposed => values
end module array_facade
''',
    'array_client': '''module array_client
contains
subroutine run()
use array_library, only: renamed => values, hidden
use array_facade, only: indirect => exposed
real :: x
x = renamed(1) + indirect(1) + hidden(1) + unknown(1)
end subroutine run
subroutine wildcard()
use array_library
real :: x
x = values(1)
end subroutine wildcard
subroutine shadowed()
use array_library, only: values
real :: x
x = values()
contains
function values() result(x)
real :: x
x = 1.
end function values
end subroutine shadowed
subroutine ambiguous()
use array_library, only: work => values
use alpha, only: work => helper
real :: x
x = work(1)
end subroutine ambiguous
end module array_client
''',
    'declared_api': '''module declared_api
private
public :: c_work, plain_work, generic_work
interface
  !> Call the C library.
  function c_work(x) result(y) bind(c, name="library_work")
    real, intent(in) :: x !< Input value.
    real :: y
  end function c_work
  subroutine plain_work()
  end subroutine plain_work
  subroutine private_work()
  end subroutine private_work
end interface
interface generic_work
  subroutine specific_work()
  end subroutine specific_work
end interface
abstract interface
  subroutine callback()
  end subroutine callback
end interface
end module declared_api
''',
    'declared_client': '''module declared_client
use declared_api, only: renamed => c_work, plain_work, private_work, generic_work
contains
subroutine run()
real :: x
x = renamed(1.)
call plain_work()
call private_work()
call generic_work()
end subroutine run
end module declared_client
''',
    'dependency_facade': '''module dependency_facade
use dependency_api, only: exported => remote_work
private
public :: exported
end module dependency_facade
''',
    'dependency_client': '''module dependency_client
contains
subroutine run()
use dependency_facade, only: work => exported
call work()
call unknown()
end subroutine run
subroutine ambiguous()
use dependency_api, only: work => remote_work
use other_api, only: work => other_work
call work()
end subroutine ambiguous
subroutine wildcard()
use dependency_api
call remote_work()
end subroutine wildcard
subroutine shadowed()
use dependency_api, only: helper => remote_work
call helper()
contains
subroutine helper()
end subroutine helper
end subroutine shadowed
end module dependency_client
''',
    'public_view': '''module public_view
private :: helper, specific
!> Public generic with a private implementation.
interface operation
  module procedure specific
end interface operation
contains
subroutine run()
call operation()
call helper()
call specific()
call local_helper()
call missing_external()
contains
subroutine local_helper()
end subroutine local_helper
end subroutine run
subroutine helper()
end subroutine helper
subroutine specific()
end subroutine specific
end module public_view
''',
    'generic_library': '''module generic_library
private
public :: dispatch
!> Dispatch a scalar or an array.
interface dispatch
  module procedure dispatch, dispatch_array
end interface dispatch
interface hidden
  module procedure dispatch_array
end interface hidden
interface operator(+)
  module procedure combine
end interface
interface operator(-)
  module procedure combine
end interface
contains
function combine(x, y) result(z)
real :: x, y, z
z = x + y
end function combine
subroutine dispatch(x)
real :: x
end subroutine dispatch
subroutine dispatch_array(x)
real :: x(:)
end subroutine dispatch_array
end module generic_library
''',
    'generic_facade': '''module generic_facade
use generic_library, only: forwarded => dispatch
end module generic_facade
''',
    'generic_client': '''module generic_client
use generic_facade, only: work => forwarded
use generic_library, only: hidden
contains
subroutine run()
call work(1.)
call hidden(1.)
end subroutine run
end module generic_client
''',
    'alpha': '''module alpha
private
public :: helper, invoke
contains
subroutine helper()
  use beta, only: remote => helper
  call remote()
end subroutine helper
subroutine invoke()
  call helper()
end subroutine invoke
subroutine secret()
end subroutine secret
end module alpha
''',
    'beta': '''module beta
contains
subroutine helper()
  use alpha, only: again => invoke
  call again()
end subroutine helper
end module beta
''',
    'facade': '''module facade
use alpha, only: exposed => helper
private
public :: exposed
end module facade
''',
    'client': '''module client
use alpha, only: first => helper
use beta, only: second => helper
use facade, only: indirect => exposed
contains
subroutine run()
  call first()
  call second()
  call indirect()
  call helper()
end subroutine run
subroutine helper()
end subroutine helper
subroutine host()
  call helper()
contains
  subroutine nested()
    use beta, only: helper
    call helper()
  end subroutine nested
end subroutine host
end module client
''',
    'uncertain': '''module uncertain
contains
subroutine ambiguous()
  use alpha
  use beta
  call helper()
end subroutine ambiguous
subroutine hidden()
  use alpha, only: secret
  call secret()
end subroutine hidden
subroutine empty_import()
  use alpha, only:
  call helper()
end subroutine empty_import
subroutine unavailable()
  use absent_module, only: first => helper
  call first()
end subroutine unavailable
subroutine renamed()
  use alpha, renamed_helper => helper
  call renamed_helper()
  call helper()
end subroutine renamed
end module uncertain
''',
}


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in SOURCES.items():
                (Path(tmp) / (name + '.F90')).write_text(text)
            self.modules = tuple(iter_module_documentation(flint.parse(tmp)))
        self.index = ReferenceIndex(self.modules)

    def test_procedure_arguments_are_not_unresolved_call_targets(self):
        scope = 'argument_api::run'
        unit = self.index.units[scope]
        self.assertEqual(unit.arguments, ('fn',))
        self.assertTrue(self.index.resolve(scope, 'fn').is_argument)
        self.assertTrue(self.index.resolve(scope + '::inner', 'fn').is_argument)
        self.assertEqual([ref.label for ref in self.index.calls[scope]], ['missing_external'])
        self.assertEqual(self.index.calls[scope + '::inner'], ())
        self.assertFalse(any('argument_api::run: fn:' in d for d in self.index.diagnostics))
        output = io.StringIO()
        write_unit(output, unit, references=self.index)
        self.assertIn('**fn**', output.getvalue())
        self.assertIn('Function supplied by the caller.', output.getvalue())
        self.assertNotIn('Calls into', output.getvalue())

    def test_imported_arrays_are_data_not_calls(self):
        for scope, name in [('run', 'renamed'), ('run', 'indirect'), ('wildcard', 'values')]:
            self.assertTrue(self.index.resolve('array_client::' + scope, name).is_data)
        self.assertEqual({ref.label for ref in self.index.calls['array_client::run']},
                         {'hidden', 'unknown'})
        self.assertEqual(self.index.calls['array_client::wildcard'], ())
        self.assertEqual(self.index.resolve('array_client::shadowed', 'values').target,
                         'array_client::shadowed::values')
        self.assertFalse(self.index.resolve('array_client::ambiguous', 'work').is_data)
        self.assertEqual(self.index.resolve('array_client::ambiguous', 'work').reason,
                         'ambiguous reference')
        self.assertTrue(any('array_client::run: unknown:' in d for d in self.index.diagnostics))

    def test_explicit_procedure_interfaces_are_api_targets(self):
        for name, target in [('renamed', 'c_work'), ('plain_work', 'plain_work')]:
            self.assertEqual(self.index.resolve('declared_client::run', name).target,
                             'declared_api::' + target)
        self.assertIsNone(self.index.resolve('declared_client::run', 'private_work').target)
        self.assertIsNone(self.index.resolve('declared_api', 'callback').target)
        self.assertNotIn('declared_api::callback', self.index.units)
        declaration = self.index.units['declared_api::c_work']
        self.assertTrue(declaration.declaration_only)
        self.assertEqual(declaration.summary, 'Call the C library.')
        self.assertIn('bind(c, name="library_work")', declaration.signature)
        self.assertEqual(declaration.variables[0].intent, 'in')
        self.assertEqual(declaration.callees, ())
        self.assertEqual([ref.target for ref in self.index.callers[declaration.qualified_name]],
                         ['declared_client::run'])
        generic = self.index.resolve('declared_client::run', 'generic_work').target
        self.assertEqual(generic, 'declared_api::interface::generic_work')
        self.assertEqual(self.index.implementations[generic][0].target, 'declared_api::specific_work')
        module = next(m for m in self.modules if m.name == 'declared_api')
        output = io.StringIO()
        write_module(output, module, references=self.index)
        self.assertIn('Procedure Interfaces', output.getvalue())
        self.assertIn(anchor('declared_api::c_work'), output.getvalue())

    def test_generic_interfaces_link_without_selecting_an_overload(self):
        target = 'generic_library::interface::dispatch'
        self.assertEqual(self.index.resolve('generic_client::run', 'work').target, target)
        self.assertIsNone(self.index.resolve('generic_client::run', 'hidden').target)
        self.assertEqual(self.index.units[target].summary, 'Dispatch a scalar or an array.')
        self.assertEqual([ref.target for ref in self.index.implementations[target]],
                         ['generic_library::dispatch', 'generic_library::dispatch_array'])
        self.assertEqual([ref.target for ref in self.index.callers[target]], ['generic_client::run'])
        self.assertFalse(self.index.callers['generic_library::dispatch'])
        module = next(m for m in self.modules if m.name == 'generic_library')
        self.assertEqual({entry.name for entry in module.interfaces}, {'dispatch', 'hidden'})
        output = io.StringIO()
        write_module(output, module, references=self.index)
        self.assertIn('Generic Interfaces', output.getvalue())
        self.assertIn('Implementations', output.getvalue())
        self.assertIn(anchor(target), output.getvalue())

    def test_public_call_lists_hide_private_and_internal_procedures(self):
        scope = 'public_view::run'
        generic = 'public_view::interface::operation'
        # Analysis retains the direct calls; only presentation filters them.
        targets = {ref.target for ref in self.index.calls[scope]}
        self.assertIn('public_view::helper', targets)
        self.assertIn('public_view::specific', targets)
        self.assertIn('public_view::run::local_helper', targets)
        self.assertIn(generic, targets)
        self.assertFalse(self.index.is_public('generic_library::dispatch_array'))
        self.assertTrue(self.index.is_public('generic_library::interface::dispatch'))
        output = io.StringIO()
        write_unit(output, self.index.units[scope], references=self.index)
        calls = output.getvalue().split('Calls into\n', 1)[1].split('\n\n', 1)[0]
        self.assertIn(anchor(generic), calls)
        self.assertNotIn('missing_external', calls)
        self.assertTrue(any('missing_external' in message for message in self.index.diagnostics))
        self.assertNotIn('helper', calls)
        self.assertNotIn('specific', calls)
        output = io.StringIO()
        write_unit(output, self.index.units[generic], references=self.index)
        self.assertNotIn('Implementations', output.getvalue())
        self.assertIn('Called by', output.getvalue())
        # A mixed generic still lists its public specific, not its private one.
        output = io.StringIO()
        write_unit(output, self.index.units['generic_library::interface::dispatch'],
                   references=self.index)
        self.assertIn('Implementations', output.getvalue())
        self.assertIn(anchor('generic_library::dispatch'), output.getvalue())
        self.assertNotIn('dispatch_array', output.getvalue())
        self.assertNotIn(anchor('generic_library::dispatch_array'), output.getvalue())

    def test_known_dependencies_are_distinct_from_unknown_calls(self):
        unclassified = self.index.resolve('dependency_client::run', 'work')
        self.assertEqual(unclassified.unindexed_module, 'dependency_api')
        self.assertIn('dependency_api::remote_work', unclassified.reason)
        self.assertIn('possibly external', unclassified.reason)
        self.assertIsNone(unclassified.external)
        index = ReferenceIndex(self.modules, external_modules={
            'dependency_api': 'Example library', 'other_api': 'Other library'})
        ref = index.resolve('dependency_client::run', 'work')
        self.assertIsNone(ref.target)
        self.assertEqual(ref.external.library, 'Example library')
        self.assertEqual(ref.external.module, 'dependency_api')
        self.assertEqual(ref.external.name, 'remote_work')
        self.assertFalse(any('dependency_client::run: work:' in d for d in index.diagnostics))
        for scope, name in [('ambiguous', 'work'), ('wildcard', 'remote_work'), ('run', 'unknown')]:
            ref = index.resolve('dependency_client::' + scope, name)
            self.assertIsNone(ref.external)
            self.assertIsNone(ref.target)
        self.assertEqual(index.resolve('dependency_client::shadowed', 'helper').target,
                         'dependency_client::shadowed::helper')
        output = io.StringIO()
        write_unit(output, index.units['dependency_client::run'], references=index)
        self.assertIn('External calls', output.getvalue())
        self.assertIn('Example library', output.getvalue())
        self.assertIn('dependency_api::remote_work', output.getvalue())
        self.assertNotIn('Calls into', output.getvalue())
        self.assertNotIn('unknown', output.getvalue())
        if importlib.util.find_spec('docutils'):
            from docutils.core import publish_doctree
            warnings = io.StringIO()
            publish_doctree(output.getvalue(), settings_overrides={
                'warning_stream': warnings, 'halt_level': 2})
            self.assertEqual(warnings.getvalue(), '')

    def test_renames_host_scopes_and_reexports(self):
        expected = {
            ('alpha::helper', 'remote'): 'beta::helper',
            ('beta::helper', 'again'): 'alpha::invoke',
            ('client::run', 'first'): 'alpha::helper',
            ('client::run', 'second'): 'beta::helper',
            ('client::run', 'indirect'): 'alpha::helper',
            ('client::run', 'helper'): 'client::helper',
            ('client::host', 'helper'): 'client::helper',
            ('client::host::nested', 'helper'): 'beta::helper',
            ('uncertain::renamed', 'renamed_helper'): 'alpha::helper',
        }
        for (scope, name), target in expected.items():
            with self.subTest(scope=scope, name=name):
                self.assertEqual(self.index.resolve(scope, name).target, target)
        self.assertEqual(
            {ref.target for ref in self.index.callers['alpha::helper']},
            {'alpha::invoke', 'client::run', 'uncertain::renamed'},
        )
        self.assertNotIn('client::host', {ref.target for ref in self.index.callers['beta::helper']})

    def test_ambiguous_private_missing_and_excluded_names_are_not_guessed(self):
        for scope, name in (
            ('uncertain::ambiguous', 'helper'), ('uncertain::hidden', 'secret'),
            ('uncertain::empty_import', 'helper'), ('uncertain::unavailable', 'first'),
            ('uncertain::renamed', 'helper'),
        ):
            with self.subTest(scope=scope):
                reference = self.index.resolve(scope, name)
                self.assertIsNone(reference.target)
                self.assertTrue(reference.reason)
        self.assertEqual(self.index.resolve('uncertain::ambiguous', 'helper').reason,
                         'ambiguous reference')
        self.assertTrue(self.index.diagnostics)

    def test_output_policy_is_separate_from_resolution(self):
        policy = HtmlDestinations(self.index)
        target = self.index.resolve('client::run', 'first').target
        self.assertEqual(policy.destination(target, 'client::run'),
                         'alpha.html#' + anchor('alpha::helper'))
        self.assertEqual(policy.destination(target, 'alpha::invoke'),
                         '#' + anchor('alpha::helper'))
        self.assertNotEqual(anchor('a_b::c'), anchor('a::b_c'))
        module = next(m for m in self.modules if m.name == 'client')
        output = io.StringIO()
        write_module(output, module, references=self.index)
        self.assertNotIn('.html', output.getvalue())

    def test_generic_name_does_not_resolve_to_a_same_named_specific(self):
        modules = tuple(replace(module, opaque_names=('helper',)) if module.name == 'alpha'
                        else module for module in self.modules)
        index = ReferenceIndex(modules)
        self.assertIsNone(index.resolve('client::run', 'first').target)

    @unittest.skipUnless(importlib.util.find_spec('docutils'), 'requires optional docutils renderer')
    def test_every_html_link_has_an_existing_page_and_anchor(self):
        from docutils import nodes
        from docutils.core import publish_doctree

        pages = {}
        for module in self.modules:
            output = io.StringIO()
            write_module(output, module, references=self.index, destinations=HtmlDestinations(self.index))
            warnings = io.StringIO()
            tree = publish_doctree(output.getvalue(), settings_overrides={
                'warning_stream': warnings, 'halt_level': 2,
            })
            self.assertEqual(warnings.getvalue(), '')
            pages[module.name + '.html'] = tree
        for page, tree in pages.items():
            for ref in tree.findall(nodes.reference):
                url = ref['refuri']
                filename, fragment = url.split('#')
                self.assertIn(fragment, pages[filename or page].ids, url)

    @unittest.skipUnless(importlib.util.find_spec('docutils'), 'requires optional docutils renderer')
    def test_large_caller_list_and_undocumented_arguments_render_cleanly(self):
        from docutils.core import publish_doctree
        from flint.docgen.model import UnitDocumentation, VariableDocumentation

        callee = UnitDocumentation('target', 'large::target', 'subroutine',
                                  'subroutine target(x)', '', '',
                                  variables=(VariableDocumentation('x', None, ''),))
        callers = tuple(replace(callee, name=f'caller_{i}', qualified_name=f'large::caller_{i}',
                                signature=f'subroutine caller_{i}(x)', callees=('target',))
                        for i in range(200))
        module = UnitDocumentation('large', 'large', 'module', 'module large', '', '',
                                   procedures=(callee, *callers))
        index = ReferenceIndex((module,))
        output = io.StringIO()
        write_module(output, module, references=index, destinations=HtmlDestinations(index))
        self.assertLess(max(map(len, output.getvalue().splitlines())), 1000)
        self.assertNotIn('Parameters', output.getvalue())
        warnings = io.StringIO()
        publish_doctree(output.getvalue(), settings_overrides={'warning_stream': warnings, 'halt_level': 2})
        self.assertEqual(warnings.getvalue(), '')
