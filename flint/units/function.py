"""flint Function class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from flint.units.unit import Unit
from flint.units.subroutine import is_prefix
from flint.units.subroutine import is_args
# TODO: This is dumb
#   Also rename it in subroutine..
from flint.units.subroutine import subprog_attrs


intrinsic_types = [
    'real',
    # TODO: 'double precision',
    'complex',
    'character',
    'logical',
]


decl_types = intrinsic_types + [
    'type',
    'class',
]


class Function(Unit):
    # Placeholder class for now
    def __init__(self):
        super(Function, self).__init__()


def is_function(line):
    """Return True if the line is a valid function statement."""
    try:
        f_idx = line.index('function')
        s_idx = line.index(')') + 1
    except ValueError:
        return False

    prefix, args, suffix = line[:f_idx], line[f_idx+1:s_idx], line[s_idx:]

    # Split attribute prefixes from return type
    # NOTE: This could fail if a type has the same name as an attribute.
    return_type, attrs = [], []
    for tok in prefix:
        (attrs if tok in subprog_attrs else return_type).append(tok)

    if return_type and not is_declaration_type(return_type):
        return False

    if not is_prefix(attrs):
        return False

    if not is_args(args):
        return False

    # TODO: Validate suffix

    return True


def is_declaration_type(decl):
    # TODO: only one type can exist
    # TODO: Ignoring KIND and type names for now, will come back to this
    if decl[0] not in decl_types:
        return False

    return True
