import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(1, '../')
from flint.source import Source  # noqa: E402


def parse_source(text):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'test.F90'
        path.write_text(text)

        source = Source()
        source.parse(str(path))

    return source


class TestUnit(unittest.TestCase):
    def test_inline_array_declarations_are_tracked(self):
        source = parse_source('''subroutine demo(i, j)
  integer :: i, j
  real :: A(:), B(10,10), x
  real, dimension(:) :: C, D
  x = A(i) + B(i,j) + C(i) + D(j) + f(i,j)
end subroutine demo
''')

        unit = source.units[0]
        dimensions = {
            str(var.name): var.dimension
            for var in unit.variables
        }

        self.assertEqual(
            dimensions,
            {'i': None, 'j': None, 'A': 1, 'B': 2, 'x': None, 'C': 1, 'D': 1},
        )
        self.assertEqual({str(name) for name in unit.callees}, {'f'})

    def test_class_declaration_does_not_stop_specification_part(self):
        source = parse_source('''subroutine demo(obj, field)
  class(type_name), intent(inout) :: obj
  real, intent(inout) :: field(:,:,:)
  real, allocatable :: work(:,:,:)
  work(:,:,:) = field(:,:,:)
end subroutine demo
''')

        unit = source.units[0]
        dimensions = {
            str(var.name): var.dimension
            for var in unit.variables
        }

        self.assertEqual(
            dimensions,
            {'obj': None, 'field': 3, 'work': 3},
        )
        self.assertEqual({str(name) for name in unit.callees}, set())

    def test_declared_scalar_is_not_callable(self):
        source = parse_source('''subroutine demo(i)
  integer :: i
  real :: value
  value = value(i) + custom_fn(i)
end subroutine demo
''')

        unit = source.units[0]

        self.assertEqual({str(name) for name in unit.callees}, {'custom_fn'})


if __name__ == '__main__':
    unittest.main()
