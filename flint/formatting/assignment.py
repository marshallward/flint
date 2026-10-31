"""Assignment and name-value spacing rules."""
from functools import partial

from flint.formatting.spacing import format_spacing, spacing_edits
from flint.formatting.runner import Change, run_spacing


def prepare_check(source, do_controls=False, strict=False):
    return partial(collect_spacing_edits, do_controls=do_controls, strict=strict)


def collect_spacing_edits(statement, do_controls=False, strict=False):
    """Propose spacing without modifying tokens or their source gaps."""
    edits = []
    for token in statement.tokens:
        if token.syntax_role == 'assignment':
            edits.extend(spacing_edits(token, ' ', ' ', minimum=not strict))
        elif token.syntax_role == 'name_value':
            edits.extend(spacing_edits(token, '', ''))
        elif token.syntax_role == 'do_control' and do_controls:
            edits.extend(spacing_edits(token, '', ''))
    if do_controls and statement.is_do_statement():
        for token in statement:
            if str(token) == ',':
                edits.extend(spacing_edits(token, after=''))
    return edits


def format_statements(path, statements, source_lines=None, do_controls=False, strict=False):
    formatted, changes = format_spacing(
        statements, partial(collect_spacing_edits, do_controls=do_controls, strict=strict),
        source_lines,
    )
    return formatted, [Change(path, c.line_number, c.original) for c in changes]


def run(paths, write=False, report=False, diff=False, excludes=(),
        do_controls=False, strict=False):
    return run_spacing(
        paths, checks=(partial(prepare_check, do_controls=do_controls, strict=strict),),
        excludes=excludes, write=write, report=report, diff=diff,
    )
