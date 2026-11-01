"""Source-level declaration comment associations, without documentation policy."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from flint.declarations import declared_entities
from flint.locations import _statement_line_locations


_active_pass = ContextVar('flint_documentation_pass', default=None)


@contextmanager
def documentation_pass():
    """Reuse the latest declaration analysis during a read-only checking pass.

    Use as a context manager or decorator around code inspecting
    ``variable.documentation``. Do not edit source tokens or statement metadata
    inside the pass. Only one declaration is retained, independent of project
    size; leaving the pass (including on exceptions) discards that snapshot.
    Nested passes have independent snapshots. Outside a pass, lookups always
    analyze current source, so edits are reflected immediately.
    """
    snapshot = []
    token = _active_pass.set(snapshot)
    try:
        yield
    finally:
        _active_pass.reset(token)
        snapshot.clear()


@dataclass(frozen=True)
class CommentBlock:
    """A contiguous comment block and its syntactic association.

    ``entity_index=None`` denotes declaration-wide documentation; otherwise it
    is the entity's name-token index. ``placement`` is leading, trailing, or
    following. A block shared by a subset of entities has one association per
    entity. Following plain comments are candidates, not semantic ownership.
    ``kind`` is forward (!>), backward (!<), or plain. Lines are one-based.
    """

    comments: tuple
    line: int
    end_line: int
    placement: str
    kind: str
    entity_index: int | None


def _comments(gap, line):
    for item in gap:
        if item.startswith('!'):
            yield line, item
        line += item.count('\n')


def _groups(comments):
    group = []
    for line, text in comments:
        if group and (line > group[-1][0] + 1 or text.startswith('!>')
                      or (text.startswith('!<') and group[0][1].startswith('!>'))):
            yield group
            group = []
        group.append((line, text))
    if group:
        yield group


def declaration_comments(statement, entities=None):
    """Return comment blocks for a recognized declaration, or None.

    Leading !> blocks are shared by all entities. Comments inside an entity or
    after its separating comma belong to that entity. A comment after a group
    of entities on one physical line is shared by that group, including within
    continued declarations. Comments on other lines are not used as fallback.
    Blank lines and a new !> block end a
    trailing/following association. No files are read or tokens changed.
    """
    return _declaration_documentation(statement, entities)[1]


def _declaration_documentation(statement, entities=None):
    snapshot = _active_pass.get()
    if snapshot is None or entities is not None:
        return _analyze_declaration(statement, entities)
    if snapshot and snapshot[0] is statement:
        return snapshot[1]
    result = _analyze_declaration(statement)
    snapshot[:] = [statement, result]
    return result


def _analyze_declaration(statement, entities=None):
    """Build internal entity views and comment evidence using only line numbers."""
    if entities is None and getattr(statement, 'kind', None) != 'declaration':
        return None, None
    locations = {loc.index: loc for loc in _statement_line_locations(statement)}
    if entities is None:
        entities = declared_entities(statement, locations=locations)
    if entities is None:
        return None, None
    if not entities or not getattr(statement, 'source_visible', True):
        return entities, ()
    result = []
    head = statement[0].head
    first_line = statement.line_number
    leading = list(_groups(_comments(head, first_line - sum(s.count('\n') for s in head))))
    for group in reversed(leading):
        if group[0][1].startswith('!>'):
            result.append(CommentBlock(tuple(text for _, text in group), group[0][0],
                                       group[-1][0], 'leading', 'forward', None))
            break
    names = [entity.name_index for entity in entities]
    ends = {entity.name_index: entity.span[1] for entity in entities}
    for index, token in enumerate(statement):
        location = locations.get(index)
        if location is None:
            continue
        for group in _groups(_comments(token.tail, location.end_line)):
            owner = next((name for name in reversed(names) if name <= index), None)
            if owner is None:
                break
            line, text = group[0]
            if text.startswith('!>') or line > location.end_line + 1:
                break
            placement = 'trailing' if line == location.end_line else 'following'
            kind = 'backward' if any(text.startswith('!<') for _, text in group) else 'plain'
            # Following blocks only apply after the final code token; comments
            # within a continued entity list retain the preceding entity owner.
            shared = index == len(statement) - 1 and (
                placement == 'following' or all(
                    entity.location is not None and entity.location.line == line
                    for entity in entities
                )
            )
            owners = [None] if shared else [owner]
            if not shared and index >= ends[owner] - 1:
                # Once an entity is complete, a comment after it (or its comma)
                # also documents earlier names on that physical code line.
                # Comments inside an unfinished initializer/shape stay local.
                owners = [name for name in names if name == owner or (
                    name <= index and name in locations
                    and locations[name].line == location.end_line
                )]
            for entity_index in owners:
                result.append(CommentBlock(tuple(text for _, text in group), line,
                                           group[-1][0], placement, kind, entity_index))
    return entities, tuple(result)


def entity_comments(entity, blocks):
    """Select entity-specific and declaration-wide blocks in source order."""
    return tuple(block for block in blocks
                 if block.entity_index in (None, entity.name_index))
