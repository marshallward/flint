from flint.construct import Construct

class Unit(object):
    unit_types = [
        'program',
        'function',
        'subroutine',
        'module',
        'submodule',
        'block',
    ]

    # TODO: Will probably move all this to a Types class...
    intrinsic_types = [
        'integer',      # R405
        'real',         # R404
        'double',       # R404 (DOUBLE PRECISION)
        'complex',      # R404
        'character',    # R404
        'logical',      # R404
    ]

    attribute_specs = [
        'codimension',
        'contiguous',
        'dimension',
        'external',
        'intent',
        'namelist',
        'optional',
        'pointer',
        'protected',
        'save',
        'target',
        'volatile',
        'value',
        'common',       # Deprecated
        'equivalence',  # Deprecated
    ]

    declaration_types = intrinsic_types + attribute_specs + [
        'type',         # R426, R403
        'enum',         # R459 ("ENUM, BIND(C)")
        'generic',      # R1210
        'interface',    # R1201
        'parameter',    # R551
        'procedure',    # R1213: Procedure declaration statement
        'data',         # R537
        'format',       # R1001
        'entry',        # R1242 (obsolete)
    ]

    def __init__(self):
        self.name = None
        self.utype = None

    def end_statement(self, line):
        assert self.utype

        # TODO: Very similar to construct... can I merge somehow?
        if line[0].startswith('end'):
            if len(line) == 1 and line[0] in ('end', 'end' + self.utype):
                return True
            elif len(line) >= 2 and (line[0], line[1]) == ('end', self.utype):
                return True
            else:
                return False

    def parse(self, lines):
        """Parse the lines of a program unit.

        Program units are generally very similar, but we leave it undefined
        here due to some slight differences.
        """
        self.parse_name(lines.current_line)
        self.parse_specification(lines)
        self.parse_execution(lines)
        self.parse_subprogram(lines)

    def parse_name(self, line):
        """Parse the name of the program unit, if present.

        Each program unit has a different header format, so this method must be
        overridden by each subclass.
        """
        self.utype = line[0]

        if len(line) >= 2:
            self.name = line[1]
        else:
            self.name = None

        print('{}: {} '.format(self.utype[0].upper(), ' '.join(line)))

    # Specification

    def parse_specification(self, lines):
        """Parse the specification part (R204) of a program unit (R202).

        Specification parts contain the following:

        1. USE statements (R1109)
        2. IMPORT statements (R1211)
        3. IMPLICIT statements (R205)
        4. Declaration constructs (R207)
        """
        # TODO: `use`, `implicit`, and declarations must appear in that order.
        #       This loop does not check order.
        for line in lines:
            if line[0] == 'use':
                self.parse_use_stmt(line)
            elif line[0] == 'import':
                self.parse_import_stmt(line)
            elif line[0] == 'implicit':
                self.parse_implicit_stmt(line)
            elif line[0] in Unit.declaration_types:
                self.parse_declaration_construct(line)
            else:
                break

    def parse_use_stmt(self, line):
        print('U: {}'.format(' '.join(line)))

    def parse_import_stmt(self, line):
        print('i: {}'.format(' '.join(line)))

    def parse_implicit_stmt(self, line):
        print('I: {}'.format(' '.join(line)))

    def parse_declaration_construct(self, line):
        print('D: {}'.format(' '.join(line)))

    # Execution

    def parse_execution(self, lines):
        # First parse the line which terminated specification
        # TODO: How to merge with iteration below?

        line = lines.current_line

        # TODO: need to include label support here
        if Construct.statement(line):
            cons = Construct()
            cons.parse(lines)
        elif self.end_statement(line) or line[0] == 'contains':
            return
        else:
            # Unhandled
            print('E: {}'.format(' '.join(line)))

        # Now iterate over the rest of the lines
        for line in lines:
            # Execution constructs
            if Construct.statement(line):
                cons = Construct()
                cons.parse(lines)
            elif self.end_statement(line) or line[0] == 'contains':
                # TODO: Use return?
                break
            else:
                # Unhandled
                print('E: {}'.format(' '.join(line)))

    def parse_subprogram(self, lines):
        line = lines.current_line

        if line[0] in Unit.unit_types:
            subprog = Unit()
            subprog.parse(lines)
        elif self.end_statement(line):
            return
        else:
            print('{}: {}'.format(self.utype[0].upper(), ' '.join(line)))

        for line in lines:
            if line[0] in Unit.unit_types:
                subprog = Unit()
                subprog.parse(lines)
            elif self.end_statement(line):
                # TODO: Use return?
                break
            else:
                # Unresolved line
                print('X: {}'.format(' '.join(line)))
