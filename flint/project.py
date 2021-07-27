"""flint Project class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import os
import sys

from flint.source import Source
from flint.units import Module


class Project(object):

    def __init__(self):
        self.debug = False

        # Source code
        self.path = None
        self.directories = []
        self.files = []
        self.include_dirs = []

        # Program structure
        self.modules = []

    # TODO: *paths is generally a bad idea for a public API.  I am only using
    #   it here to get sensible output in my MOM6 tests.
    # TODO: `exclude` may prove more useful here.
    def parse(self, *paths):
        filepaths = []
        for path in paths:
            assert os.path.isdir(path)
            self.path = path

            for root, dirs, files in os.walk(self.path):
                self.directories.append(root)

                for fname in files:
                    fpath = os.path.join(root, fname)
                    if os.path.splitext(fname)[1] in ('.f90', '.F90'):
                        filepaths.append(fpath)
                    else:
                        if self.debug:
                            print('SKIP file: {}'.format(fpath))

        for fpath in filepaths:
            f90file = Source()
            f90file.include_paths = self.directories + self.include_dirs
            f90file.parse(fpath)

            self.files.append(f90file)

        # Generate list of modules
        for src in self.files:
            for unit in src.units:
                if isinstance(unit, Module):
                    self.modules.append(unit)

        # Now gather the callers for each function
        for mod in self.modules:
            for fn in mod.subprograms:
                # Check for fn() calls in the other modules
                for caller_mod in self.modules:
                    for caller_fn in caller_mod.subprograms:
                        if fn.name in caller_fn.callees:
                            cname = caller_fn.name
                            if (caller_mod != mod):
                                cname = '{}::{}'.format(caller_mod.name, cname)
                            fn.callers.add(cname)
