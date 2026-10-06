import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(1, '../')
import flint  # noqa: E402
from report_operator_spacing import format_statements  # noqa: E402


def format_source(text, strict=False):
    formatted, _ = format_source_with_changes(text, strict=strict)
    return formatted


def format_source_with_changes(text, strict=False):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'test.F90'
        path.write_text(text)

        project = flint.parse(str(path))
        source = project.sources[0]
        formatted, changes = format_statements(
            path,
            source.statements,
            text.splitlines(),
            strict=strict,
        )

    return formatted, changes


class TestOperatorSpacing(unittest.TestCase):
    def test_binary_operators_get_minimum_spacing(self):
        source = '''subroutine demo(a, b, c, ok)
  ok=a+b*c/d<=c.and.a/=b
  if (a+b>c) call f()
end subroutine demo
'''

        self.assertEqual(
            format_source(source),
            '''subroutine demo(a, b, c, ok)
  ok=a + b * c / d <= c .and. a /= b
  if (a + b > c) call f()
end subroutine demo
''',
        )

    def test_concatenation_is_not_changed(self):
        source = '''subroutine demo(a, b, c)
  a = b//c
end subroutine demo
'''

        self.assertEqual(format_source(source), source)

    def test_arithmetic_inside_callable_and_subscript_groups_is_not_changed(self):
        source = '''subroutine demo(a, h, i, j, m_to_L, s_to_T)
  a = f(scale=m_to_L*s_to_T) + h(i+1,j)
  a = (m_to_L*s_to_T)
end subroutine demo
'''

        self.assertEqual(
            format_source(source),
            '''subroutine demo(a, h, i, j, m_to_L, s_to_T)
  a = f(scale=m_to_L*s_to_T) + h(i+1,j)
  a = (m_to_L * s_to_T)
end subroutine demo
''',
        )

    def test_arithmetic_inside_do_loop_control_is_not_changed(self):
        source = '''subroutine demo(isc, iec)
  do i=isc-1,iec+1
    x = i*2
  enddo
end subroutine demo
'''

        self.assertEqual(
            format_source(source),
            '''subroutine demo(isc, iec)
  do i=isc-1,iec+1
    x = i * 2
  enddo
end subroutine demo
''',
        )

    def test_print_star_format_is_not_changed(self):
        source = '''subroutine demo(message)
  print *, "message: " // message
end subroutine demo
'''

        self.assertEqual(format_source(source), source)

    def test_strict_binary_operators_get_exact_spacing(self):
        source = '''subroutine demo(a, b, c)
  a = b  +   c
end subroutine demo
'''

        self.assertEqual(
            format_source(source, strict=True),
            '''subroutine demo(a, b, c)
  a = b + c
end subroutine demo
''',
        )

    def test_unary_signs_do_not_get_following_space(self):
        source = '''subroutine demo(a, b, c)
  a = - b + + c
end subroutine demo
'''

        self.assertEqual(
            format_source(source),
            '''subroutine demo(a, b, c)
  a = -b + +c
end subroutine demo
''',
        )

    def test_logical_not_gets_following_space(self):
        source = '''subroutine demo(a, b)
  if (.not.a.and.b) call f()
end subroutine demo
'''

        self.assertEqual(
            format_source(source),
            '''subroutine demo(a, b)
  if (.not. a .and. b) call f()
end subroutine demo
''',
        )

    def test_exponent_and_operator_spec_are_not_changed(self):
        source = '''module demo
  interface operator(+)
  end interface
contains
  subroutine calc(a, b)
    a = b**2
  end subroutine calc
end module demo
'''

        self.assertEqual(format_source(source), source)

    def test_declaration_prefix_operators_are_not_changed(self):
        source = '''subroutine demo(a)
  character(len=*), intent(in) :: a
  real, dimension(*) :: b
  real :: c=1+2
end subroutine demo
'''

        self.assertEqual(
            format_source(source),
            '''subroutine demo(a)
  character(len=*), intent(in) :: a
  real, dimension(*) :: b
  real :: c=1 + 2
end subroutine demo
''',
        )

    def test_reports_changed_continuation_line(self):
        source = '''subroutine demo(a, b, c, d)
  a = b + &
      c*d
end subroutine demo
'''

        _, changes = format_source_with_changes(source)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].line_number, 3)
        self.assertEqual(changes[0].original, '      c*d')


if __name__ == '__main__':
    unittest.main()
