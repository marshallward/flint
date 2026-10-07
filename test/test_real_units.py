import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(1, '../')
import flint  # noqa: E402
from report_real_units import real_unit_issues  # noqa: E402


def issues_for_source(text):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'test.F90'
        path.write_text(text)

        project = flint.parse(str(path))
        return real_unit_issues(project.sources[0])


class TestRealUnits(unittest.TestCase):
    def test_real_without_units_is_reported(self):
        source = '''subroutine demo()
  real :: x ! distance
end subroutine demo
'''

        issues = issues_for_source(source)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].name, 'x')
        self.assertEqual(issues[0].line_number, 2)
        self.assertEqual(issues[0].comments, ('! distance',))

    def test_real_with_bracketed_units_is_not_reported(self):
        source = '''subroutine demo()
  real :: x ! distance [m]
end subroutine demo
'''

        self.assertEqual(issues_for_source(source), [])

    def test_non_real_variables_are_not_reported(self):
        source = '''subroutine demo()
  integer :: n ! count
  logical :: enabled ! flag
end subroutine demo
'''

        self.assertEqual(issues_for_source(source), [])

    def test_shared_comment_units_apply_to_comma_list(self):
        source = '''subroutine demo()
  real :: u, v ! velocity [m s-1]
end subroutine demo
'''

        self.assertEqual(issues_for_source(source), [])

    def test_shared_multiline_comment_units_apply_to_comma_list(self):
        source = '''subroutine demo()
  real :: L_out, L_in ! Nondimensional exchange weight
                       ! for outflow and inflow directions [nondim].
                       ! Active only in finite length-scale mode.
end subroutine demo
'''

        self.assertEqual(issues_for_source(source), [])

    def test_split_variables_with_individual_unit_comments(self):
        source = '''subroutine demo()
  real :: u, & ! zonal velocity [L T-1 ~> m s-1]
          v    ! meridional velocity [L T-1 ~> m s-1]
end subroutine demo
'''

        self.assertEqual(issues_for_source(source), [])

    def test_split_variable_reports_line_with_missing_units(self):
        source = '''subroutine demo()
  real :: u, & ! zonal velocity
          v    ! meridional velocity [L T-1 ~> m s-1]
end subroutine demo
'''

        issues = issues_for_source(source)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].name, 'u')
        self.assertEqual(issues[0].line_number, 2)

    def test_comment_on_continuation_line_reports_that_line(self):
        source = '''subroutine demo()
  real :: u, & ! zonal velocity [m s-1]
          v    ! meridional velocity
end subroutine demo
'''

        issues = issues_for_source(source)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].name, 'v')
        self.assertEqual(issues[0].line_number, 3)

    def test_later_continuation_variable_reports_its_own_line(self):
        source = '''subroutine demo()
  real, pointer :: &
    a => NULL(), & ! first [m]
    b => NULL()    ! second
end subroutine demo
'''

        issues = issues_for_source(source)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].name, 'b')
        self.assertEqual(issues[0].line_number, 4)

    def test_units_in_following_doc_block_are_accepted(self):
        source = '''subroutine demo()
  real ALLOCABLE_, dimension(NIMEMB_PTR_,NJMEM_,NKMEM_) :: visc_rem_u
              !< Both the fraction of the zonal momentum originally in a
              !! layer that remains after a time-step of viscosity, and the
              !! fraction of a time-step worth of a barotropic acceleration
              !! that a layer experiences after viscosity is applied [nondim].
              !! Nondimensional between 0 (at the bottom) and 1 (far above).
end subroutine demo
'''

        self.assertEqual(issues_for_source(source), [])

    def test_doc_comments_are_accepted(self):
        source = '''subroutine demo()
  real :: x !< distance [m]
end subroutine demo
'''

        self.assertEqual(issues_for_source(source), [])

    def test_leading_forward_doc_comment_is_accepted(self):
        source = '''subroutine demo()
  !> A negligible parameter which avoids division by zero, but is too small to
  !! modify physical values [nondim].
  real, parameter :: subroundoff = 1e-30
end subroutine demo
'''

        self.assertEqual(issues_for_source(source), [])

    def test_plain_leading_comment_is_not_accepted(self):
        source = '''subroutine demo()
  ! A plain comment with units [m]
  real :: x
end subroutine demo
'''

        issues = issues_for_source(source)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].name, 'x')
        self.assertEqual(issues[0].comments, ())

    def test_multiline_missing_units_comment_is_reported(self):
        source = '''subroutine demo()
  real :: x ! first line
            ! second line
end subroutine demo
'''

        issues = issues_for_source(source)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].comments, ('! first line', '! second line'))

    def test_plain_following_comment_is_not_associated(self):
        source = '''subroutine demo()
  real :: x
  ! This is about the following declaration.
  integer :: n
end subroutine demo
'''

        issues = issues_for_source(source)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].comments, ())

    def test_indented_following_comment_with_units_is_accepted(self):
        source = '''subroutine demo()
  real :: x
          ! Distance [m]
end subroutine demo
'''

        issues = issues_for_source(source)

        self.assertEqual(issues, [])

    def test_indented_following_comment_without_units_is_reported(self):
        source = '''subroutine demo()
  real :: x
          ! Distance
end subroutine demo
'''

        issues = issues_for_source(source)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].comments, ('! Distance',))

    def test_units_after_pointer_initialization_are_accepted(self):
        source = '''subroutine demo()
  real, pointer :: x => NULL() !< distance [m]
end subroutine demo
'''

        self.assertEqual(issues_for_source(source), [])

    def test_units_after_default_initialization_are_accepted(self):
        source = '''subroutine demo()
  real :: x = 0.0 !< distance [m]
end subroutine demo
'''

        self.assertEqual(issues_for_source(source), [])


if __name__ == '__main__':
    unittest.main()
