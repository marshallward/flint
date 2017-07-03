import os
import sys

from flint.source import Source


class Project(object):

    def __init__(self, verbose=False):
        self.files = []
        self.verbose = verbose
        self.path = None

    def parse(self, path):
        assert os.path.isdir(path)
        self.path = path

        filepaths = []

        for root, dirs, files in os.walk(self.path):
            for fname in files:
                if os.path.splitext(fname)[1] in ('.f90', '.F90'):
                    fpath = os.path.join(root, fname)
                    filepaths.append(fpath)
                else:
                    print('SKIP file: {}'.format(fpath))

        for fpath in filepaths:
            f90file = Source(project=self, verbose=self.verbose)
            f90file.parse(fpath)
            self.files.append(f90file)
