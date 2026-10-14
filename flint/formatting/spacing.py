"""Non-mutating whitespace proposals and rendering for source style checks.

Liminals are lists of strings containing the material between source tokens:
whitespace, comments, continuation markers, and newlines. Adjacent tokens share
the same list: the left token's tail is the right token's head, not a copy.
Edits use id(list) to identify that shared gap, rather than its contents or
either token. Rendering looks up that ID in a replacement dictionary, so either
side of a gap finds the same proposal without modifying the original list.
Proposals belong to the parsed source that produced them; they are not file
offsets and should not be reused with a different parse.
"""

from typing import NamedTuple


class LineChange(NamedTuple):
    """Description of one physical source line with spacing changes."""

    line_number: int
    original: str


class SpacingEdit(NamedTuple):
    """An immutable replacement proposal for one shared liminal list.

    liminal_id is Python's id() of the original list, not a source offset.
    original and replacement snapshot the strings, not the list identity.
    """

    liminal_id: int
    original: tuple[str, ...]
    replacement: tuple[str, ...]


def simple_liminals(liminals) -> bool:
    """Return true for simple same-line whitespace."""
    return all(
        (item == '' or item.isspace()) and '\n' not in item
        for item in liminals
    )


def propose_edit(liminals, replacement):
    """Return an edit only if the replacement differs from the original.

    Identify the gap by id(liminals): adjacent token head/tail attributes refer
    to the same list. Equal contents in separate gaps must not share an edit.
    Keep the original parsed lists alive while using these proposals; object
    IDs are only meaningful during their lifetime and may later be reused.
    """
    original = tuple(liminals)
    replacement = tuple(replacement)
    if ''.join(original) == ''.join(replacement):
        return []
    return [SpacingEdit(id(liminals), original, replacement)]


def spacing_edits(token, before=None, after=None, minimum=False):
    """Propose simple spacing on either side, without modifying the token."""
    edits = []
    for liminals, requested in ((token.head, before), (token.tail, after)):
        if requested is None or not simple_liminals(liminals):
            continue
        if minimum and ''.join(liminals):
            continue
        edits.extend(propose_edit(liminals, [requested] if requested else []))
    return edits


def edit_replacements(edits):
    """Return a dictionary mapping liminal-list IDs to replacement tuples.

    Proposals from either side of a shared head/tail gap have the same key.
    Identical proposals coalesce; incompatible replacements are rejected.
    """
    replacements = {}
    for edit in edits:
        if (
            edit.liminal_id in replacements
            and replacements[edit.liminal_id] != edit.replacement
        ):
            raise ValueError('Conflicting spacing edits for the same source gap')
        replacements[edit.liminal_id] = edit.replacement
    return replacements


def liminal_text(liminals, replacements):
    """Render a gap using its proposed replacement, or its original strings.

    replacements is keyed by id() of the original liminal lists. Looking up
    the list identity lets either neighboring token find the same edit; using
    the contents as a key would conflate unrelated gaps with equal whitespace.
    The lookup falls back to liminals when that gap has no proposed edit.
    """
    return ''.join(replacements.get(id(liminals), liminals))


def statement_text(statement, replacements):
    """Render a statement with proposed gaps, leaving its tokens untouched."""
    if not statement:
        return ''
    output = [liminal_text(statement[0].head, replacements)]
    for token in statement:
        output.extend((str(token), liminal_text(token.tail, replacements)))
    return ''.join(output)


def statement_line(statement, replacements):
    """Render proposed spacing in the same form as Statement.source_line().

    Omit earlier lines attached to the first token's head, but retain the
    indentation on the statement's starting line and any continuation lines.
    Strip trailing newline characters. Despite the name, the result can span
    multiple physical lines; comparing it with the original source_line()
    identifies which lines would change without modifying parsed tokens.
    """
    if not statement:
        return ''
    head = liminal_text(statement[0].head, replacements)
    prefix = head.rsplit('\n', 1)[-1] if head else ''
    return (prefix + statement_text(statement, replacements)[len(head):]).rstrip('\n')


def render(statements, edits=()) -> str:
    """Render parsed source, optionally applying proposals only to output."""
    replacements = edit_replacements(edits)
    output = []
    first = True
    for statement in statements:
        if not statement:
            continue
        if first:
            output.append(liminal_text(statement[0].head, replacements))
            first = False
        for token in statement:
            output.extend((str(token), liminal_text(token.tail, replacements)))
    return ''.join(output)


def changed_lines(statement, original, formatted, source_lines=None):
    """Yield original physical lines whose proposed rendering differs."""
    original_lines = original.splitlines()
    formatted_lines = formatted.splitlines()
    for offset, original_line in enumerate(original_lines):
        if offset >= len(formatted_lines) or original_line != formatted_lines[offset]:
            line_number = statement.line_number + offset
            if source_lines and line_number <= len(source_lines):
                yield line_number, source_lines[line_number - 1]
            else:
                yield line_number, original_line


def format_spacing(statements, collect_edits, source_lines=None):
    """Collect proposals and return formatted output plus line diagnostics."""
    statements = list(statements)
    edits = []
    for statement in statements:
        if getattr(statement, 'source_visible', True) and statement:
            edits.extend(collect_edits(statement))
    replacements = edit_replacements(edits)
    changes = []
    for statement in statements:
        if not getattr(statement, 'source_visible', True) or not statement:
            continue
        if statement_text(statement, replacements) != statement.source_text():
            for line_number, original in changed_lines(
                statement,
                statement.source_line(),
                statement_line(statement, replacements),
                source_lines,
            ):
                changes.append(LineChange(line_number, original))
    return render(statements, edits), changes
