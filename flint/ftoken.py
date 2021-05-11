"""f90lex Token and PToken classes.

``Token`` is a representation of the Fortran token, designed as a subclass of
the Python string.  The usual (string) value corresponds to the original
lexeme, but it also contains a ``head`` and ``tail`` which contain the adjacent
"liminal" tokens.

Equality and hash tests use the case-insensitive forms, like good little
Fortran tokens.

(By "liminal" I mean the whitespace tokens between the semantic tokens.)

The PToken is a subclass of Token, which is produced from preprocessing and
stores its original pre-processed value as ``pp``, which it uses for roundtrip
parsing output.

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
class Token(str):
    # NOTE: Immutable types generally need __new__ implementations
    #   (At least that is my understanding...)
    def __new__(cls, value='', *args, **kwargs):
        tok = str.__new__(cls, value, *args)
        tok.head = []
        tok.tail = []
        tok.split = None
        return tok

    def __eq__(self, other):
        return self.lower() == other.lower()

    def __hash__(self):
        return hash(str(self).lower())


class PToken(Token):
    """Preprocessed Token which prints its origin macro."""
    def __init__(self, value='', pp=''):
        self.pp = pp

    def __str__(self):
        return self.pp
