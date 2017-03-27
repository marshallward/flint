import itertools
import os
import shlex

from flint.fortlines import FortLines
from flint.program import Program


class Source(object):
    def __init__(self):
        self.project = None     # Link to parent
        self.path = None
        self.abspath = None     # Use property to get root from project

        self.programs = []
        self.modules = []
        self.subroutines = []
        self.functions = []

        # Temporary debug variable
        self.lines = None

    def parse(self, path):
        # Resolve filepath
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
            f90lex = shlex.shlex(srcfile)
            f90lex.commenters = '!'
            f90lex.whitespace = ' \t'   # TODO check this
            tokens = list(f90lex)

        # Maybe do the lowercase check later...
        lines = [list(gg.lower() if not gg[0] in '\'"' else gg for gg in g)
                 for k, g in itertools.groupby(tokens, lambda x: x == '\n')
                 if not k]

        self.lines = lines

        ilines = FortLines(lines)
        for line in ilines:
            if line[0] == 'program':
                # Testing
                print(' '.join(line))

                if len(line) == 2:
                    # TODO: validate label
                    prog_name = line[1]

                prog = Program(prog_name)
                prog.parse(ilines)

                self.programs.append(prog)
            else:
                # Unresolved line
                print('XXX: {}'.format(' '.join(line)))
