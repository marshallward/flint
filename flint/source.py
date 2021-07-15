import os
import sys

# Use Python 3 compatible open()
try:
    from io import open     # Python 2
except ImportError:
    pass                    # Python 3

from flint.lexer import Lexer
from flint.units import get_program_unit_type
from flint.fortlines import gen_stmt


class Source(object):
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.debug = False
        self.include_paths = []

        # Program units
        self.units = []

    def parse(self, path):
        # XXX: This chokes on non-unicode strings (e.g. latin-1).
        #  Using errors='replace' gets past these errors but will break
        #  roundtrip parsing.  This needs some additional thought.
        with open(path, errors='replace') as fpath:
            lexer = Lexer(fpath, self.include_paths)
            for line in lexer:
                try:
                    unit_type = get_program_unit_type(line)
                    unit = unit_type()
                    unit.verbose = self.verbose
                    unit.parse(lexer)
                    self.units.append(unit)
                except ValueError:
                    # Unresolved line
                    print('X│ {}'.format(gen_stmt(line)))
