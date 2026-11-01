"""Streaming positions in Flint's rendered source, without a retained index.

Positions are one-based character coordinates, not byte offsets or visual tab
columns. Ends are exclusive. Results describe the current source rendering;
after whitespace edits, recompute them. Macro expansions with no displayed text
have no separate source span. Included-file origins are not inferred.
"""
from typing import NamedTuple


class TokenLocation(NamedTuple):
    index: int
    token: object
    line: int
    column: int | None
    end_line: int
    end_column: int | None


def _advance(text, line, column):
    count = text.count('\n')
    if count:
        return line + count, len(text) - text.rfind('\n')
    return line, None if column is None else column + len(text)


def statement_locations(statement, *, column=None):
    """Yield displayed token positions within one statement.

    The statement supplies its first line. ``column`` optionally specifies the
    first token's column. Otherwise a newline in its leading liminals supplies
    the column; without one it remains unknown until a newline is encountered.
    In particular, a semicolon-separated statement cannot determine its initial
    column from its own tokens alone. Use source_locations for exact columns.
    """
    if not statement or not getattr(statement, 'source_visible', True):
        return
    line = statement.line_number
    if line is None:
        raise ValueError('Statement has no source line number')
    if column is None:
        head = ''.join(statement[0].head)
        if '\n' in head:
            column = len(head) - head.rfind('\n')
    yield from _locations(statement, line, column)


def _statement_line_locations(statement):
    """Internal line-only positions for comment association; columns are unset."""
    if not statement or not getattr(statement, 'source_visible', True):
        return
    line = statement.line_number
    if line is None:
        raise ValueError('Statement has no source line number')
    for index, token in enumerate(statement):
        text = str(token)
        end_line = line + text.count('\n')
        if text:
            yield TokenLocation(index, token, line, None, end_line, None)
        line = end_line
        for gap in token.tail:
            line += gap.count('\n')


def _locations(statement, line, column):
    for index, token in enumerate(statement):
        text = str(token)
        end_line, end_column = _advance(text, line, column)
        if text:
            yield TokenLocation(index, token, line, column, end_line, end_column)
        line, column = end_line, end_column
        for gap in token.tail:
            line, column = _advance(gap, line, column)


def source_locations(source):
    """Yield (statement, location) pairs across the complete source rendering.

    Only the first token's head and each token's tail are counted, since adjacent
    head/tail lists share the same source gap. Consuming this iterator retains
    no per-token or per-statement index. The Source must contain the complete
    ordered statement stream, as produced by Source.parse.
    """
    line, column = 1, 1
    first = True
    previous = None
    for statement in source.statements:
        # Some unit streams repeat the identical closing statement object.
        # It denotes one source occurrence, not repeated physical text.
        if statement is previous:
            continue
        previous = statement
        if not statement:
            continue
        if first:
            for gap in statement[0].head:
                line, column = _advance(gap, line, column)
            first = False
        for index, token in enumerate(statement):
            text = str(token)
            end_line, end_column = _advance(text, line, column)
            if text and getattr(statement, 'source_visible', True):
                yield statement, TokenLocation(index, token, line, column,
                                                end_line, end_column)
            line, column = end_line, end_column
            for gap in token.tail:
                line, column = _advance(gap, line, column)
