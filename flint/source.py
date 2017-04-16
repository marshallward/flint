import os
import sys

from flint.fortlines import FortLines
from flint.unit import Unit
from flint.tokenize import tokenize


class Source(object):
    def __init__(self):
        self.project = None     # Link to parent

        # Filepath
        self.path = None
        self.abspath = None     # TODO: Use a property to get root from project

        # Program units
        self.units = []

        # Diagnostics
        self.linewidths = []
        self.whitespace = []

    def parse(self, path):
        # Resolve filepaths
        if os.path.isabs(path):
            self.abspath = path

            if self.project:
                root_path = self.project.path
                plen = len(root_path)
                assert path[:plen] == self.project.path
                self.abspath = path[plen:]
            else:
                self.path = self.abspath

        else:
            self.path = path
            if self.project:
                # TODO: Probably need a root path consistency check here...
                self.abspath = os.path.join(self.project.path, path)
            else:
                self.abspath = os.path.abspath(path)

        raw_lines = []
        delim = None
        print(self.path)
        with open(self.path) as srcfile:
            for line in srcfile:
                try:
                    tokens, delim = tokenize(line, delim)
                except ValueError:
                    print('error', srcfile)
                    print(line)
                    sys.exit()
                raw_lines.append(tokens)

        # Line cleanup
        src_lines = []
        for line in raw_lines:

            # Record line widths
            width = len(''.join(line))
            self.linewidths.append(width)

            # Strip comments and preprocessed lines
            # TODO: Handle preprocessed lines better
            line = [w for w in line if w[0] not in '!#']

            # Merge unhandled tokens
            # (Soon to be deprecated function)
            line = retokenize_line(line)

            # XXX: This thing needs to be fixed anyway...
            ## Track whitespace between tokens
            ## TODO: Move first whitespace to `self.indent`?
            #line_ws = []
            #ws_count = 0
            ##print(line)
            #for tok in line:
            #    if tok == ' ':
            #        ws_count += 1
            #    else:
            #        line_ws.append(ws_count)
            #        ws_count = 0

            #line_ws.append(ws_count)
            #self.whitespace.append(line_ws)

            # TODO: Check token case consistency
            #       For now just convert to lowercase
            line = [tok.lower() if tok[0] not in '\'"' else tok
                    for tok in line]

            # Remove whitespace
            #tokenized_line = [tok for tok in line if not tok == ' ']
            tokenized_line = [tok for tok in line
                              if not all(c == ' ' for c in tok)]
            if tokenized_line:
                src_lines.append(tokenized_line)

        flines = FortLines(src_lines)

        for line in flines:
            #if line[0] in Unit.unit_types:
            if Unit.statement(line):
                unit = Unit()
                unit.parse(flines)
                self.units.append(unit)
            else:
                # Unresolved line
                print('X: {}'.format(' '.join(line)))


def retokenize_line(line):
    """Retokenize line to include literal numbers and operators.

    The shlex tokenizer resolves most Fortran tokens, but fails to gather
    tokens associated with numbers and dot-operators.

    For example, the number -2.4e3 is tokenized into the following:
    >>> ['1', '2', '.', '4', 'e', '3']

    Similarly, the .and. operator is tokenzed into the following:
    >>> ['.', 'and', '.']

    This functions re-groups those tokens into a single token.

    This is a first attempt to resolve such tokens, although it is still a
    work in progress.
    """
    # XXX: Move all this to the `tokenize` function!
    newline = []
    tokens = iter(line)
    for tok in tokens:
        # Floating point re-tokenizer
        if tok.isdigit():
            # TODO leading sign (hard!)
            # TODO E-notation
            # TODO kind (e.g. 1_8)
            value = tok
            try:
                tok = next(tokens)
                if tok == '.':
                    value += tok
                    tok = next(tokens)
                    if tok.isdigit():
                        value += tok
                        tok = next(tokens)
            except StopIteration:
                tok = None

            newline.append(value)
            if tok is not None:
                newline.append(tok)
        else:
            newline.append(tok)

    return newline
