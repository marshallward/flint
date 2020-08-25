import os
import sys

# Use Python 3 compatible open()
try:
    from io import open     # Python 2
except ImportError:
    pass                    # Python 3

from flint.fortlines import FortLines
from flint.report import Report
from flint.units.unit import Unit
from flint.tokenizer import Tokenizer
from flint.document import is_docstring

from flint.units import get_program_unit_type


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
        self.inc_reports = {}

        # Preprocessor substitution
        self.defines = {}
        self.stop_parsing = False

    def parse(self, path):
        # NOTE: Tracking both path and abspath is probably pointless...

        # Resolve filepaths
        if os.path.isabs(path):
            self.abspath = path
            self.path = path

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

        (src_lines, flines) = self.tokenize()

        # NOTE: Would be great to integrate this with self.tokenize()
        # Kinda moved into tokenize
        #flines = FortLines(src_lines)

        for line in flines:
            try:
                unit_type = get_program_unit_type(line)
                unit = unit_type()
                unit.verbose = self.verbose
                unit.parse(flines)
                self.units.append(unit)
            except ValueError:
                # Unresolved line
                print('X: {}'.format(' '.join(line)))

            #if Unit.statement(line):
            #    unit = Unit(verbose=self.verbose)
            #    unit.parse(flines)
            #    self.units.append(unit)
            #else:
            #    # Unresolved line
            #    print('X: {}'.format(' '.join(line)))

    def tokenize(self, path=None, report=None):
        if not path:
            path = self.path
        if not report:
            report = self.report

        tokenizer = Tokenizer()
        line_number = 0
        src_lines = []
        if self.verbose:
            print('{} ({})'.format(self.path, self.abspath))

        # TODO: Settle on name, move to __init__
        self.stop_parsing = False

        # TODO: pycodestyle has a better way to deal with nonunicode files
        with open(path, errors='replace') as srcfile:
            for line in srcfile:
                line_number += 1

                report.check_linewidth(line, line_number)

                if line.lstrip().startswith('#'):
                    self.preprocess(line[1:])

                if self.stop_parsing:
                    continue

                try:
                    tokens = tokenizer.parse(line)
                except ValueError:
                    print('error', srcfile)
                    print(line)
                    sys.exit()

                # Substitute any preprocessor tokens
                for i, tok in enumerate(tokens):
                    if tok in self.defines:
                        val = self.defines[tok]

                        # Substitute unknown values with empty strings
                        # TODO: Better way to do this?
                        if val is None:
                            val = ''

                        replacement = val + '\n'
                        tokens[i:i+1] = tokenizer.parse(replacement)
                        if (self.verbose):
                            print('replacing {} with {}'
                                  ''.format(repr(tok), repr(val)))

                # TODO: Shouldn't this be done with `lines`?
                report.check_trailing_whitespace(tokens, line_number)

                # TODO: Check whitespace between tokens
                if tokens and all(c in ' \t' for c in tokens[0]):
                    self.indent.append(len(tokens[0]))
                else:
                    self.indent.append(0)

                report.check_token_spacing(tokens, line_number)

                # Track the case consistency of tokens
                # NOTE: This is at the source level, but should possibly be
                #       handled at the block level (module, function, etc)
                for tok in tokens:
                    # Exclude comments and strings
                    if tok[0] not in ('!', '"', '\''):
                        report.cases[tok.lower()].add(tok)

                # Strip comments and preprocessed lines, but keep docstrings
                # TODO: Handle preprocessed lines better
                tokens = [tok for tok in tokens
                          if tok[0] not in '!#' or is_docstring(tok)]

                # XXX: Is this changing the case of comment tokens?
                tokens = [
                    tok.lower()
                    if tok[0] not in '\'"' and not is_docstring(tok)
                    else tok
                    for tok in tokens
                ]

                # Remove whitespace
                tokenized_line = [tok for tok in tokens
                                  if not all(c in ' \t' for c in tok)]
                if tokenized_line:
                    src_lines.append(tokenized_line)

        report.check_keyword_case()

        return (src_lines, FortLines(src_lines))

    def preprocess(self, line):
        words = line.strip().split(None, 2)
        directive = words[0]

        if directive == 'define':
            # TODO: macro functions
            replacement = words[2] if len(words) == 3 else None
            self.defines[words[1]] = replacement
            if (self.verbose):
                print('#define: {} as {}'
                      ''.format(repr(words[1]), repr(replacement)))

        elif directive == 'undef':
            identifier = words[1]
            try:
                self.defines.pop(identifier)
            except KeyError:
                if self.verbose:
                    print('flint: warning: unset identifier {} was never '
                          'defined.'.format(identifier))

        # TODO
        #elif directive == 'if':
        #    expr = line.strip().split(None, 1)[1]

        elif directive == 'ifdef':
            macro = line.split(None, 1)[1]
            if macro not in self.defines:
                self.stop_parsing = True

        elif directive == 'ifndef':
            macro = line.split(None, 1)[1]
            if macro in self.defines:
                self.stop_parsing = True

        elif directive == 'else':
            self.stop_parsing = not self.stop_parsing

        elif directive == 'endif':
            self.stop_parsing = False

        elif directive.startswith('include'):
            # This directive uniquely does not require a whitespace delimiter.
            if directive != 'include':
                inc_fpath = directive.replace('include', '', 1)
                words[0] = 'include'
                words.insert(1, inc_fpath)

            assert (words[1][0], words[1][-1]) in (('"', '"'), ('<', '>'))
            inc_fname = words[1][1:-1]

            # First check current directory
            curdir = os.path.dirname(self.path)
            test_fpath = os.path.join(curdir, inc_fname)

            inc_path = None
            if os.path.isfile(test_fpath):
                inc_path = test_fpath
            elif self.project:
                # Scan the project directories for the file
                for idir in self.project.directories:
                    test_fpath = os.path.join(idir, inc_fname)
                    if os.path.isfile(test_fpath):
                        inc_path = test_fpath
            # else: do not bother looking

            if inc_path:
                # TODO: Using the Source tokenize seems dumb here but I
                #  don't have a better solution at the moment.
                inc_report = Report()
                self.tokenize(path=inc_path, report=inc_report)
                self.inc_reports[inc_path] = inc_report
            else:
                if self.verbose:
                    print('flint: Include file {} not found; skipping.'
                          ''.format(inc_fname))
        else:
            if self.verbose:
                print('flint: unsupported preprocess directive: {}'
                      ''.format(line))
