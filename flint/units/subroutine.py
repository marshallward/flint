"""flint Subroutine class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from flint.units.unit import Unit

subprog_attrs = [
    'elemental',
    'impure',
    'module',
    'non_recursive',
    'pure',
    'recursive',
]


class Subroutine(Unit):
    def __init__(self):
        super(Subroutine, self).__init__()


def is_subroutine(line):
    """Return True if the line is a valid subroutine statement."""
    try:
        idx = line.index('subroutine')
    except ValueError:
        return False

    prefix, args = line[:idx], line[(idx+1):]

    if not is_prefix(prefix):
        return False

    if not is_args(args):
        return False

    return True


def is_prefix(prefix):
    """Return True if `prefix` is a valid subroutine prefix."""
    for spec in prefix:
        if spec not in subprog_attrs:
            return False
        if prefix.count(spec) > 1:
            return False

    if 'recursive' in prefix and 'non_recursive' in prefix:
        return False

    if 'pure' in prefix and 'impure' in prefix:
        return False

    return True


def is_args(args):
    # Subroutine arguments are optional
    if not args:
        return True

    # If present, they must be delimited by parentheses
    try:
        i_l = args.index('(')
        i_r = args.index(')')
    except ValueError:
        return False

    # Confirm comma separators
    if any(t != ',' for t in args[(i_l + 2):i_r:2]):
        return False

    # TODO: Confirm valid argument names
    #dummy_arg_list = args[(i_l + 1):i_r:2]

    bind = args[(i_r+1):]
    if bind:
        if tuple(bind[0:3]) != ('bind', '(', 'c') or bind[-1] != ')':
            return False

        name_spec = bind[3:-1]
        if name_spec and name_spec[0:3] != (',', 'name', '='):
            return False

        # TODO: validate the name

    return True
