"""flint Source class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
# Use Python 3 compatible open()
try:
    from io import open     # Python 2
except ImportError:
    pass                    # Python 3

from flint.lexer import Lexer
from flint.units import get_program_unit_type


class Source(object):
    def __init__(self):
        # Configuration
        self.debug = False
        self.include_paths = []
        self.path = None

        # Contents
        self.units = []
        self.statements = []

    def parse(self, path):
        self.path = path
        # XXX: This chokes on non-unicode strings (e.g. latin-1).
        #  Using errors='replace' gets past these errors but will break
        #  roundtrip parsing.  This needs some additional thought.
        with open(path, errors='replace') as fpath:
            lexer = Lexer(fpath, self.include_paths)
            for stmt in lexer:
                try:
                    unit_type = get_program_unit_type(stmt)
                    unit = unit_type()
                    unit.parse(lexer)
                    self.units.append(unit)
                    self.statements.extend(unit.statements)
                except ValueError:
                    self.statements.append(stmt)
