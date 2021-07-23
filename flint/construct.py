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
        'change'
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
        # Pop off construct label
        if stmt[0][-1] == ':':
            stmt = stmt[1:]

        # TODO: Actual rules vary for every construct type, not just 'if'
        if stmt[0] in Construct.construct_types:
            if stmt[0] == 'if':
                return (stmt[0], stmt[-1]) == ('if', 'then')
            elif stmt[0] == 'where':
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
        if stmt[0].startswith('end'):
            if len(stmt) == 1 and stmt[0] in ('end', 'end' + self.ctype):
                return True
            elif len(stmt) == 2 and (stmt[0], stmt[1]) == ('end', self.ctype):
                return True
            else:
                return False

        elif self.ctype == 'do' and len(stmt) > 1 and stmt[1] == 'continue':
            # TODO: Will stmt[0] always be a label?
            # TODO: Check if label is inside the 'do' construct?
            return True
        else:
            return False

    def __init__(self, unit, depth=1):
        self.ctype = None
        self.name = None

        # Program unit containing the construct
        self.unit = unit

        # Testing
        self.depth = depth
        self.statements = []

    def parse(self, statements):
        stmt = statements.current_line
        # Check for construct label (and pop off)
        if stmt[0][-1] == ':':
            self.name = stmt[0][:-1]
            stmt = stmt[1:]

        if stmt[0] == 'select':
            self.ctype = stmt[1]
        else:
            self.ctype = stmt[0]

        stmt.tag = 'C'
        self.statements.append(stmt)

        # Generate the list of variable names
        var_names = [v.name for v in self.unit.variables]

        # Parse the contents of the construct
        for stmt in statements:
            self.unit.callees.update(get_callable_symbols(stmt, var_names))

            if Construct.construct_stmt(stmt):
                cons = Construct(self.unit, depth=self.depth + 1)
                cons.parse(statements)
                self.statements.append(cons.statements)
            elif self.end_statement(stmt):
                stmt.tag = 'C'
                self.statements.append(stmt)
                break
            else:
                # Unhandled
                stmt.tag = 'e'
                self.statements.append(stmt)
