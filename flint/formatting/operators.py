"""Role-aware operator spacing rules."""
from functools import partial

from flint.formatting.spacing import format_spacing, spacing_edits
from flint.formatting.runner import Change, run_spacing


SKIPPED_OPERATOR_ROLES = {
    'callable_or_subscript_operator', 'concatenation', 'declaration_specifier',
    'do_control_operator', 'exponentiation', 'format_specifier',
    'generic_operator_specifier',
}


def prepare_check(source, strict=False):
    return partial(collect_spacing_edits, strict=strict)


def collect_spacing_edits(statement, strict=False):
    edits = []
    for token in statement.tokens:
        role = getattr(token, 'operator_role', None)
        if role is None or role in SKIPPED_OPERATOR_ROLES:
            continue
        if role == 'unary_operator' and token == '.not.':
            edits.extend(spacing_edits(token, after=' ', minimum=not strict))
        elif role == 'unary_operator':
            edits.extend(spacing_edits(token, after=''))
        elif role == 'binary_operator':
            edits.extend(spacing_edits(token, ' ', ' ', minimum=not strict))
    return edits


def format_statements(path, statements, source_lines=None, strict=False):
    formatted, changes = format_spacing(
        statements, partial(collect_spacing_edits, strict=strict), source_lines,
    )
    return formatted, [Change(path, c.line_number, c.original) for c in changes]


def run(paths, write=False, report=False, diff=False, excludes=(), strict=False):
    return run_spacing(
        paths, checks=(partial(prepare_check, strict=strict),),
        excludes=excludes, write=write, report=report, diff=diff,
    )
