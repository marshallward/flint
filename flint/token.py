"""flint Token and PToken classes.

``Token`` is a representation of the Fortran token, designed as a subclass of
the Python string.  The underlying string is normalized to lowercase, except
for string literals. ``original`` retains the original lexeme for ``str()``
output. It also contains a ``head`` and ``tail`` which contain the adjacent
"liminal" tokens.

Equality and hashing are inherited from ``str``; compare with normalized
strings. Slicing and joining operate on the semantic string, not its original
spelling. Use ``str(token)`` for source output.

(By "liminal" I mean the whitespace tokens between the semantic tokens.)

The PToken is a subclass of Token, which is produced from preprocessing and
stores its original pre-processed value as ``pp``, which it uses for roundtrip
parsing output.

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from enum import Enum
from functools import lru_cache


class TokenKind(Enum):
    """Lexical categories for semantic tokens.

    Whitespace, comments, and preprocessor lines are stored as liminals on
    adjacent tokens, so this enum only classifies values that become Token
    instances.
    """
    NAME = 'name'
    INTEGER = 'integer'
    REAL = 'real'
    STRING = 'string'
    ASSIGNMENT = 'assignment'
    POINTER_ASSIGNMENT = 'pointer_assignment'
    ARITHMETIC_OPERATOR = 'arithmetic_operator'
    CONCATENATION_OPERATOR = 'concatenation_operator'
    RELATIONAL_OPERATOR = 'relational_operator'
    LOGICAL_OPERATOR = 'logical_operator'
    DEFINED_OPERATOR = 'defined_operator'
    LOGICAL_LITERAL = 'logical_literal'
    DELIMITER = 'delimiter'
    SEPARATOR = 'separator'
    COMPONENT_SELECTOR = 'component_selector'
    UNKNOWN = 'unknown'


ARITHMETIC_OPERATORS = {'+', '-', '*', '/', '**'}
RELATIONAL_OPERATORS = {'==', '/=', '<', '>', '<=', '>='}
LOGICAL_OPERATORS = {'.and.', '.or.', '.eqv.', '.neqv.', '.not.'}
LOGICAL_LITERALS = {'.true.', '.false.'}
DELIMITERS = {'(', ')', '[', ']', '{', '}'}
SEPARATORS = {',', ':', '::'}


@lru_cache(maxsize=4096)
def classify_lexeme(value):
    """Return the coarse token kind for a Scanner lexeme."""
    if not value:
        return TokenKind.UNKNOWN
    if value[0].isalpha() or value[0] == '_':
        return TokenKind.NAME
    if value[0].isdigit() or (
        value[0] == '.' and len(value) > 1 and value[1].isdigit()
    ):
        if any(char in value for char in '.eEdD'):
            return TokenKind.REAL
        return TokenKind.INTEGER
    if value[0] in ('"', "'"):
        return TokenKind.STRING
    lower = value.lower()
    if lower in LOGICAL_LITERALS:
        return TokenKind.LOGICAL_LITERAL
    if lower in LOGICAL_OPERATORS:
        return TokenKind.LOGICAL_OPERATOR
    if value.startswith('.') and value.endswith('.') and len(value) > 2:
        return TokenKind.DEFINED_OPERATOR
    if value == '=':
        return TokenKind.ASSIGNMENT
    if value == '=>':
        return TokenKind.POINTER_ASSIGNMENT
    if value in ARITHMETIC_OPERATORS:
        return TokenKind.ARITHMETIC_OPERATOR
    if value == '//':
        return TokenKind.CONCATENATION_OPERATOR
    if value in RELATIONAL_OPERATORS:
        return TokenKind.RELATIONAL_OPERATOR
    if value in DELIMITERS:
        return TokenKind.DELIMITER
    if value in SEPARATORS:
        return TokenKind.SEPARATOR
    if value == '%':
        return TokenKind.COMPONENT_SELECTOR
    return TokenKind.UNKNOWN


class Token(str):
    # NOTE: Immutable types generally need __new__ implementations
    #   (At least that is my understanding...)
    def __new__(cls, value='', *args, **kwargs):
        kind = kwargs.pop('kind', None)
        original = str.__new__(str, value, *args)
        kind = kind if kind is not None else classify_lexeme(original)
        normalized = original if kind is TokenKind.STRING else original.lower()
        tok = str.__new__(cls, normalized)
        tok.original = original
        tok.head = []
        tok.tail = []
        tok.kind = kind
        tok.syntax_role = None
        tok.operator_role = None
        return tok

    def __str__(self):
        return self.original

    @property
    def is_name(self):
        return self.kind == TokenKind.NAME

    @property
    def is_number(self):
        return self.kind in (TokenKind.INTEGER, TokenKind.REAL)

    @property
    def is_string(self):
        return self.kind == TokenKind.STRING

    @property
    def is_operator(self):
        return self.kind in (
            TokenKind.ASSIGNMENT,
            TokenKind.POINTER_ASSIGNMENT,
            TokenKind.ARITHMETIC_OPERATOR,
            TokenKind.CONCATENATION_OPERATOR,
            TokenKind.RELATIONAL_OPERATOR,
            TokenKind.LOGICAL_OPERATOR,
            TokenKind.DEFINED_OPERATOR,
        )

    @property
    def is_punctuation(self):
        return self.kind in (
            TokenKind.DELIMITER,
            TokenKind.SEPARATOR,
            TokenKind.COMPONENT_SELECTOR,
        )

    @property
    def is_logical_literal(self):
        return self.kind == TokenKind.LOGICAL_LITERAL


def _token_from_lexeme(value, head):
    """Build a plain lexer token with its existing leading whitespace list.

    The lexer supplies a scanned string and shares adjacent token liminals.
    Avoid constructing and immediately discarding an empty head list, and
    avoid the general constructor's argument handling on this hot path.
    """
    kind = classify_lexeme(value)
    normalized = value if kind is TokenKind.STRING else value.lower()
    token = str.__new__(Token, normalized)
    token.original = value
    token.head = head
    token.tail = []
    token.kind = kind
    token.syntax_role = None
    token.operator_role = None
    return token


class PToken(Token):
    """Preprocessed Token which prints its origin macro."""
    def __init__(self, value='', pp=''):
        self.pp = pp

    def __str__(self):
        return ''.join(self.pp)
