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

        # Source attributes
        self.programs = []
        self.modules = []
        self.subroutines = []
        self.functions = []

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
            f90lex.whitespace = ' \t'   # TODO check this
            tokens = list(f90lex)

        # Maybe do the lowercase check later...
        raw_lines = [list(gg.lower() if not gg[0] in '\'"' else gg for gg in g)
                     for k, g in itertools.groupby(tokens, lambda x: x == '\n')
                     if not k]

        # Strip comments
        decomment_lines = [l[:l.index('!')] if '!' in l else l
                           for l in raw_lines]

        # Remove empty lines
        src_lines = [l for l in decomment_lines if l]

        for line in src_lines:
            print(line)

        ilines = FortLines(src_lines)
        for line in ilines:
            if line[0] == 'program':
                # Testing
                print(' '.join(line))

                # TODO: Validate prog_name (need to deal with whitespace)
                prog_name = None

                prog = Program(prog_name)
                prog.parse(ilines)

                self.programs.append(prog)
            else:
                # Unresolved line
                print('XXX: {}'.format(' '.join(line)))
