import os
import shlex

from flint.fortlines import FortLines
from flint.module import Module
from flint.program import Program


class Source(object):
    # R202
    program_units = {
        'program': Program,     # R1101
        'function': None,       # R1229 (R203)
        'subroutine': None,     # R1235 (R203)
        'module': Module,       # R1104
        'submodule': None,      # R1116
        'block': None,          # R1120
    }

    def __init__(self):
        # Filepath
        self.project = None     # Link to parent
        self.path = None
        self.abspath = None     # TODO: Use a property to get root from project

        # Program units
        self.units = []

        # Diagnostics
        self.linewidths = []
        self.whitespace = []
        self.commented = []

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

        # Create tokenizer
        with open(self.path) as srcfile:
            f90lex = shlex.shlex(srcfile, punctuation_chars='*/=<>:')
            f90lex.commenters = ''
            f90lex.whitespace = ''

            # When punctuation_chars is set, certain tokens are added to
            # wordchars.  Here we undo this change and remove them.
            wcmap = f90lex.wordchars.maketrans(dict.fromkeys('~-.?'))
            f90lex.wordchars = f90lex.wordchars.translate(wcmap)

            tokens = list(f90lex)

        # Tokenized lines
        raw_lines = []
        start = end = 0
        while True:
            try:
                end = start + tokens[start:].index('\n')
                raw_lines.append(tokens[start:end])
                start = end + 1
            except ValueError:
                break

        # Line cleanup
        src_lines = []
        for line in raw_lines:

            # Record line widths
            width = len(''.join(line))
            self.linewidths.append(width)

            # Strip comments
            if '!' in line:
                line = line[:line.index('!')]
                self.commented.append(True)
            else:
                self.commented.append(False)

            # Merge unhandled tokens
            # TODO  m(-_-)m
            #   1. Operators
            #   2. Boolean values
            #   3. Floating point values

            # Track whitespace between tokens
            # TODO: Move first whitespace to `self.indent`?
            line_ws = []
            ws_count = 0
            for tok in line:
                if tok == ' ':
                    ws_count += 1
                else:
                    line_ws.append(ws_count)
                    ws_count = 0

            line_ws.append(ws_count)
            self.whitespace.append(line_ws)

            # TODO: Check token case consistenc
            #       For now just convert to lowercase
            line = [tok.lower() for tok in line if tok[0] not in '\'"']

            # Remove whitespace
            tokenized_line = [tok for tok in line if not tok == ' ']
            if tokenized_line:
                src_lines.append(tokenized_line)

        flines = FortLines(src_lines)

        for line in flines:
            if line[0] in Source.program_units:
                # Testing
                print('{}: {}'.format(line[0][0].upper(), ' '.join(line)))

                utype = line[0]
                Unit = Source.program_units[utype]

                # Get unit name if present
                unit = Unit()
                unit.parse(flines)

                # How to select container?
                self.units.append(unit)

            else:
                # Unresolved line
                print('X: {}'.format(' '.join(line)))
