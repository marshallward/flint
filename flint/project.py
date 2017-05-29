import os
import sys

from flint.source import Source


class Project(object):

    def __init__(self,verbose=False):
        self.files = []
        self.verbose = verbose

    def parse(self, root_path):
        assert os.path.isdir(root_path)

        for fname in os.listdir(root_path):
            fpath = os.path.join(root_path, fname)

            # TODO: Validate file
            # For now use extensions
            if os.path.isfile(fpath):

                if os.path.splitext(fpath)[1] in ('.f90', '.F90'):
                    f90file = Source(verbose=self.verbose)
                    f90file.parse(fpath)

                    self.files.append(f90file)
                else:
                    print('SKIP file: {}'.format(fpath))
                    continue

            elif os.path.isdir(fpath):
                self.parse(fpath)

            else:
                print('SKIP file: {}'.format(fpath))
