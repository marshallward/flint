"""Source views for custom declaration checks."""
from pathlib import Path
import tempfile
import unittest

import flint
from flint.declarations import declared_entities


class DeclaredEntityTests(unittest.TestCase):
    def entities(self, declaration):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'demo.F90'
            path.write_text('subroutine demo()\n' + declaration + '\nend subroutine demo\n')
            source = flint.parse(str(path)).sources[0]
            statement = source.statements[1]
            original = statement.source_line()
            result = declared_entities(statement)
            self.assertEqual(statement.source_line(), original)
            return result

    def test_repeated_names_nested_shapes_and_initializers(self):
        entities = self.entities('  real, dimension(x) :: &\n    x, y(2,3) = reshape([1,2,3,4,5,6], [2,3])')
        self.assertEqual([str(entity.name) for entity in entities], ['x', 'y'])
        self.assertEqual([entity.location.line for entity in entities], [3, 3])
        self.assertTrue(all(entity.location.token is entity.name for entity in entities))
        self.assertEqual([str(token) for token in entities[0].type_tokens], ['real'])
        self.assertEqual([str(token) for token in entities[0].attribute_tokens[0]],
                         ['dimension', '(', 'x', ')'])

    def test_no_separator_and_double_precision(self):
        entities = self.entities('  double precision x, y(2)')
        self.assertEqual([str(entity.name) for entity in entities], ['x', 'y'])
        self.assertEqual([str(token) for token in entities[0].type_tokens], ['double', 'precision'])
        self.assertIsNone(entities[0].declaration.separator)

    def test_unsupported_and_non_declaration_return_none(self):
        self.assertIsNone(self.entities('  procedure(callback), pointer :: p'))
        self.assertIsNone(self.entities('  real = 1'))
