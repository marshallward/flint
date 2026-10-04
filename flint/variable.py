"""flint Variable class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from flint.document import Document


class Variable(object):

    intrinsic_types = [
        'integer',
        'real',
        'double',   # double precision
        'complex',
        'character',
        'logical',
    ]

    def __init__(self, name, vtype):
        self.name = name
        self.type = vtype
        self.intent = None
        self.dimension = None

        self.attributes = []
        self.refs = 0

        self.stmt = None
        self.doc = Document()

    @classmethod
    def from_token(cls, token, vtype, intent=None, dimension=None, stmt=None):
        variable = cls(token, vtype)
        variable.intent = intent
        variable.dimension = dimension
        variable.stmt = stmt
        return variable

    @staticmethod
    def dimension_from_tokens(tokens):
        par_count = 1
        rank = 1
        for tok in tokens:
            if tok == '(':
                par_count += 1
            elif tok == ')':
                par_count -= 1
            elif tok == ',' and par_count == 1:
                rank += 1

            if par_count == 0:
                return rank

        return rank

    @property
    def is_array(self):
        return self.dimension is not None
