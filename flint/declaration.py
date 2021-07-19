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

    def parse(self, lines):
        self.parse_header(lines.current_line)

        # A minimal parsing of the declaration contents.  TODO...
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

        # TODO: Very similar to construct... can I merge somehow?
        # XXX: And now Declaration... need to generalize this.
        if line[0].startswith('end'):
            if len(line) == 1 and line[0] in ('end', 'end' + self.dtype):
                return True
            elif len(line) >= 2 and (line[0], line[1]) == ('end', self.dtype):
                return True
            else:
                return False


