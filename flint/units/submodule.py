"""flint Submodule class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from flint.units.unit import Unit


class Submodule(Unit):
    # Placeholder class for now
    def __init__(self):
        super(Submodule, self).__init__()


def is_submodule(line):
    """Return True if the line is a valid submodule statement."""
    if len(line) < 2:
        # XXX: This is just to prevent index error in the next test
        #   Not entirely sure what this ought to be, come back to it...
        return False

    if (line[0], line[1]) != ('submodule', '('):
        return False

    # Not a great test, but enough to get things going.
    if len(line) == 5 and line[3] != ')':
        return False

    if len(line) == 7 and (line[4], line[6]) != (':', ')'):
        return False

    return True
