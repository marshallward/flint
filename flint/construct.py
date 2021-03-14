from flint.calls import get_callable_symbols
from flint.fortlines import gen_stmt


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
    def statement(line):
        # Pop off construct label
        if line[0][-1] == ':':
            line = line[1:]

        # TODO: Actual rules vary for every construct type, not just 'if'
        if line[0] in Construct.construct_types:
            if line[0] == 'if':
                return (line[0], line[-1]) == ('if', 'then')
            elif line[0] == 'where':
                assert line[1] == '('
                par_count = 1
                for idx, tok in enumerate(line[2:], start=2):
                    if tok == '(':
                        par_count += 1
                    elif tok == ')':
                        par_count -= 1

                    if par_count == 0:
                        break

                return idx == len(line) - 1

                # XXX: Need to figure this out!
                return
            else:
                return True

    def end_statement(self, line):
        if line[0].startswith('end'):
            if len(line) == 1 and line[0] in ('end', 'end' + self.ctype):
                return True
            elif len(line) == 2 and (line[0], line[1]) == ('end', self.ctype):
                return True
            else:
                return False

        elif self.ctype == 'do' and len(line) > 1 and line[1] == 'continue':
            # TODO: Will line[0] always be a label?
            # TODO: Check if label is inside the 'do' construct?
            return True
        else:
            return False

    def __init__(self, unit, depth=1, verbose=False):
        self.ctype = None
        self.name = None
        self.verbose = verbose

        # Program unit containing the construct
        self.unit = unit

        # Testing
        self.depth = depth

    def parse(self, lines):
        line = lines.current_line
        # Check for construct label (and pop off)
        if line[0][-1] == ':':
            self.name = line[0][:-1]
            line = line[1:]

        if line[0] == 'select':
            self.ctype = line[1]
        else:
            self.ctype = line[0]

        if self.verbose:
            print('C: {}'.format(gen_stmt(line, self.depth - 1)))

        # Generate the list of variable names
        var_names = [v.name for v in self.unit.variables]

        # Parse the contents of the construct
        for line in lines:
            self.unit.callees.update(get_callable_symbols(line, var_names))

            if Construct.statement(line):
                cons = Construct(self.unit, depth=self.depth + 1, verbose=self.verbose)
                cons.parse(lines)
            elif self.end_statement(line):
                if self.verbose:
                    print('C: {}'.format(gen_stmt(line, self.depth)))
                break
            else:
                # Unhandled
                if self.verbose:
                    print('e: {}'.format(gen_stmt(line, self.depth)))
