import os
import sys

from flint.source import Source


class Project(object):

    def __init__(self, verbose=False):
        self.files = []
        self.verbose = verbose
        self.path = None

        self.directories = []

    # Recursive hunt for a unit matching utype and name
    def search_units(self, unit, utype, name):
        if unit.name == name and unit.utype == utype:
            return unit
        if unit.blocks:
            for block in unit.blocks:
                match = self.search_units(block, utype, name)
                if match:
                    return match
        if unit.subprograms:
            for subprog in unit.subprograms:
                match = self.search_units(subprog, utype, name)
                if match:
                    return match
        return None

    # This returns the matching Unit or None if not found.
    def find_member(self, utype, name):
        matched_unit = None
        for proj_file in self.files:
            for unit in proj_file.units:
                matched_unit = self.search_units(unit, utype, name)
                if matched_unit:
                    break
        return matched_unit

    # TODO: *paths is generally a bad idea for a public API.  I am only using
    #   it here to get sensible output in my MOM6 tests.
    # TODO: `exclude` may prove more useful here.
    # Keep track of skipped items
    # Because *input_items is an iterable, you can pass a single file or many
    # single files and directories.  Make a pathway for files and directories.
    # TODO: detect file/directory globs?
    def parse(self, *input_items):
        skipped_items = []
        filepaths = []
        for input_item in input_items:
            if os.path.isdir(input_item):
                self.path = input_item

                for root, dirs, files in os.walk(self.path):
                    self.directories.append(root)

                    for fname in files:
                        fpath = os.path.join(root, fname)
                        if os.path.splitext(fname)[1] in ('.f90', '.F90'):
                            filepaths.append(fpath)
                        else:
                            skipped_items.append(fpath)
            elif os.path.isfile(input_item):
                filepaths.append(input_item)

        for fpath in filepaths:
            self.path = fpath
            f90file = Source(project=self, verbose=self.verbose)
            try:
                f90file.parse(path=fpath)
            except IOError:
                # In case of IO error, consider this a skipped file
                skipped_items.append(fpath)
            except:
                # Propogate other errors up to the program
                print("Unexpected error:", sys.exc_info()[0])
                raise
            self.files.append(f90file)

        if len(skipped_items) > 0:
            print("WARNING: Item(s) were skipped")
            if self.verbose:
                for item in skipped_items:
                    print(">",item)
