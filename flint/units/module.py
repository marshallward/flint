"""Some sample functions to test parsing of program unit statements."""

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
