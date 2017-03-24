import itertools
import os
import shlex

class F90Source(object):
    def __init__(self):
        self.project = None     # Link to parent
        self.path = None
        self.abspath = None     # Use property to get root from project

        self.modules = []
        self.subroutines = []
        self.functions = []

    def parse(self, path):

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

        lines = [list(g) for k,g in itertools.groupby(tokens, lambda x:x == '\n')
                 if not k]

        print(lines)
