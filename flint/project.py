import os
import sys

from flint.f90src import F90Source

class Project(object):

    def __init__(self):
        self.files = []

    def parse(self, root_path):
        assert os.path.isdir(root_path)

        for fname in os.listdir(root_path):
            fpath = os.path.join(root_path, fname)

            if os.path.isfile(fpath):
                f90file = F90Source(fpath)
                self.files.append(f90file)

            elif os.path.isdir(fpath):
                self.parse(fpath)

            else:
                print('oops, unsupported file.')
                sys.exit(-1)
