from flint.document import Document
from flint.statement import Statement


# XXX: Separate parsing from the actual object itself and its manipulation!!
class Interface(object):
    def __init__(self):
        self.name = None

        # Contents could be stored here...
        self.abstract = None
        self.procedures = []

        # Code data
        self.statements = []
        self.doc = Document()

    def parse(self, lines):
        self.parse_header(lines.current_line)

        for line in lines:
            if self.procedure_stmt(line):
                self.parse_procedure_stmt(line)
            elif line[0] in ('function', 'subroutine'):
                stmt = Statement(lines.current_line, tag='S')
                self.statements.append(stmt)
            elif self.end_interface_stmt(line):
                break
            else:
                stmt = Statement(line, tag='I')
                self.statements.append(stmt)

        # Finalisation
        stmt = Statement(lines.current_line, tag='I')
        self.statements.append(stmt)

    def parse_header(self, line):
        tokens = iter(line)
        tok = next(tokens)

        if tok == 'abstract':
            self.abstract = True
            tok = next(tokens)
        assert tok == 'interface'

        # TODO: Parse generic-spec (operator, assignment, etc)
        try:
            self.name = next(tokens)
        except StopIteration:
            pass

        stmt = Statement(line, tag='I')
        self.statements.append(stmt)

    def procedure_stmt(self, line):
        # XXX: Assert self.name is set?
        return line[0] == 'procedure' or line[:2] == ('module', 'procedure') 

    def parse_procedure_stmt(self, line):
        stmt = Statement(line, tag='P')
        self.statements.append(stmt)

        tokens = iter(line)
        tok = next(tokens)

        # TODO: Check if procedure belongs to a module
        if tok == 'module':
            tok = next(tokens)

        assert tok == 'procedure'
        next(tokens)

        if tok == '::':
            tok = next(tokens)

        # TODO: List of procedures; this just takes the first one!
        # TODO: Validate the name
        self.procedures.append(tok)

    def end_interface_stmt(self, line):
        if line[0].startswith('end'):
            if len(line) == 1 and line[0] == 'endinterface':
                return True
            elif len(line) >= 2 and (line[0], line[1]) == ('end', 'interface'):
                # TODO: other generic-spec tests
                if len(line) >= 3:
                    assert line[2] == self.name
                return True
            else:
                return False


