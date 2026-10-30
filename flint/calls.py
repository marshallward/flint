"""Callable symbol tracker.

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""


def get_callable_symbols(line, variables, *, variable_names=None):
    """Find callables, optionally reusing normalized variable names for a scope."""
    candidates = [
        b for a, b, c in zip(line, line[1:], line[2:])
        # TODO: Resolve derived-type components so type-bound procedures can be
        # distinguished from array/data components like obj%field(i,j).
        if c == '(' and a != '%' and b[0].isalpha()
    ]
    if not candidates:
        return []
    if variable_names is None:
        variable_names = {var.name.lower() for var in variables}
    return [name for name in candidates if name not in variable_names]
