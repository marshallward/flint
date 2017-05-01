import collections
import string


class Report(object):
    def __init__(self):
        # Default behaviour
        self.linewidth = 79
        self.indent = 4

        # NOTE: Current codes used here are totally rubbish!
        self.errors = collections.defaultdict(list)
        self.cases = collections.defaultdict(set)

    def check_linewidth(self, line, line_number):
        code = 'C0101'
        if len(line) > self.linewidth:
            self.errors[code].append(line_number)

    def check_trailing_whitespace(self, tokens, line_number):
        code = 'C0102'
        if tokens and all(c in string.whitespace for c in tokens[-1]):
            self.errors[code].append(line_number)

    def check_token_spacing(self, tokens, line_number):
        code = 'C0103'
        # TODO: Obviously room for improvement here...
        for idx, tok in enumerate(tokens[1:], start=1):
            if all(c in ' \t' for c in tok) and len(tok) > 1:
                if idx == len(tokens) - 2 and tokens[-1].startswith('!'):
                    continue
                err = line_number, ''.join(tokens[idx-1:idx+2])
                self.errors[code].append(err)

    def check_mixed_tabs_spaces(self, tokens, line_number):
        raise NotImplementedError

    def check_keyword_case(self):
        code = 'C0104'
        for kw in self.cases:
            kw_set = self.cases[kw]
            if len(kw_set) > 1:
                self.errors[code].append(kw_set)

    def error_endcomma(self, line_number=None):
        code = 'E0101'

        # TODO: Get line number somehow
        if line_number is None:
            line_number = -1

        self.errors[code].append(line_number)
