"""Callable symbol tracker.

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""


def get_callable_symbols(line, variables):
    variable_names = {str(var.name).lower() for var in variables}
    names = [
        b for a, b, c in zip(line, line[1:], line[2:])
        # TODO: Resolve derived-type components so type-bound procedures can be
        # distinguished from array/data components like obj%field(i,j).
        if a != '%' and c == '(' and b[0].isalpha()
        and str(b).lower() not in variable_names
    ]

    return names
