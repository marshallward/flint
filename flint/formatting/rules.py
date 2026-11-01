"""Named built-in formatting rules, usable from Python or the CLI."""
from functools import partial

from flint.formatting import assignment, callables, indentation, operators


RULES = {
    'assignment-spacing': assignment.prepare_check,
    'operator-spacing': operators.prepare_check,
    'callable-comma-spacing': callables.prepare_check,
}

DIAGNOSTIC_RULES = {
    'indentation': indentation.indentation_issues,
}

ALL_RULES = {**RULES, **DIAGNOSTIC_RULES}


def select_rules(only=None, skip=(), *, strict=False, do_controls=False,
                 excluded_functions=()):
    """Return ordered spacing checks for the shared spacing runner.

    Names are explicit and stable; unknown names are rejected before parsing.
    ``only=None`` selects all spacing rules; an empty iterable selects none.
    Diagnostic-only rules are selected separately by select_diagnostic_rules.
    """
    names = tuple(RULES) if only is None else tuple(only)
    skip = set(skip)
    unknown = (set(names) | skip) - ALL_RULES.keys()
    if unknown:
        raise ValueError('Unknown formatting rule(s): ' + ', '.join(sorted(unknown)))
    checks = {}
    for name in names:
        if name in skip or name not in RULES:
            continue
        options = {'strict': strict}
        if name == 'assignment-spacing':
            options['do_controls'] = do_controls
        elif name == 'callable-comma-spacing':
            options['excluded_functions'] = excluded_functions
        checks[name] = partial(RULES[name], **options)
    return checks


def select_diagnostic_rules(only=None, skip=(), *, strict=False, indent=4):
    """Return source-to-issues checks that cannot yet propose fixes."""
    if not isinstance(indent, int) or isinstance(indent, bool) or indent < 1:
        raise ValueError('Indentation width must be a positive integer')
    names = tuple(ALL_RULES) if only is None else tuple(only)
    skip = set(skip)
    unknown = (set(names) | skip) - ALL_RULES.keys()
    if unknown:
        raise ValueError('Unknown formatting rule(s): ' + ', '.join(sorted(unknown)))
    return {
        name: partial(DIAGNOSTIC_RULES[name], strict=strict, indent=indent)
        for name in names if name in DIAGNOSTIC_RULES and name not in skip
    }
