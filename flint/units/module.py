"""flint Module class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from flint.units.unit import Unit


class Module(Unit):
    # Placeholder class for now
    def __init__(self):
        super(Module, self).__init__()


def is_module(line):
    """Return True if the line is a valid module statement."""
    if len(line) != 2 and line[0] != 'module':
        return False

    # TODO: line[1] must be a valid name

    return True
