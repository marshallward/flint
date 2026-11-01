"""Source-level declaration comment associations, without documentation policy."""
from dataclasses import dataclass

from flint.declarations import declared_entities
from flint.locations import statement_locations


@dataclass(frozen=True)
class CommentBlock:
    """A contiguous comment block and its syntactic association.

    ``entity_index=None`` denotes declaration-wide documentation; otherwise it
    is the entity's name-token index. ``placement`` is leading, trailing, or
    following. Following plain comments are candidates, not semantic ownership.
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
        if group and (line > group[-1][0] + 1 or text.startswith(('!>', '!<'))):
            yield group
            group = []
        group.append((line, text))
    if group:
        yield group


def declaration_comments(statement, entities=None):
    """Return comment blocks for a recognized declaration, or None.

    Leading !> blocks are shared by all entities. Comments inside an entity or
    after its separating comma belong to that entity. A trailing comment on a
    single-line entity list is declaration-wide. Comments attached to another
    entity are never used as fallback. Blank lines and a new !> block end a
    trailing/following association. No files are read or tokens changed.
    """
    if entities is None:
        entities = declared_entities(statement)
    if entities is None:
        return None
    if not entities or not getattr(statement, 'source_visible', True):
        return ()
    result = []
    head = statement[0].head
    first_line = statement.line_number
    leading = list(_groups(_comments(head, first_line - sum(s.count('\n') for s in head))))
    for group in reversed(leading):
        if group[0][1].startswith('!>'):
            result.append(CommentBlock(tuple(text for _, text in group), group[0][0],
                                       group[-1][0], 'leading', 'forward', None))
            break
    locations = {loc.index: loc for loc in statement_locations(statement)}
    names = [entity.name_index for entity in entities]
    for index, token in enumerate(statement):
        location = locations.get(index)
        if location is None:
            continue
        owner = next((name for name in reversed(names) if name <= index), None)
        if owner is None:
            continue
        for group in _groups(_comments(token.tail, location.end_line)):
            line, text = group[0]
            if text.startswith('!>') or line > location.end_line + 1:
                break
            placement = 'trailing' if line == location.end_line else 'following'
            kind = 'backward' if text.startswith('!<') else 'plain'
            # Following blocks only apply after the final code token; comments
            # within a continued entity list retain the preceding entity owner.
            shared = index == len(statement) - 1 and (
                placement == 'following' or all(
                    entity.location is not None and entity.location.line == line
                    for entity in entities
                )
            )
            result.append(CommentBlock(tuple(text for _, text in group), line,
                                       group[-1][0], placement, kind,
                                       None if shared else owner))
    return tuple(result)


def entity_comments(entity, blocks):
    """Select entity-specific and declaration-wide blocks in source order."""
    return tuple(block for block in blocks
                 if block.entity_index in (None, entity.name_index))
