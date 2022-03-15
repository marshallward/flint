"""flint Project class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import os

from flint.source import Source
from flint.units import Module


class Project(object):
    # TODO: make a control parameter
    extensions = ['.f90', '.F90']

    def __init__(self):
        # Source code
        self.path = None
        self.directories = []
        self.sources = []
        self.include_dirs = []

        # Program structure
        self.main = None
        self.modules = []
        self.externals = []
        # NOTE: Currently just a dict containing procedure names as keys, and
        #   returns the list of procedure names which call it.
        # TODO: Replace this with an actual call graph
        self.graph = {}

    # TODO: *paths is generally a bad idea for a public API.  I am only using
    #   it here to get sensible output in my MOM6 tests.
    def parse(self, *paths, excludes=None):
        # Set up the exclusion list
        if excludes:
            exclude_dirs = [os.path.normpath(p) for p in excludes]
        else:
            exclude_dirs = []

        filepaths = []
        for path in paths:
            # Single files can be handled independently
            if os.path.isfile(path):
                filepaths.append(path)
                continue

            # Herein assume directories containing source files
            assert os.path.isdir(path)
            self.path = path

            for root, dirs, files in os.walk(self.path):
                self.directories.append(root)

                # Skip any excluded directories
                if os.path.normpath(root) in exclude_dirs:
                    continue

                for fname in files:
                    fpath = os.path.join(root, fname)

                    if os.path.splitext(fname)[1] in Project.extensions:
                        filepaths.append(fpath)

        for fpath in filepaths:
            f90file = Source()
            f90file.include_paths = self.directories + self.include_dirs
            f90file.parse(fpath, graph=self.graph)

            self.sources.append(f90file)

        # Generate list of modules
        for src in self.sources:
            for unit in src.units:
                if isinstance(unit, Module):
                    self.modules.append(unit)
                else:
                    self.externals.append(unit)

        # Append the globals as a hidden module
        extmod = Module()
        for unit in self.externals:
            extmod.subprograms.append(unit)
        self.modules.append(extmod)
