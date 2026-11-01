"""Comment evidence stays attached to its declared entity."""
import io
import unittest

from flint.declarations import declared_entities
from flint.documentation import declaration_comments, entity_comments
from flint.lexer import Lexer


class DeclarationCommentTests(unittest.TestCase):
    def associate(self, text):
        statement = next(Lexer(io.StringIO(text)))
        original = statement.source_line()
        entities = declared_entities(statement)
        blocks = declaration_comments(statement, entities)
        self.assertEqual(statement.source_line(), original)
        return entities, blocks

    def test_continued_entities_do_not_borrow_comments(self):
        entities, blocks = self.associate('real :: a, & !< A [m]\n  b !< B\n!! details\n')
        a, b = [entity_comments(entity, blocks) for entity in entities]
        self.assertEqual(a[0].comments, ('!< A [m]',))
        self.assertEqual(b[0].comments, ('!< B', '!! details'))
        self.assertEqual((a[0].line, b[0].line, b[0].end_line), (1, 2, 3))
        self.assertEqual(a[0].entity_index, entities[0].name_index)

    def test_single_line_list_shares_trailing_comment(self):
        entities, blocks = self.associate('real :: a, b ! Shared [m]\n')
        self.assertIsNone(blocks[0].entity_index)
        self.assertEqual(entity_comments(entities[0], blocks), entity_comments(entities[1], blocks))

    def test_forward_and_backward_evidence_remain_distinct(self):
        entities, blocks = self.associate('!> Shared description\nreal :: a, &\n  b !< B [m]\n')
        a, b = [entity_comments(entity, blocks) for entity in entities]
        self.assertEqual([block.kind for block in a], ['forward'])
        self.assertEqual([block.kind for block in b], ['forward', 'backward'])

    def test_following_plain_comment_is_explicit_candidate(self):
        entities, blocks = self.associate('real :: a\n! Length [m]\n! Details\n')
        self.assertEqual(blocks[0].placement, 'following')
        self.assertEqual(blocks[0].kind, 'plain')
        self.assertEqual(blocks[0].line, 2)

    def test_blank_line_and_forward_marker_end_association(self):
        for text in ('real :: a\n\n! Unrelated [m]\n',
                     'real :: a\n!> Next variable [m]\nreal :: b\n'):
            with self.subTest(text=text):
                _, blocks = self.associate(text)
                self.assertEqual(blocks, ())

    def test_initializer_string_is_not_a_comment(self):
        _, blocks = self.associate("character(*) :: a = '!< [m]' ! Actual\n")
        self.assertEqual(blocks[0].comments, ('! Actual',))

    def test_comments_after_shape_and_initialization(self):
        entities, blocks = self.associate('real :: a(2) = [1,2], & !< A\n b !< B\n')
        self.assertEqual(entity_comments(entities[0], blocks)[0].comments, ('!< A',))
        self.assertEqual(entity_comments(entities[1], blocks)[0].comments, ('!< B',))
