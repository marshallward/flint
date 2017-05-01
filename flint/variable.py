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
        self.attributes = []
        self.refs = 0
