"""flint Construct class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from flint.calls import get_callable_symbols
from flint.statement import Statement


class Construct(object):

    construct_types = [
        'associate',
        'block',
        'critical',
        'do',
        'if',
        'forall',
        'where',
        # Proxy for keyword pairs below
        'change',
        'select',
    ]

    # TODO: Ignore these for now
    construct_kw_pairs = [
        ('change', 'team'),
        ('select', 'case'),
        ('select', 'rank'),
        ('select', 'type'),
    ]

    # TODO: Override for individual constructs?
    @staticmethod
    def construct_stmt(stmt):
        if stmt.kind == 'assignment':
            return False
        stmt = stmt.code_tokens
        if not stmt:
            return False

        # TODO: Actual rules vary for every construct type, not just 'if'
        if stmt[0] in Construct.construct_types:
            if stmt[0] == 'block':
                # BLOCK has no operands. The keyword is also a legal object
                # name, e.g. block%name = '' or block => another_block.
                return len(stmt) == 1
            elif stmt[0] == 'if':
                return (stmt[0], stmt[-1]) == ('if', 'then')
            elif stmt[0] in ('where', 'forall'):
                assert stmt[1] == '('
                par_count = 1
                for idx, tok in enumerate(stmt[2:], start=2):
                    if tok == '(':
                        par_count += 1
                    elif tok == ')':
                        par_count -= 1

                    if par_count == 0:
                        break

                return idx == len(stmt) - 1

                # XXX: Need to figure this out!
                return
            else:
                return True

    def end_statement(self, stmt):
        if (self.terminal_label is not None and stmt.statement_label is not None
                and int(stmt.statement_label) == self.terminal_label):
            return True
        if stmt.kind == 'assignment':
            return False
        words = stmt.code_tokens
        if not words:
            return False
        if words[0] == 'end' + self.ctype:
            suffix = words[1:]
        elif words[:2] == ['end', self.ctype]:
            suffix = words[2:]
        else:
            return False
        if self.ctype == 'team' and suffix[:1] == ['(']:
            depth = 0
            for index, token in enumerate(suffix):
                if token == '(':
                    depth += 1
                elif token == ')':
                    depth -= 1
                    if depth == 0:
                        suffix = suffix[index + 1:]
                        break
            else:
                return False
        return not suffix or (len(suffix) == 1 and self.name is not None
                              and suffix[0] == self.name.lower())

    def __init__(self, unit, depth=1):
        self.ctype = None
        self.name = None
        self.terminal_label = None

        # Program unit containing the construct
        self.unit = unit

        # Testing
        self.depth = depth
        self.statements = []

    def parse(self, statements):
        stmt = statements.current_line
        self.name = stmt.construct_name
        words = stmt.code_tokens
        self.ctype = 'team' if words[:2] == ['change', 'team'] else words[0]
        if self.ctype == 'do' and len(words) > 1 and words[1].isdigit():
            self.terminal_label = int(words[1])

        stmt.tag = 'C'
        self.statements.append(stmt)

        # Parse the contents of the construct
        for stmt in statements:
            callables = get_callable_symbols(stmt, self.unit.variables)
            self.unit.callees.update(callables)

            if Construct.construct_stmt(stmt):
                cons = Construct(self.unit, depth=self.depth + 1)
                cons.parse(statements)
                self.statements.extend(cons.statements)
                # Legacy nested DOs may share one terminal statement. The
                # child already recorded it, so close without appending again.
                if self.terminal_label is not None and self.end_statement(statements.current_line):
                    break
            elif self.end_statement(stmt):
                stmt.tag = 'C'
                self.statements.append(stmt)
                break
            else:
                # Unhandled
                stmt.tag = 'e'
                self.statements.append(stmt)
