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

        for fname in os.listdir(self.path):
            fpath = os.path.join(self.path, fname)

            # TODO: Validate file
            # For now use extensions
            if os.path.isfile(fpath):

                if os.path.splitext(fpath)[1] in ('.f90', '.F90'):
                    f90file = Source(project=self, verbose=self.verbose)
                    f90file.parse(fpath)

                    self.files.append(f90file)
                else:
                    print('SKIP file: {}'.format(fpath))
                    continue

            elif os.path.isdir(fpath):
                self.parse(fpath)

            else:
                print('SKIP file: {}'.format(fpath))
