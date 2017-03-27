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
        line = next(self.lines)

        # Join extended lines
        while (line[-1] == '&'):
            line = line[:-1] + next(self.lines)

        # TODO: Combine tokens incorrectly split by shlex
        # (Or, you know, use a better tokenizer)

        return line
