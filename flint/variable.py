class Variable(object):

    intrinsic_types = [
        'integer',      # R405
        'real',         # R404
        'double',       # R404 (DOUBLE PRECISION)
        'complex',      # R404
        'character',    # R404
        'logical',      # R404
        # XXX
        'realtype',     # Garbage type to accommodate GOTM until #define is
                        # handled properly
    ]

    def __init__(self, name, vtype):
        self.name = name
        self.type = vtype
        self.attributes = []
        self.refs = 0
