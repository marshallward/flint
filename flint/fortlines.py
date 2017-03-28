class FortLines(object):
    """Fortran source line iterator"""

    def __init__(self, lines):
        self.lines = iter(lines)

        # Split lines
        self.buffered_line = None

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        if self.buffered_line:
            line = self.buffered_line
            self.buffered_line = None
        else:
            line = next(self.lines)

        if ';' in line:
            idx = line.index(';')
            line, self.buffered_line = line[:idx], line[1 + idx:]

            # How literally do we handle end-line semicolons?
            # This tosses them aside
            if self.buffered_line == []:
                self.buffered_line = None

        # Join extended lines
        # TODO: 255-limit line check
        while (line[-1] == '&'):
            line = line[:-1] + next(self.lines)

        return line
