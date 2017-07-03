import os
import sys

from flint.fortlines import FortLines
from flint.report import Report
from flint.unit import Unit
from flint.tokenizer import Tokenizer


class Source(object):
    def __init__(self, project=None, verbose=False):
        self.project = project
        self.verbose = verbose
        self.path = None
        self.abspath = None

        # Program units
        self.units = []

        # Diagnostics
        self.indent = []
        self.report = Report()

        # Preprocessor substitution
        self.defines = {}

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

                if line.lstrip().startswith('#'):
                    self.preprocess(line)

                try:
                    tokens = tokenizer.parse(line)
                except ValueError:
                    print('error', srcfile)
                    print(line)
                    sys.exit()

                # TODO: Don't do this with tokens
                self.report.check_trailing_whitespace(tokens, line_number)

                # TODO: Check whitespace between tokens
                if tokens and all(c in ' \t' for c in tokens[0]):
                    self.indent.append(len(tokens[0]))
                else:
                    self.indent.append(0)

                self.report.check_token_spacing(tokens, line_number)

                for tok in tokens:
                    self.report.cases[tok.lower()].add(tok)

                # Strip comments and preprocessed lines
                # TODO: Handle preprocessed lines better
                tokens = [w for w in tokens if w[0] not in '!#']

                # TODO: Check token case consistency
                #       For now just convert to lowercase
                tokens = [tok.lower() if tok[0] not in '\'"' else tok
                          for tok in tokens]

                # Remove whitespace
                tokenized_line = [tok for tok in tokens
                                  if not all(c in ' \t' for c in tok)]
                if tokenized_line:
                    src_lines.append(tokenized_line)

        self.report.check_keyword_case()

        # NOTE: Would be great to integrate the prior loop into FortLines...
        flines = FortLines(src_lines)

        for line in flines:
            if Unit.statement(line):
                unit = Unit(verbose=self.verbose)
                unit.parse(flines)
                self.units.append(unit)
            else:
                # Unresolved line
                print('X: {}'.format(' '.join(line)))

    def preprocess(self, line):
        words = line.strip().split()
        directive = words[0][1:]
        if directive == 'define':
            # TODO: macro functions
            self.defines[words[1]] = words[2:]

        elif directive == 'undef':
            identifier = words[1]
            try:
                self.defines.pop(identifier)
            except KeyError:
                print('flint: warning: identifier {} was never '
                      'set.'.format(identifier))

        elif directive == 'include':
            assert words[1], words[-1] in (('"', '"'), ('<', '>'))
            inc_fname = words[1][1:-1]

            # First check current directory
            curdir = os.path.dirname(self.path)
            test_fpath = os.path.join(curdir, inc_fname)
            if os.path.isfile(test_fpath):
                inc_fpath = test_fpath
                print('Include path: ' + inc_fpath)
            elif self.project:
                # Search project for file
                print('Include path: TODO')
            else:
                print('flint: Include file {} not found; skipping.'
                      ''.format(inc_fname))

        else:
            #print('flint: unsupported preprocess directive: {}'
            #      ''.format(directive))
            pass
