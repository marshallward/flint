"""Source-backed type-bound procedures, generic bindings, and finalizers.

These are associations on a type, not data components or executable procedures.
Targets are names, not resolved calls; inheritance and dispatch are not inferred.
"""
from dataclasses import dataclass

from flint.declarations import NAME, PARENS, _compile, capture, choice, optional, repeat, seq
from flint.document import docstrip
from flint.documentation import declaration_comments, entity_comments
from flint.locations import statement_locations


ATTRIBUTE = choice(choice('public', 'private', 'nopass', 'deferred', 'non_overridable'),
                   seq('pass', optional(PARENS)))
SPECIFIC = seq(
    'procedure', optional(seq('(', capture('interface', NAME), ')')),
    repeat(seq(',', capture('attribute', ATTRIBUTE))),
    optional(capture('separator', '::')),
    capture('entity', seq(NAME, optional(seq('=>', NAME)))),
    repeat(seq(',', capture('entity', seq(NAME, optional(seq('=>', NAME)))))),
)
GENERIC_NAME = choice(seq(choice('operator', 'assignment', 'read', 'write'), PARENS), NAME)
GENERIC = seq(
    'generic', optional(seq(',', capture('attribute', choice('public', 'private')))),
    capture('separator', '::'),
    capture('entity', seq(capture('name', GENERIC_NAME), '=>', NAME, repeat(seq(',', NAME)))),
)
FINAL = seq('final', optional(capture('separator', '::')),
            capture('entity', NAME), repeat(seq(',', capture('entity', NAME))))
_MATCHERS = {kind: _compile(rule) for kind, rule in
             (('procedure', SPECIFIC), ('generic', GENERIC), ('final', FINAL))}


@dataclass
class Binding:
    """One locally declared association, retaining its original statement span."""
    name: str
    kind: str
    targets: tuple
    interface: str | None
    attributes: tuple
    public: bool | None
    statement: object
    span: tuple
    group_description: str = ''

    @property
    def name_index(self):
        return self.span[0]

    @property
    def location(self):
        return next((loc for loc in statement_locations(self.statement)
                     if loc.index == self.name_index), None)

    @property
    def documentation(self):
        # Included statements retain the original physical comment evidence.
        stmt = getattr(self.statement, 'origin_statement', self.statement)
        siblings = parse_bindings(stmt)
        entity = next(binding for binding in siblings if binding.name_index == self.name_index)
        return entity_comments(entity, declaration_comments(stmt, siblings))

    @property
    def description(self):
        return self.group_description or docstrip(
            [comment for block in self.documentation for comment in block.comments
             if not comment.startswith(('!>@{', '!>@}'))], oneline=False)


def parse_bindings(statement, *, default_public=True):
    """Return bindings for a complete statement, or () for unsupported syntax.

    Call only within a derived type's binding part (after CONTAINS). Semantic
    tokens are matched without discarding source-only macro anchors or whitespace.
    """
    indices = [i for i, token in enumerate(statement)
               if not getattr(token, 'is_macro_anchor', False)]
    tokens = [statement[i] for i in indices]
    if not tokens or tokens[0] not in _MATCHERS:
        return ()
    captures = []
    if _MATCHERS[tokens[0]](tokens, 0, captures) != len(tokens):
        return ()
    parts = {key: [span for tag, span in captures if tag == key]
             for key in ('attribute', 'interface', 'entity', 'name', 'separator')}
    if (parts['attribute'] or parts['interface']) and not parts['separator']:
        return ()
    attributes = tuple(tuple(t[:] for t in tokens[a:b]) for a, b in parts['attribute'])
    access = next((a[0] == 'public' for a in attributes if a[0] in ('public', 'private')),
                  default_public)
    interface = tokens[parts['interface'][0][0]][:] if parts['interface'] else None
    kind = {'procedure': 'binding', 'generic': 'generic-binding', 'final': 'final-binding'}[tokens[0]]
    if kind == 'final-binding':
        access = None  # Finalization procedures have no binding accessibility.
    result = []
    for start, end in parts['entity']:
        if kind == 'generic-binding':
            a, b = parts['name'][0]
            name = ''.join(t[:] for t in tokens[a:b])
            targets = tuple(t[:] for t in tokens[b + 1:end] if t != ',')
        else:
            name = tokens[start][:]
            targets = () if ('deferred',) in attributes else (tokens[end - 1][:],)
        result.append(Binding(name, kind, targets, interface, attributes, access, statement,
                              (indices[start], indices[end - 1] + 1)))
    return tuple(result)
