"""flint Interface class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from flint.document import Document
from flint.statement import Statement


class Interface(object):
    def __init__(self):
        self.name = None

        # Contents could be stored here...
        self.abstract = None
        self.procedures = []

        # Code data
        self.statements = []
        self.doc = Document()

    def parse(self, statements):
        self.parse_header(statements.current_line)

        for stmt in statements:
            if self.procedure_stmt(stmt):
                self.parse_procedure_stmt(stmt)
            elif stmt[0] in ('function', 'subroutine'):
                stmt.tag = 'S'
                self.statements.append(stmt)
            elif self.end_interface_stmt(stmt):
                break
            else:
                stmt.tag = 'I'
                self.statements.append(stmt)

        # Finalisation
        stmt = statements.current_line
        stmt.tag = 'I'
        self.statements.append(stmt)

    def parse_header(self, stmt):
        tokens = iter(stmt)
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

        stmt.tag = 'I'
        self.statements.append(stmt)

    def procedure_stmt(self, stmt):
        # XXX: Assert self.name is set?
        return stmt[0] == 'procedure' or stmt[:2] == ('module', 'procedure')

    def parse_procedure_stmt(self, stmt):
        stmt.tag = 'P'
        self.statements.append(stmt)

        tokens = iter(stmt)
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

    def end_interface_stmt(self, stmt):
        if stmt[0].startswith('end'):
            if len(stmt) == 1 and stmt[0] == 'endinterface':
                return True
            elif len(stmt) >= 2 and (stmt[0], stmt[1]) == ('end', 'interface'):
                # TODO: other generic-spec tests
                if len(stmt) >= 3:
                    assert stmt[2] == self.name
                return True
            else:
                return False
