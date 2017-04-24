import collections
import string

class Report(object):
    def __init__(self):
        # Default behaviour
        self.linewidth = 79
        self.indent = 4

        self.errors = collections.defaultdict(list)

    def check_linewidth(self, line, line_number):
        code = 'C0101'
        if len(line) > self.linewidth:
            self.errors[code].append(line_number)

    def check_trailing_whitespace(self, tokens, line_number):
        code = 'C0102'
        if all(c in string.whitespace for c in tokens[-1]):
            self.errors[code].append(line_number)
