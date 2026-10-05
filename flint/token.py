"""flint Token and PToken classes.

``Token`` is a representation of the Fortran token, designed as a subclass of
the Python string.  The usual (string) value corresponds to the original
lexeme, but it also contains a ``head`` and ``tail`` which contain the adjacent
"liminal" tokens.

Equality and hash tests use the case-insensitive forms, like good little
Fortran tokens.

(By "liminal" I mean the whitespace tokens between the semantic tokens.)

The PToken is a subclass of Token, which is produced from preprocessing and
stores its original pre-processed value as ``pp``, which it uses for roundtrip
parsing output.

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from enum import Enum


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
        tok = str.__new__(cls, value, *args)
        tok.head = []
        tok.tail = []
        tok.kind = kind if kind is not None else classify_lexeme(value)
        tok.syntax_role = None
        tok.operator_role = None
        return tok

    def __eq__(self, other):
        return self.lower() == other.lower()

    def __hash__(self):
        return hash(str(self).lower())

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


class PToken(Token):
    """Preprocessed Token which prints its origin macro."""
    def __init__(self, value='', pp=''):
        self.pp = pp

    def __str__(self):
        return ''.join(self.pp)
