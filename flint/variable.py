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

        self.attributes = []
        self.refs = 0

        self.doc = Document()
