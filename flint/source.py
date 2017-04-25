import os
import sys

from flint.fortlines import FortLines
from flint.report import Report
from flint.unit import Unit
from flint.tokenizer import Tokenizer


class Source(object):
    def __init__(self, project=None):
        self.project = project

        # Filepath
        self.path = None
        self.abspath = None

        # Program units
        self.units = []

        # Diagnostics
        self.indent = []

        self.report = Report()

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

        tokenizer = Tokenizer()
        line_number = 0
        src_lines = []
        print('{} ({})'.format(self.path, self.abspath))

        # TODO: pycodestyle has a better way to deal with nonunicode files
        with open(self.path, errors='replace') as srcfile:
            for line in srcfile:
                line_number += 1

                self.report.check_linewidth(line, line_number)

                try:
                    tokens = tokenizer.parse(line)
                except ValueError:
                    print('error', srcfile)
                    print(line)
                    sys.exit()

                self.report.check_trailing_whitespace(tokens, line_number)

                # TODO: Check whitespace between tokens
                if tokens and all(c in ' \t' for c in tokens[0]):
                    self.indent.append(len(tokens[0]))
                else:
                    self.indent.append(0)

                self.report.check_token_spacing(tokens, line_number)

                # Strip comments and preprocessed lines
                # TODO: Handle preprocessed lines better
                tokens = [w for w in tokens if w[0] not in '!#']

                # TODO: Check token case consistency
                #       For now just convert to lowercase
                tokens = [tok.lower() if tok[0] not in '\'"' else tok
                        for tok in tokens]

                # Remove whitespace
                tokenized_line = [tok for tok in tokens
                                  if not all(c == ' ' for c in tok)]
                if tokenized_line:
                    src_lines.append(tokenized_line)

        # NOTE: Would be great to integrate the prior loop into FortLines...
        flines = FortLines(src_lines)

        for line in flines:
            if Unit.statement(line):
                unit = Unit()
                unit.parse(flines)
                self.units.append(unit)
            else:
                # Unresolved line
                print('X: {}'.format(' '.join(line)))
