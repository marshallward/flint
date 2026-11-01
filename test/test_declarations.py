import io
import unittest

from flint.declarations import parse_declaration, _compile, capture, choice, optional, repeat, seq
from flint.lexer import Lexer
from flint.token import PToken, Token, semantic_tokens


def tokens(text):
    return next(Lexer(io.StringIO(text + '\n')))


def spelling(statement, span):
    return ''.join(str(token) for token in statement[slice(*span)])


class TestDeclarationGrammar(unittest.TestCase):
    def test_compiled_backtracking_does_not_leak_captures(self):
        rule = seq(
            optional(seq(capture('discarded_optional', 'real'), 'missing')),
            choice(seq(capture('discarded_choice', 'real'), 'missing'), capture('type', 'real')),
            repeat(seq(',', capture('attribute', 'pointer'), '::')),
        )
        captures = []
        statement = tokens('real, pointer, target')
        self.assertEqual(_compile(rule)(statement, 0, captures), 1)
        self.assertEqual(captures, [('type', (0, 1))])

    def test_nested_selectors_attributes_and_entities(self):
        text = 'REAL(KIND=selected_real_kind(12, 200)), DIMENSION(0:n), INTENT(IN) :: A, B'
        statement = tokens(text)
        result = parse_declaration(statement)
        self.assertEqual(spelling(statement, result.type_spec),
                         'REAL(KIND=selected_real_kind(12,200))')
        self.assertEqual([spelling(statement, span) for span in result.attributes],
                         ['DIMENSION(0:n)', 'INTENT(IN)'])
        self.assertEqual([spelling(statement, span) for span in result.entities], ['A', 'B'])
        self.assertEqual(statement[result.separator], '::')
        self.assertEqual(result.prefix_end, result.separator + 1)
        self.assertEqual(statement.source_text(), text + '\n')

    def test_initializers_do_not_split_on_nested_commas(self):
        statement = tokens('integer, parameter :: a(2) = [1, 2], b = size([3, 4])')
        result = parse_declaration(statement)
        self.assertEqual([spelling(statement, span) for span in result.entities],
                         ['a(2)=[1,2]', 'b=size([3,4])'])
        self.assertEqual([spelling(statement, span) for span in result.initializations],
                         ['=[1,2]', '=size([3,4])'])

    def test_declaration_forms(self):
        for text in (
            'integer i, j', 'double precision x', 'logical :: flag',
            'complex :: z = (1.0, 2.0)', 'character(len=*) :: text',
            'character*10 text', 'character :: text*10',
            'type(box(k=4)), pointer :: p => null()', 'class(*) :: object',
            'real, codimension[:], allocatable :: a(:)', 'real :: a(10)[*]',
            'integer, bind(c, name="MiXeD") :: value',
            'integer, parameter :: a(2) = (/ (i, i=1,2) /)',
        ):
            with self.subTest(text=text):
                statement = tokens(text)
                before = [(t.syntax_role, t.operator_role, id(t.head), id(t.tail))
                          for t in statement]
                self.assertIsNotNone(parse_declaration(statement))
                self.assertEqual(statement.source_text(), text + '\n')
                self.assertEqual(before, [(t.syntax_role, t.operator_role, id(t.head), id(t.tail))
                                          for t in statement])

    def test_complete_match_and_fallback(self):
        for text in (
            'real = 1', 'real(i) = 1', 'type :: box', 'type is (box)',
            'real function f(x)', 'procedure(iface), pointer :: f',
            'integer*8 i', 'integer ::', 'integer :: i,',
            'integer :: i =', 'integer i = 1', 'integer, unknown :: i',
            'integer, dimension(2) i', 'integer :: i(2]',
        ):
            with self.subTest(text=text):
                self.assertIsNone(parse_declaration(tokens(text)))

    def test_preprocessing_uses_semantic_text(self):
        statement = tokens('CHARACTER(LEN=*), PARAMETER :: version = "Unknown"')
        expanded = [PToken(t.original, pp='') for t in statement]
        self.assertEqual(parse_declaration(statement), parse_declaration(expanded))
        self.assertEqual(''.join(map(str, expanded)), '')

    def test_macro_anchors_are_skipped_with_original_span_mapping(self):
        text = ('#define ATTR , allocatable\n#define EXTENT :\n'
                'real ATTR, dimension(EXTENT,EXTENT) :: a, b\n')
        statement = next(Lexer(io.StringIO(text)))
        original = statement.source_text()
        gaps = [(id(t.head), tuple(t.head), id(t.tail), tuple(t.tail)) for t in statement]
        result = parse_declaration(statement)
        self.assertIsNotNone(result)
        self.assertEqual([str(statement[start]) for start, end in result.entities], ['a', 'b'])
        self.assertEqual(statement[result.separator], '::')
        self.assertEqual([''.join(semantic_tokens(statement[start:end]))
                          for start, end in result.attributes], ['allocatable', 'dimension(:,:)'])
        self.assertEqual(statement.source_text(), original)
        self.assertEqual(gaps, [(id(t.head), tuple(t.head), id(t.tail), tuple(t.tail)) for t in statement])

    def test_empty_macro_and_macro_type(self):
        for text in ('#define EMPTY\nreal EMPTY :: a\n',
                     '#define TYPE real\nTYPE :: a\n'):
            with self.subTest(text=text):
                statement = next(Lexer(io.StringIO(text)))
                result = parse_declaration(statement)
                self.assertIsNotNone(result)
                self.assertEqual(statement[result.type_spec[0]], 'real')
                self.assertEqual(statement[result.entities[0][0]], 'a')
                self.assertEqual(statement.source_text(), text)

    def test_spans_after_label(self):
        statement = [Token('100'), *tokens('integer :: i')]
        self.assertIsNone(parse_declaration(statement))
        result = parse_declaration(statement, start=1)
        self.assertEqual(result.type_spec, (1, 2))
        self.assertEqual(result.entities, ((3, 4),))

    def test_reparse_after_token_edit(self):
        statement = tokens('integer :: i')
        self.assertIsNotNone(parse_declaration(statement))
        statement.extend([Token(','), Token('j')])
        self.assertEqual(len(parse_declaration(statement).entities), 2)


if __name__ == '__main__':
    unittest.main()
