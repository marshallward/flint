"""Some sample functions to test parsing of program unit statements."""

from flint.units.unit import Unit


class Submodule(Unit):
    # Placeholder class for now
    def __init__(self):
        super(Submodule, self).__init__()


def is_submodule(line):
    """Return True if the line is a valid submodule statement."""
    if (line[0], line[1]) != ('submodule', '('):
        return False

    # Not a great test, but enough to get things going.
    if len(line) == 5 and line[3] != ')':
        return False

    if len(line) == 7 and (line[4], line[6]) != (':', ')'):
        return False

    return True
