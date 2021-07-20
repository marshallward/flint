from flint.document import Document
from flint.statement import Statement

# This is a "declaration block", a made-up term to encapsulate multiline
# declarations:
#  - interface
#  - type (derived types)
#  - enum (via C interface)
# Perhaps it makes more sense to wrap this up in a variable type.
#
# Also, I expect some commonality between this and Unit()

class Declaration(object):
    def __init__(self):
        self.name = None
        self.dtype = None

        # Contents could be stored here...

        # Code data
        self.statements = []
        self.doc = Document()

    def parse(self, lines):
        self.parse_header(lines.current_line)

        # TODO: Replace this with proper handling of the statements
        # XXX: If an interface contains a subroutine, and it terminates with
        #   `end`, rather than `end subroutine`, then this will abort early and
        #   usually cause some unexpected error.
        for line in lines:
            if self.end_statement(line):
                break
            else:
                stmt = Statement(line, tag=self.dtype[0].upper())
                self.statements.append(stmt)

        # Finalisation
        stmt = Statement(lines.current_line, tag=self.dtype[0].upper())
        self.statements.append(stmt)

    def parse_header(self, line):
        # XXX: Naive assumption... maybe true?
        self.dtype = line[0]
        self.name = line[-1]

        stmt = Statement(line, tag=self.dtype[0].upper())
        self.statements.append(stmt)

    def end_statement(self, line):
        assert self.dtype

        # NOTE: This explicitly checks that the type is part of the statement.
        #   Unlike with program units, `end` is not sufficient.
        if line[0].startswith('end'):
            if len(line) == 1 and line[0] == 'end' + self.dtype:
                return True
            elif len(line) >= 2 and (line[0], line[1]) == ('end', self.dtype):
                return True
            else:
                return False


