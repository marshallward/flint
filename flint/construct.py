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

    def __init__(self, depth=1):
        self.ctype = None
        self.name = None

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

        print('C: {}{} '.format(' ' * (self.depth - 1), ' '.join(line)))

        for line in lines:
            if Construct.statement(line):
                cons = Construct(depth=self.depth + 1)
                cons.parse(lines)
            elif self.end_statement(line):
                print('C: {}{} '.format(' ' * self.depth, ' '.join(line)))
                break
            else:
                # Unhandled
                print('e: {}{} '.format(' ' * self.depth, ' '.join(line)))
