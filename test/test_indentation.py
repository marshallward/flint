"""Regression tests for the Flint-based indentation reporter.

Run with ``python -m unittest discover -s test -p 'test_*.py'``.
"""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import flint

from flint.formatting.indentation import indentation_issues
from flint.cli import parse as main
from flint.tools.format import format_statements


class IndentationTests(unittest.TestCase):
    """Exercise real Flint parsing, including physical source locations."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'sample.F90'

    def check(self, text, strict=False):
        self.path.write_text(text, encoding='utf-8')
        project = flint.parse(str(self.path))
        return indentation_issues(project.sources[0], strict=strict, indent=2)

    def test_nested_blocks_and_module_scope(self):
        self.assertEqual(self.check(
            'module sample\n'
            'implicit none\n'
            'contains\n'
            'subroutine work(a)\n'
            '  logical :: a\n'
            '  integer :: i\n'
            '  if (a) then\n'
            '    do i=1,3\n'
            '      call task()\n'
            '    enddo\n'
            '  else if (.not. a) then\n'
            '    call other()\n'
            '  else\n'
            '    call last()\n'
            '  endif\n'
            'end subroutine work\n'
            'end module sample\n'
        ), [])

    def test_bad_block_indent_does_not_cascade(self):
        issues = self.check(
            'subroutine work(a)\n'
            '  logical :: a\n'
            '   if (a) then\n'
            '    call task()\n'
            '  endif\n'
            'end subroutine work\n'
        )
        self.assertEqual([issue.line_number for issue in issues], [3])
        self.assertIn('expected 2 spaces, found 3', issues[0].message)

    def test_continuation_minimum_and_alignment(self):
        self.assertEqual(self.check(
            'subroutine work()\n'
            '  call task(1, &\n'
            '      2, &\n'
            '             3)\n'
            'end subroutine work\n'
        ), [])
        issues = self.check(
            'subroutine work()\n'
            '  call task(1, &\n'
            '    2)\n'
            'end subroutine work\n'
        )
        self.assertEqual([issue.line_number for issue in issues], [3])
        self.assertIn('at least 6 spaces', issues[0].message)

    def test_single_line_if_action_exception(self):
        self.assertEqual(self.check(
            'subroutine work(a)\n'
            '  logical :: a\n'
            '  if (a) &\n'
            '    call task(1, &\n'
            '      2)\n'
            '  if (a) &\n'
            '      call task()\n'
            'end subroutine work\n'
        ), [])

    def test_multiline_condition_is_not_if_action(self):
        issues = self.check(
            'subroutine work(a)\n'
            '  logical :: a\n'
            '  if (a .and. &\n'
            '    a) &\n'
            '    call task()\n'
            'end subroutine work\n'
        )
        self.assertEqual([issue.line_number for issue in issues], [4])

    def test_block_if_has_no_action_exception(self):
        issues = self.check(
            'subroutine work(a)\n'
            '  logical :: a\n'
            '  if (a &\n'
            '    ) then\n'
            '    call task()\n'
            '  endif\n'
            'end subroutine work\n'
        )
        self.assertEqual([issue.line_number for issue in issues], [4])

    def test_documentation_comments_are_not_continuation_code(self):
        self.assertEqual(self.check(
            '!> Procedure documentation\n'
            'subroutine work()\n'
            '  integer :: a !< Variable documentation\n'
            '  !! More variable documentation\n'
            '  ! Ordinary comment\n'
            '\n'
            '  call task(1, & ! Trailing comment\n'
            '  !! Documentation between continuation lines\n'
            '\n'
            '      2)\n'
            '  a = 1\n'
            'end subroutine work\n'
        ), [])

    def test_comment_does_not_end_continuation(self):
        issues = self.check(
            'subroutine work()\n'
            '  call task(1, &\n'
            '  ! Comment\n'
            '  2)\n'
            'end subroutine work\n'
        )
        self.assertEqual([issue.line_number for issue in issues], [4])

    def test_documented_declaration_allows_two_spaces_unless_strict(self):
        text = (
            'subroutine work()\n'
            '  real :: &\n'
            '    x, & !< First variable [m]\n'
            '    y    !< Second variable [m]\n'
            'end subroutine work\n'
        )
        self.assertEqual(self.check(text), [])
        issues = self.check(text, strict=True)
        self.assertEqual([issue.line_number for issue in issues], [3, 4])

    def test_undocumented_declarations_allow_two_spaces_unless_strict(self):
        declarations = (
            'real ::', 'integer ::', 'logical ::', 'complex ::',
            'character(len=10) ::', 'double precision ::',
            'type(item) ::', 'class(item), allocatable ::',
            'procedure(callback), pointer ::', 'real',
        )
        for declaration in declarations:
            with self.subTest(declaration=declaration):
                text = (
                    'module sample\n'
                    'type :: item\n'
                    '  integer :: i\n'
                    'end type item\n'
                    'contains\n'
                    'subroutine work()\n'
                    f'  {declaration} &\n'
                    '    x\n'
                    'end subroutine work\n'
                    'end module sample\n'
                )
                self.assertEqual(self.check(text), [])
                issues = self.check(text, strict=True)
                self.assertEqual([issue.line_number for issue in issues], [8])

    def test_declaration_continuation_minimum(self):
        for strict in (False, True):
            with self.subTest(strict=strict):
                issues = self.check(
                    'subroutine work()\n'
                    '  real :: &\n'
                    '   x\n'
                    'end subroutine work\n', strict=strict,
                )
                self.assertEqual([issue.line_number for issue in issues], [3])
                self.assertEqual(self.check(
                    'subroutine work()\n'
                    '  real :: &\n'
                    '      x, &\n'
                    '           y\n'
                    'end subroutine work\n', strict=strict,
                ), [])

    def test_strict_does_not_change_if_exception_or_non_declarations(self):
        text = (
            'subroutine work(a)\n'
            '  logical :: a\n'
            '  if (a) &\n'
            '    call task()\n'
            '  call task(1, &\n'
            '    2)\n'
            'end subroutine work\n'
        )
        for strict in (False, True):
            with self.subTest(strict=strict):
                issues = self.check(text, strict=strict)
                self.assertEqual([issue.line_number for issue in issues], [6])

    def test_typed_function_header_is_not_a_declaration_continuation(self):
        issues = self.check(
            'real function work( &\n'
            '  x)\n'
            '  real :: x\n'
            '  work = x\n'
            'end function work\n'
        )
        self.assertEqual([issue.line_number for issue in issues], [2])

    def test_strict_option_reaches_reporter_from_command_line(self):
        text = 'subroutine work()\n  real :: &\n    x\nend subroutine work\n'
        self.path.write_text(text, encoding='utf-8')
        for strict in (False, True):
            with self.subTest(strict=strict):
                config = self.path.parent / 'flint.toml'
                config.write_text('[format.indentation]\nwidth = 2\n')
                args = ['flint', 'format', str(self.path), '--only', 'indentation',
                        '--config', str(config)]
                if strict:
                    args.append('--strict')
                with patch('sys.argv', args), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), int(strict))
        self.assertEqual(self.path.read_text(encoding='utf-8'), text)

    def test_leading_continuation_markers(self):
        self.assertEqual(self.check(
            'subroutine work()\n'
            '  call task(1, &\n'
            '      & 2)\n'
            'end subroutine work\n'
        ), [])

    def test_continued_string(self):
        issues = self.check(
            'subroutine work()\n'
            "  call task('first &\n"
            "    &second')\n"
            'end subroutine work\n'
        )
        self.assertEqual([issue.line_number for issue in issues], [3])

    def test_semicolon_blocks_and_named_construct(self):
        self.assertEqual(self.check(
            'subroutine work()\n'
            '  integer :: i\n'
            '  outer: do i=1,3; call task()\n'
            '    call other(); call last()\n'
            '  end do outer\n'
            'end subroutine work\n'
        ), [])

    def test_select_case(self):
        self.assertEqual(self.check(
            'subroutine work(i)\n'
            '  integer :: i\n'
            '  select case (i)\n'
            '    case (1)\n'
            '      call task()\n'
            '    case default\n'
            '      call other()\n'
            '  end select\n'
            'end subroutine work\n'
        ), [])

    def test_paired_loop_headers_share_visual_indent(self):
        self.assertEqual(self.check(
            'subroutine work()\n'
            '  integer :: i, j\n'
            '  do j=1,3; do i=1,3\n'
            '    call task()\n'
            '  enddo; enddo\n'
            'end subroutine work\n'
        ), [])

    def test_interface_and_typed_function(self):
        self.assertEqual(self.check(
            'module sample\n'
            'interface\n'
            '  real function work(a)\n'
            '    real :: a\n'
            '  end function work\n'
            'end interface\n'
            'end module sample\n'
        ), [])

    def test_derived_type(self):
        self.assertEqual(self.check(
            'module sample\n'
            'type :: item\n'
            '  integer :: i\n'
            'end type item\n'
            'end module sample\n'
        ), [])

    def test_type_contains_aligns_with_header_and_bindings_with_fields(self):
        self.assertEqual(self.check(
            'module sample\n'
            'type, public :: item\n'
            '  integer :: i\n'
            'contains\n'
            '  procedure, public :: work\n'
            'end type item\n'
            'contains\n'
            'subroutine work(self)\n'
            '  class(item) :: self\n'
            'end subroutine work\n'
            'end module sample\n'
        ), [])

    def test_indented_type_contains_and_unindented_bindings_are_reported(self):
        issues = self.check(
            'module sample\n'
            'type, public :: item\n'
            '  integer :: i\n'
            '  contains\n'
            'procedure, public :: work\n'
            'end type item\n'
            'end module sample\n'
        )
        self.assertEqual([issue.line_number for issue in issues], [4, 5])
        self.assertEqual(issues[0].message, 'expected 0 spaces, found 2')
        self.assertEqual(issues[1].message, 'expected 2 spaces, found 0')

    def test_type_without_fields_keeps_contains_aligned_with_header(self):
        self.assertEqual(self.check(
            'module sample\n'
            'type, public :: item\n'
            'contains\n'
            '  procedure, nopass :: work\n'
            'end type item\n'
            'contains\n'
            'subroutine work()\n'
            'end subroutine work\n'
            'end module sample\n'
        ), [])

    def test_four_space_type_layout_is_still_reported(self):
        issues = self.check(
            'module sample\n'
            '    type, public :: item\n'
            '        integer :: i\n'
            '       contains\n'
            '        procedure, public :: work\n'
            '    end type item\n'
            'end module sample\n'
        )
        self.assertEqual([issue.line_number for issue in issues], [2, 3, 4, 5, 6])
        self.assertEqual(issues[0].message, 'expected 0 spaces, found 4')
        for issue in (issues[1], issues[3]):
            self.assertTrue(issue.message.startswith('expected 2 spaces,'))
        self.assertEqual(issues[2].message, 'expected 0 spaces, found 7')
        self.assertEqual(issues[-1].message, 'expected 0 spaces, found 4')

    def test_internal_function_preserves_enclosing_procedure_indent(self):
        self.assertEqual(self.check(
            'module sample\n'
            'contains\n'
            'subroutine outer()\n'
            '  integer :: n\n'
            '  n = 1\n'
            '  contains\n'
            '  real function first_deriv(r, dx, order)\n'
            '    real, intent(in) :: r(-3:3), dx\n'
            '    integer, intent(in) :: order\n'
            '    if (order == 6) then\n'
            '      first_deriv = r(1) / dx\n'
            '    else\n'
            '      first_deriv = r(-1) / dx\n'
            '    endif\n'
            '  end function first_deriv\n'
            '  subroutine inner()\n'
            '    call task()\n'
            '  end subroutine inner\n'
            'end subroutine outer\n'
            'subroutine next_routine()\n'
            '  call task()\n'
            'end subroutine next_routine\n'
            'end module sample\n'
        ), [])

    def test_internal_subroutine_in_function(self):
        self.assertEqual(self.check(
            'real function outer()\n'
            '  outer = 1.0\n'
            '  contains\n'
            '  subroutine inner()\n'
            '    call task()\n'
            '  end subroutine inner\n'
            'end function outer\n'
        ), [])

    def test_keyword_named_call_does_not_open_procedure(self):
        self.assertEqual(self.check(
            'subroutine work\n'
            '  call function(1)\n'
            '  call task()\n'
            'end subroutine work\n'
        ), [])

    def test_tabs(self):
        issues = self.check('subroutine work()\n\tcall task()\nend subroutine work\n')
        self.assertEqual(len(issues), 1)
        self.assertIn('not tabs', issues[0].message)

    def test_preprocessor_inactive_branch(self):
        self.assertEqual(self.check(
            'subroutine work()\n'
            '#if 0\n'
            'call ignored()\n'
            '#else\n'
            '  call task()\n'
            '#endif\n'
            'end subroutine work\n'
        ), [])

    def test_report_exit_status_and_no_writes(self):
        text = 'subroutine work()\n call task()\nend subroutine work\n'
        self.path.write_text(text, encoding='utf-8')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = format_statements([str(self.path)], only=['indentation'], indent=2)
        self.assertEqual(result, 1)
        self.assertIn(f'{self.path}:2:', output.getvalue())
        self.assertEqual(self.path.read_text(encoding='utf-8'), text)
        self.path.write_text(text.replace('\n call', '\n  call'), encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(format_statements([str(self.path)], only=['indentation'], indent=2), 0)


if __name__ == '__main__':
    unittest.main()
