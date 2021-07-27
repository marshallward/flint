"""flint Variable class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from flint.document import Document


class Variable(object):

    intrinsic_types = [
        'integer',      # R405
        'real',         # R404
        'double',       # R404 (DOUBLE PRECISION)
        'complex',      # R404
        'character',    # R404
        'logical',      # R404
    ]

    def __init__(self, name, vtype):
        self.name = name
        self.type = vtype
        self.intent = None

        self.attributes = []
        self.refs = 0

        self.doc = Document()
