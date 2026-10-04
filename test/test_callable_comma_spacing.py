import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(1, '../')
import flint  # noqa: E402
from report_callable_comma_spacing import (  # noqa: E402
    format_statements,
    statement_contexts,
)


def format_source(text):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'test.F90'
        path.write_text(text)

        project = flint.parse(str(path))
        source = project.sources[0]
        formatted, _ = format_statements(
            path,
            source.statements,
            statement_contexts(source),
            text.splitlines(),
        )

    return formatted


class TestCallableCommaSpacing(unittest.TestCase):
    def test_array_constructor_commas_are_not_changed(self):
        source = '''subroutine demo(a, b)
  real :: a, b
  call f((/1,2,3/),a,b)
end subroutine demo
'''

        self.assertEqual(
            format_source(source),
            '''subroutine demo(a, b)
  real :: a, b
  call f((/1,2,3/), a, b)
end subroutine demo
''',
        )

    def test_component_reference_commas_are_not_changed(self):
        source = '''subroutine demo(CS, I, J)
  integer :: I, J
  if (CS%umask(I,J) == 3) call f(I,J)
end subroutine demo
'''

        self.assertEqual(
            format_source(source),
            '''subroutine demo(CS, I, J)
  integer :: I, J
  if (CS%umask(I,J) == 3) call f(I, J)
end subroutine demo
''',
        )

    def test_write_control_commas_are_not_changed(self):
        source = '''subroutine demo(root, outunit, id, timestep)
  if (root) write(outunit,*) "BEGIN CHECKSUM:: ", id, timestep
end subroutine demo
'''

        self.assertEqual(format_source(source), source)


if __name__ == '__main__':
    unittest.main()
