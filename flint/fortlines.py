class FortLines(object):
    """Fortran source line iterator"""

    def __init__(self, lines):
        # TODO: Check if already an iterator?
        self.lines = iter(lines)

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        return next(self.lines)
