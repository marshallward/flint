class FortLines(object):
    """Fortran source line iterator."""

    def __init__(self, lines):
        self.lines = iter(lines)

        self.current_line = None

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
        string_append = False
        while line[-1] == '&':
            next_line = next(self.lines)

            if line[-2][0] in '"\'' or string_append:
                idx = next_line.index('&')

                new_string = line[-2] + next_line[idx + 1]
                line = line[:-2] + [new_string] + next_line[idx + 2:]

                # True if string continues to next line
                string_append = (next_line[idx + 1][-1] not in '"\'')
            else:
                line = line[:-1] + next_line

        self.current_line = line
        return line
