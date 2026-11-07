"""Presence checks reject omissions without requiring a documentation renderer."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import flint
from flint.docgen.check import check_documentation
from flint.tools.checkdocs import check_docs, source_files


class DocumentationCheckTests(unittest.TestCase):
    def check(self, text, **options):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text(text)
            source = flint.parse(str(path)).sources[0]
            def snapshot():
                return [(str(token), tuple(token.head), tuple(token.tail))
                        for statement in source.statements for token in statement]
            before = snapshot()
            issues = check_documentation(source, **{'strict': True, **options})
            self.assertEqual(snapshot(), before)
            return issues

    def test_entities_and_locations_include_private_but_not_locals(self):
        issues = self.check('''!> A module.
module Demo
private
integer :: missing
type :: state
real :: component
end type state
contains
subroutine work(x)
real :: x
real :: temporary
end subroutine work
end module Demo
''')
        self.assertEqual([(i.line, i.kind, i.name) for i in issues], [
            (4, 'variable', 'Demo::missing'), (5, 'type', 'Demo::state'),
            (6, 'component', 'Demo::state::component'), (9, 'subroutine', 'Demo::work')])

    def test_member_comments_do_not_document_enclosing_or_following_scopes(self):
        text = '''module demo
integer :: value !< A value, not a module or type description.
type :: state
integer :: field !< A field, not a type description.
end type state
contains
subroutine work()
integer :: local !< A local, not a procedure description.
end subroutine work
end module demo
'''
        self.assertEqual([(i.kind, i.name) for i in self.check(text, strict=False)],
                         [('type', 'demo::state')])
        self.assertEqual([(i.kind, i.name) for i in self.check(text, strict=True)],
                         [('module', 'demo'), ('type', 'demo::state'), ('subroutine', 'demo::work')])

    def test_scope_header_and_footer_documentation_still_count(self):
        for text in (
                '!! Module description.\nmodule demo\nend module demo\n',
                'module demo !< Module description.\nend module demo\n',
                'module demo\n!< Module description.\nend module demo\n',
                'module demo\ninteger :: x !< Value.\n!> Module description.\nend module demo\n',
                'module demo\ninteger :: x !< Value.\n\n!! Module description.\nend module demo\n'):
            with self.subTest(text=text):
                self.assertEqual(self.check(text, strict=True), [])

    def test_relaxed_mode_still_checks_contents(self):
        text = '''module demo
integer :: missing
type :: state
real :: component
end type state
contains
subroutine run(x)
real :: x
end subroutine run
real function value()
value = 0.
end function value
end module demo
'''
        relaxed = self.check(text, strict=False, arguments=True)
        self.assertEqual({i.name for i in relaxed}, {
            'demo::missing', 'demo::state', 'demo::state::component',
            'demo::run::x'})
        strict = self.check(text, strict=True, arguments=True)
        self.assertEqual({i.name for i in strict} - {i.name for i in relaxed},
                         {'demo', 'demo::run', 'demo::value'})

    def test_precise_associations_do_not_borrow_continuation_docs(self):
        issues = self.check('''!> A module.
module demo
!> Forward documentation shared by this declaration.
integer :: first, second
integer :: third, fourth !< Shared same-line documentation.
integer :: fifth, &
           sixth !< Documents sixth, not fifth.
integer :: seventh !<
! Ordinary comments do not satisfy the requirement.
integer :: eighth
end module demo
''')
        self.assertEqual([i.name for i in issues], ['demo::fifth', 'demo::seventh', 'demo::eighth'])
        self.assertEqual([i.line for i in issues], [6, 8, 10])

    def test_declaration_groups_end_without_leaking(self):
        issues = self.check('''!> A module.
module demo
!>@{ Shared diagnostic IDs.
integer :: first, second
integer :: third
!>@}
integer :: missing
end module demo
''')
        self.assertEqual([i.name for i in issues], ['demo::missing'])

    def test_macro_initializer_retains_trailing_and_following_docs(self):
        issues = self.check('''#define POSIX_SIGUSR1 10
!> Signals.
module posix
integer, parameter :: SIGUSR1 = POSIX_SIGUSR1
  !< Signal number for SIGUSR1 (user-defined signal 1)
integer, parameter :: other = POSIX_SIGUSR1 !< Another documented value.
integer :: missing, &
           last = POSIX_SIGUSR1 !< Only last is documented.
integer :: undocumented = POSIX_SIGUSR1
end module posix
''')
        self.assertEqual([i.name for i in issues], ['posix::missing', 'posix::undocumented'])

    def test_macro_generated_variable_keeps_its_semantic_name(self):
        issues = self.check('''#define NAME generated
!> A module.
module demo
integer :: NAME
end module demo
''')
        self.assertEqual([i.name for i in issues], ['demo::generated'])

    def test_program_description_is_strict_only_but_contents_are_checked(self):
        text = '''program demo
contains
real function value()
value = 0.
end function value
end program demo
'''
        self.assertEqual(self.check(text, strict=False), [])
        self.assertEqual([i.name for i in self.check(text, strict=True)], ['demo', 'demo::value'])

    def test_all_function_descriptions_are_strict_only(self):
        text = '''module demo
private
public :: exported
contains
real function exported()
exported = 0.
contains
real function internal_helper()
internal_helper = 0.
end function internal_helper
end function exported
real function hidden()
hidden = 0.
end function hidden
end module demo
module default_public
private :: hidden
contains
real function visible()
visible = 0.
end function visible
real function hidden()
hidden = 0.
end function hidden
end module default_public
real function external_function()
external_function = 0.
end function external_function
'''
        relaxed = self.check(text, strict=False)
        self.assertEqual(relaxed, [])
        strict_functions = {i.name for i in self.check(text, strict=True) if i.kind == 'function'}
        self.assertEqual(strict_functions, {
            'demo::exported', 'default_public::visible', 'external_function',
            'demo::exported::internal_helper', 'demo::hidden', 'default_public::hidden'})

    def test_abstract_type_description_is_deferred_but_components_are_not(self):
        text = '''!> A module.
module demo
type, abstract :: base
integer :: missing_component
end type base
type, extends(base) :: concrete
end type concrete
end module demo
'''
        relaxed = self.check(text, strict=False)
        self.assertEqual({i.name for i in relaxed}, {'demo::base::missing_component', 'demo::concrete'})
        strict = self.check(text, strict=True)
        self.assertEqual({i.name for i in strict} - {i.name for i in relaxed}, {'demo::base'})

    def test_only_private_module_parameters_are_deferred(self):
        text = '''!> A module.
module demo
private
public :: exported
integer, parameter :: hidden = 1, exported = 2
integer, parameter, public :: inline_public = 3
integer :: private_state
end module demo
!> Another module.
module other
private :: named_private
integer, parameter :: named_private = 1, default_public = 2
integer, parameter, private :: inline_private = 3
end module other
'''
        relaxed = self.check(text, strict=False)
        self.assertEqual({i.name for i in relaxed}, {
            'demo::exported', 'demo::inline_public', 'demo::private_state', 'other::default_public'})
        strict = self.check(text, strict=True)
        self.assertEqual({i.name for i in strict} - {i.name for i in relaxed}, {
            'demo::hidden', 'other::named_private', 'other::inline_private'})

    def test_argument_check_is_opt_in_and_catches_implicit_arguments(self):
        text = '''!> Update the value.
subroutine run(x, y, implicit_arg)
real :: x !< Input.
real :: y
real :: local
end subroutine run
'''
        self.assertEqual(self.check(text), [])
        self.assertEqual({i.name for i in self.check(text, arguments=True)},
                         {'run::y', 'run::implicit_arg'})

    def test_named_interface_and_body_are_checked(self):
        issues = self.check('''!> A module.
module demo
interface generic
  subroutine work()
  end subroutine work
end interface generic
end module demo
''')
        self.assertEqual([(i.kind, i.name) for i in issues],
                         [('interface', 'demo::generic'), ('subroutine', 'demo::work')])

    def test_missing_include_is_not_a_successful_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text('!> A module.\nmodule demo\n#include "absent.h"\nend module demo\n')
            with self.assertRaisesRegex(ValueError, 'Incomplete parse'):
                check_docs([str(path)])

    def test_nested_include_docs_and_physical_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = root / 'inner.h'
            header.write_text('! Header.\ninteger :: documented !< A value.\ninteger :: missing\n')
            (root / 'outer.h').write_text('#include "inner.h"\n')
            path = root / 'demo.F90'
            text = '!> A module.\nmodule demo\n#include "outer.h"\ninteger :: mdl !< Module name.\nend module demo\n'
            path.write_text(text)
            source = flint.parse(str(path), includes=[str(root)]).sources[0]
            issues = check_documentation(source)
            self.assertEqual([(i.path, i.line, i.name) for i in issues],
                             [(str(header), 3, 'demo::missing')])
            self.assertEqual(check_documentation(source, defer_includes=[header]), [])
            self.assertEqual(check_documentation(source, strict=True, defer_includes=[header]), issues)
            # Deferring the parent header must not suppress a nested header.
            self.assertEqual(check_documentation(source, defer_includes=[root / 'outer.h']), issues)
            self.assertEqual(path.read_text(), text)

    def test_excluded_trees_and_symlink_targets_are_not_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'vendor/nested').mkdir(parents=True)
            (root / 'src').mkdir()
            external = root / 'vendor/nested/library.F90'
            external.write_text('not Fortran')
            (root / 'src/link.F90').symlink_to(external)
            local = root / 'src/local.F90'
            local.write_text('!> A module.\nmodule demo\nend module demo\n')
            self.assertEqual(source_files([root], [root / 'vendor']), [local])
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(check_docs([root], excludes=[root / 'vendor']), 0)

    def test_cli_exit_codes_and_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            command = [sys.executable, '-m', 'flint', 'check-docs', str(path)]
            missing = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(missing.returncode, 2)
            path.write_text('module demo\ninteger :: x\nend module demo\n')
            failed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(failed.returncode, 1)
            self.assertIn(f'{path}:2: missing-documentation: variable demo::x', failed.stdout)
            path.write_text('!> A module.\nmodule demo\ninteger :: x !< Value.\nend module demo\n')
            passed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(passed.returncode, 0, passed.stderr)
            self.assertEqual(passed.stdout, '')
            path.write_text('module demo\ncontains\nsubroutine run()\nend subroutine run\nend module demo\n')
            relaxed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(relaxed.returncode, 0, relaxed.stderr)
            strict = subprocess.run([*command, '--strict'], capture_output=True, text=True)
            self.assertEqual(strict.returncode, 1)
            self.assertIn('module demo', strict.stdout)
            self.assertIn('subroutine demo::run', strict.stdout)
