"""Named built-in formatting rules, usable from Python or the CLI."""
from functools import partial

from flint.formatting import assignment, callables, operators


RULES = {
    'assignment-spacing': assignment.prepare_check,
    'operator-spacing': operators.prepare_check,
    'callable-comma-spacing': callables.prepare_check,
}


def select_rules(only=None, skip=(), *, strict=False, do_controls=False,
                 excluded_functions=()):
    """Return ordered name-to-check mappings for the shared runner.

    Names are explicit and stable; unknown names are rejected before parsing.
    ``only=None`` selects all built-ins, while an empty iterable selects none.
    """
    names = tuple(RULES) if only is None else tuple(only)
    skip = set(skip)
    unknown = (set(names) | skip) - RULES.keys()
    if unknown:
        raise ValueError('Unknown formatting rule(s): ' + ', '.join(sorted(unknown)))
    checks = {}
    for name in names:
        if name in skip:
            continue
        options = {'strict': strict}
        if name == 'assignment-spacing':
            options['do_controls'] = do_controls
        elif name == 'callable-comma-spacing':
            options['excluded_functions'] = excluded_functions
        checks[name] = partial(RULES[name], **options)
    return checks
