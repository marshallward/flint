"""Callable symbol tracker.

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""


def get_callable_symbols(line, variables):
    names = [
        b for a, b, c in zip(line, line[1:], line[2:])
        if a != '%' and c == '(' and b[0].isalpha()
        and b not in variables
    ]

    return names
