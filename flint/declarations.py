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


def _compile(rule):
    """Compile a grammar node once; failed matches leave no captures behind.

    Only sequences need rollback: leaves cannot capture, and other combinators
    delegate failure to children. Matchers retain grammar, never parsed tokens.
    """
    if isinstance(rule, str):
        return lambda tokens, start, captures: (
            start + 1 if start < len(tokens) and tokens[start] == rule else -1
        )
    tag, value = rule
    if tag == 'kind':
        return lambda tokens, start, captures: (
            start + 1 if start < len(tokens) and tokens[start].kind is value else -1
        )
    if tag == 'group':
        def group(tokens, start, captures):
            if start < len(tokens) and tokens[start] == value:
                end = _group_end(tokens, start)
                return end if end > start + 2 else -1
            return -1
        return group
    if tag == 'expression':
        def expression(tokens, start, captures):
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
        return expression
    if tag == 'sequence':
        children = tuple(_compile(child) for child in value)
        def sequence(tokens, start, captures):
            mark = len(captures)
            end = start
            for child in children:
                end = child(tokens, end, captures)
                if end < 0:
                    del captures[mark:]
                    return -1
            return end
        return sequence
    if tag == 'choice':
        if all(isinstance(child, str) for child in value):
            literals = frozenset(value)
            return lambda tokens, start, captures: (
                start + 1 if start < len(tokens) and tokens[start] in literals else -1
            )
        children = tuple(_compile(child) for child in value)
        def choose(tokens, start, captures):
            for child in children:
                end = child(tokens, start, captures)
                if end >= 0:
                    return end
            return -1
        return choose
    if tag == 'optional':
        child = _compile(value)
        def optional_match(tokens, start, captures):
            end = child(tokens, start, captures)
            return start if end < 0 else end
        return optional_match
    if tag == 'repeat':
        child = _compile(value)
        def repeated(tokens, start, captures):
            end = start
            while True:
                next_end = child(tokens, end, captures)
                if next_end < 0:
                    return end
                if next_end == end:
                    raise ValueError('Repeated grammar node must consume a token')
                end = next_end
        return repeated
    if tag == 'capture':
        name, child = value
        child = _compile(child)
        def captured(tokens, start, captures):
            end = child(tokens, start, captures)
            if end >= 0:
                captures.append((name, (start, end)))
            return end
        return captured
    raise ValueError(f'Unknown grammar node: {tag}')


_match_declaration = _compile(TYPE_DECLARATION)


def parse_declaration(tokens, start=0):
    """Recognize a complete type declaration, or return None for fallback.

    ``tokens`` must contain semantic Token objects. ``start`` can skip a label;
    returned spans still refer to the full original token sequence. Source-only
    macro anchors are skipped during matching, not removed from the statement.
    """
    if start < 0 or start >= len(tokens):
        return None
    source_indices = None
    if any(getattr(token, 'is_macro_anchor', False) for token in tokens):
        source_indices = [index for index, token in enumerate(tokens)
                          if not getattr(token, 'is_macro_anchor', False)]
        start = sum(index < start for index in source_indices)
        tokens = [tokens[index] for index in source_indices]
    if start >= len(tokens) or tokens[start] not in _STARTERS:
        return None
    captures = []
    if _match_declaration(tokens, start, captures) != len(tokens):
        return None
    parts = {'type': [], 'attribute': [], 'entity': [], 'initialization': [],
             'separator': []}
    for name, span in captures:
        if source_indices is not None:
            span = (source_indices[span[0]], source_indices[span[1] - 1] + 1)
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


def declared_entities(statement, *, locations=None):
    """Return declared entity views, or None for an unrecognized declaration.

    Supports the same standard type declarations as parse_declaration, with or
    without ``::``. Procedure declarations and extensions require caller fallback.
    Locations use displayed statement coordinates, not inferred include origins.
    Recompute views after token insertion/removal and locations after whitespace
    edits. ``locations`` may supply a current index-to-TokenLocation mapping to
    share an existing coordinate walk. No file I/O or token mutation is performed.
    """
    if getattr(statement, 'kind', None) != 'declaration':
        return None
    declaration = parse_declaration(statement.tokens, start=statement.code_index)
    if declaration is None:
        return None
    names = {start for start, end in declaration.entities}
    if locations is None:
        locations = {location.index: location for location in statement_locations(statement)
                     if location.index in names}
    return tuple(DeclaredEntity(statement, declaration, span, locations.get(span[0]))
                 for span in declaration.entities)
