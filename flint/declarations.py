"""Structural grammar for type declarations (J3/24-007 R703, R801-R805).

The grammar identifies token spans, not a fully validated Fortran program.
Selectors, shapes, and initialization expressions are balanced opaque regions;
expression typing, attribute constraints, and scope constraints belong to later
analysis. Procedure declarations and compiler extensions are not recognized.
No tokens or source whitespace are copied or modified.
"""
from dataclasses import dataclass

from flint.token import TokenKind
from flint.locations import statement_locations


def seq(*children):
    return ('sequence', children)


def choice(*children):
    return ('choice', children)


def optional(child):
    return ('optional', child)


def repeat(child):
    return ('repeat', child)


def capture(name, child):
    return ('capture', (name, child))


NAME = ('kind', TokenKind.NAME)
INTEGER = ('kind', TokenKind.INTEGER)
PARENS = ('group', '(')
BRACKETS = ('group', '[')
EXPRESSION = ('expression', None)
CHAR_LENGTH = choice(INTEGER, PARENS)

TYPE_SPEC = choice(
    seq(choice('integer', 'real', 'complex', 'logical'), optional(PARENS)),
    seq('double', 'precision'),
    seq('character', optional(choice(PARENS, seq('*', CHAR_LENGTH)))),
    seq(choice('type', 'class'), PARENS),
)
ATTRIBUTE = choice(
    'public', 'private', 'allocatable', 'asynchronous', 'contiguous', 'external',
    'intrinsic', 'optional', 'parameter', 'pointer', 'protected', 'save',
    'target', 'value', 'volatile',
    seq(choice('dimension', 'intent', 'bind', 'rank'), PARENS),
    seq('codimension', BRACKETS),
)
ENTITY = capture('entity', seq(
    NAME, optional(PARENS), optional(BRACKETS),
    optional(seq('*', CHAR_LENGTH)),
    optional(capture('initialization', seq(choice('=', '=>'), EXPRESSION))),
))
TYPE_DECLARATION = seq(
    capture('type', TYPE_SPEC),
    optional(seq(
        repeat(seq(',', capture('attribute', ATTRIBUTE))),
        capture('separator', '::'),
    )),
    ENTITY, repeat(seq(',', ENTITY)),
)

_CLOSERS = {'(': ')', '[': ']', '(/': '/)'}
_ENDS = frozenset(_CLOSERS.values())
_STARTERS = frozenset(('integer', 'real', 'complex', 'logical', 'double',
                       'character', 'type', 'class'))


@dataclass(frozen=True)
class Declaration:
    """Half-open token spans into the original statement, in source order.

    Spans must be recomputed if tokens are inserted, removed, or replaced.
    They remain valid when only whitespace or analysis roles are edited.
    """

    type_spec: tuple
    attributes: tuple
    entities: tuple
    initializations: tuple
    separator: int | None

    @property
    def prefix_end(self):
        """Index at which the entity list begins."""
        return self.entities[0][0]


def _group_end(tokens, start):
    stack = []
    for index in range(start, len(tokens)):
        token = tokens[index]
        if token in _CLOSERS:
            stack.append(_CLOSERS[token])
        elif token in _ENDS:
            if not stack or stack.pop() != token:
                return -1
            if not stack:
                return index + 1
    return -1


def _match(rule, tokens, start, captures):
    """Interpret a grammar node; failed branches leave no captures behind."""
    mark = len(captures)
    end = _match_node(rule, tokens, start, captures)
    if end < 0:
        del captures[mark:]
    return end


def _match_node(rule, tokens, start, captures):
    if isinstance(rule, str):
        return start + 1 if start < len(tokens) and tokens[start] == rule else -1
    tag, value = rule
    if tag == 'kind':
        return start + 1 if start < len(tokens) and tokens[start].kind is value else -1
    if tag == 'group':
        if start < len(tokens) and tokens[start] == value:
            end = _group_end(tokens, start)
            return end if end > start + 2 else -1
        return -1
    if tag == 'expression':
        end = start
        while end < len(tokens) and tokens[end] != ',':
            if tokens[end] in _CLOSERS:
                end = _group_end(tokens, end)
                if end < 0:
                    return -1
            elif tokens[end] in _ENDS:
                return -1
            else:
                end += 1
        return end if end > start else -1
    if tag == 'sequence':
        end = start
        for child in value:
            end = _match(child, tokens, end, captures)
            if end < 0:
                return -1
        return end
    if tag == 'choice':
        for child in value:
            end = _match(child, tokens, start, captures)
            if end >= 0:
                return end
        return -1
    if tag == 'optional':
        end = _match(value, tokens, start, captures)
        return start if end < 0 else end
    if tag == 'repeat':
        end = start
        while True:
            next_end = _match(value, tokens, end, captures)
            if next_end < 0:
                return end
            if next_end == end:
                raise ValueError('Repeated grammar node must consume a token')
            end = next_end
    if tag == 'capture':
        name, child = value
        end = _match(child, tokens, start, captures)
        if end >= 0:
            captures.append((name, (start, end)))
        return end
    raise ValueError(f'Unknown grammar node: {tag}')


def parse_declaration(tokens, start=0):
    """Recognize a complete type declaration, or return None for fallback.

    ``tokens`` must contain semantic Token objects. ``start`` can skip a label;
    returned spans still refer to the full original token sequence.
    """
    if start < 0 or start >= len(tokens) or tokens[start] not in _STARTERS:
        return None
    captures = []
    if _match(TYPE_DECLARATION, tokens, start, captures) != len(tokens):
        return None
    parts = {'type': [], 'attribute': [], 'entity': [], 'initialization': [],
             'separator': []}
    for name, span in captures:
        parts[name].append(span)
    if parts['initialization'] and not parts['separator']:
        return None  # R801 constraint C806.
    return Declaration(
        parts['type'][0], tuple(parts['attribute']), tuple(parts['entity']),
        tuple(parts['initialization']),
        parts['separator'][0][0] if parts['separator'] else None,
    )


@dataclass(frozen=True)
class DeclaredEntity:
    """One entity in a syntactic declaration, referencing original tokens.

    ``span`` is half-open; ``name_index`` is its first token. ``location`` is
    a TokenLocation or None for a token without a displayed source span.
    This is a source view, not a scope-resolved Variable or a symbol table entry.
    """

    statement: object
    declaration: Declaration
    span: tuple
    location: object

    @property
    def name_index(self):
        return self.span[0]

    @property
    def name(self):
        """Original name token (use str() for source spelling)."""
        return self.statement[self.name_index]

    @property
    def type_tokens(self):
        start, end = self.declaration.type_spec
        return tuple(self.statement[start:end])

    @property
    def attribute_tokens(self):
        return tuple(tuple(self.statement[start:end])
                     for start, end in self.declaration.attributes)


def declared_entities(statement):
    """Return declared entity views, or None for an unrecognized declaration.

    Supports the same standard type declarations as parse_declaration, with or
    without ``::``. Procedure declarations and extensions require caller fallback.
    Locations use displayed statement coordinates, not inferred include origins.
    Recompute views after token insertion/removal and locations after whitespace
    edits. No parsing, file I/O, scope traversal, or token mutation is performed.
    """
    if getattr(statement, 'kind', None) != 'declaration':
        return None
    declaration = parse_declaration(statement.tokens, start=statement.code_index)
    if declaration is None:
        return None
    names = {start for start, end in declaration.entities}
    locations = {location.index: location for location in statement_locations(statement)
                 if location.index in names}
    return tuple(DeclaredEntity(statement, declaration, span, locations.get(span[0]))
                 for span in declaration.entities)
