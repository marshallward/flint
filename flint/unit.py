class Unit(object):
    intrinsic_types = [
            'integer',      # R405
            'real',         # R404
            'double',       # R404 (DOUBLE PRECISION)
            'complex',      # R404
            'character',    # R404
            'logical',      # R404
    ]

    declaration_types = intrinsic_types + [
            'type',         # R426, R403
            'enum',         # R459 ("ENUM, BIND(C)")
            'generic',      # R1210
            'interface',    # R1201
            'parameter',    # R551
            'procedure',    # R1213: Procedure declaration statement
            # Skipping R213... (mostly for pre-declared variables)
            'data',         # R537
            'format',       # R1001
            'entry',        # R1242 (obsolete)
    ]

    def __init__(self, name):
        self.name = name

        # Implicit state
        self.implicit = {}

        self.modules = []
        self.functions = []
        self.variables = []

    @staticmethod
    def parse_name(line):
        """Parse the name of the program unit, if present.

        Each program unit has a different header format, so this method must be
        overridden by each subclass.
        """
        raise NotImplementedError

    def parse(self, lines):
        """Parse the lines of a program unit.

        Each program unit consists of three sections:

        1. Specification part (R204)
        2. Execution part (R209)
        3. Subprograms:
           a. Internal subprogram part (R211)
           b. Module subprogram part (R1107)

        None of this has yet been implemented.  Below is just some basic
        handling of DO and IF constructs.
        """
        # TODO: Might as well do this here, rather than a static function
        #self.parse_name(lines.prior_line)

        self.parse_specification(lines)
        self.parse_execution(lines)

    # Specification

    def parse_specification(self, lines):
        """Parse the specification part (R204) of a program unit (R202).

        Specification parts contain the following:

        1. USE statements (R1109)
        2. IMPORT statements (R1211)
        3. IMPLICIT statements (R205)
        4. "declaration constructs"

        """
        for line in lines:
            # TODO: Reorganise as a dict
            if line[0] == 'use':
                self.parse_use_stmt(line)
            elif line[0] == 'import':
                self.parse_import_stmt(line)
            elif line[0] == 'implicit':
                self.parse_implicit_stmt(line)
            elif line[0] in Unit.declaration_types:
                # TODO: function statements (R1245)? (probably never...)
                self.parse_declaration_construct(line)
            else:
                # Any other keyword indicates the end of specification.
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
        if line[0] == 'do' or (line[0], line[-1]) == ('if', 'then'):
            print('C: {} '.format(' '.join(line)))
            self.parse_construct(line[0], lines)

        # Termination
        elif line[0].startswith('end'):
            if (line[0] == 'end' and line[1] == 'program' or
                    line[0] == 'endprogram'):
                print('P: {} '.format(' '.join(line)))
            else:
                # Should never happen?
                print('XXX: {}'.format(line))
        else:
            # Unhandled
            print('E: {}'.format(line))

        # Now iterate over the rest of the lines
        for line in lines:
            # Execution constructs
            if line[0] == 'do' or (line[0], line[-1]) == ('if', 'then'):
                print('C: {} '.format(' '.join(line)))
                self.parse_construct(line[0], lines)

            # Termination
            elif line[0].startswith('end'):
                if (line[0] == 'end' and line[1] == 'program' or
                        line[0] == 'endprogram'):
                    print('P: {} '.format(' '.join(line)))
                    break
                else:
                    # Should never happen?
                    print('XXX: {}'.format(line))
            else:
                # Unhandled
                print('X: {}'.format(line))

    def parse_construct(self, ctype, lines):
        for line in lines:
            # Execution constructs
            if line[0] == 'do' or (line[0], line[-1]) == ('if', 'then'):
                print('c: {} '.format(' '.join(line)))
                self.parse_construct(line[0], lines)

            elif line[0].startswith('end'):
                if (line[0] == 'end' and line[1] == ctype or
                        line[0] == 'end' + ctype):
                    print('C: {} '.format(' '.join(line)))
                    break
                else:
                    # Should never happen?
                    print('X: {}'.format(line))
            else:
                # Unhandled
                print('C: {}'.format(line))
