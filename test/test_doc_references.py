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
from flint.docgen.rst import write_module


SOURCES = {
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
