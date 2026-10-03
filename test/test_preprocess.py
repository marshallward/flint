import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(1, '../')
from flint.lexer import Lexer  # noqa: E402


class TestPreprocess(unittest.TestCase):
    def test_include_expansion_is_not_source_visible(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            include = Path(tmpdir) / 'defs.h'
            include.write_text('x=1\n')

            lexer = Lexer(
                io.StringIO('#include "defs.h"\n'),
                include_paths=[tmpdir],
            )
            statement = next(lexer)

        self.assertFalse(statement.source_visible)
        self.assertEqual(statement.source_path, str(include))
        self.assertEqual(statement.source_line_number, 1)
        self.assertIsNone(statement.expansion_path)
        self.assertEqual(statement.expansion_line_number, 1)


if __name__ == '__main__':
    unittest.main()
