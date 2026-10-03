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

        self.assertEqual(
            {str(name) for name in unit._arrays},
            {'A', 'B', 'C', 'D'},
        )
        self.assertEqual({str(name) for name in unit.callees}, {'f'})


if __name__ == '__main__':
    unittest.main()
