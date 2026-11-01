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
        self.subprograms = []

        # Code data
        self.statements = []
        self.doc = Document()

    def parse(self, statements):
        # Unit owns interfaces too; defer this import to avoid a module cycle.
        from flint.units.unit import Unit

        self.parse_header(statements.current_line)

        for stmt in statements:
            if self.procedure_stmt(stmt):
                self.parse_procedure_stmt(stmt)
            elif self.end_interface_stmt(stmt):
                break
            elif (index := Unit.header_index(stmt)) is not None and stmt[index] in ('function', 'subroutine'):
                body = Unit()
                body.parse(statements)
                self.subprograms.append(body)
                self.statements.extend(body.statements)
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
        return stmt[0] == 'procedure' or stmt[:2] == ['module', 'procedure']

    def parse_procedure_stmt(self, stmt):
        stmt.tag = 'P'
        self.statements.append(stmt)

        start = 2 if stmt[0] == 'module' else 1
        if stmt[start:start + 1] == ['::']:
            start += 1
        self.procedures.extend(token for token in stmt[start:] if token != ',')

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
