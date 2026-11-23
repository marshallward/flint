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
from flint.lines import Lines
from flint.units import get_program_unit_type


class Source(object):
    def __init__(self, *, standard=True):
        self.standard = standard
        # Configuration
        self.path = None
        self.include_paths = []
        self.macros = {}

        # Contents
        self.units = []
        self.statements = []
        self.leading_liminals = []

    @property
    def lines(self):
        return Lines(self.statements, leading_liminals=self.leading_liminals)

    def source_text(self):
        """Reconstruct source, including files with no Fortran statements."""
        return ''.join(self.leading_liminals) + ''.join(
            str(token) + ''.join(token.tail)
            for statement in self.statements for token in statement
        )

    def parse(self, path, graph=None):
        self.path = path
        # XXX: This chokes on non-unicode strings (e.g. latin-1).
        #  Using errors='replace' gets past these errors but will break
        #  roundtrip parsing.  This needs some additional thought.
        with open(path, encoding='utf-8', errors='replace', newline='') as fpath:
            lexer = Lexer(fpath, self.include_paths, standard=self.standard)
            # Ordinarily shared with the first token's head. Keep an owner
            # even when comments/directives produce no semantic statements.
            self.leading_liminals = lexer.prior_tail
            for stmt in lexer:
                unit_type = get_program_unit_type(stmt)
                unit = unit_type()

                unit.parse(lexer, graph=graph)
                self.units.append(unit)
                self.statements.extend(unit.statements)

            # Transfer macros from the lexer to the source
            self.macros = lexer.macros
            self.fn_macros = lexer.fn_macros
