class Construct(object):

    construct_types = [
        'associate',
        'block',
        'critical',
        'do',
        'if',
        'forall',
        'where',
        # TODO: Deal with pairs later
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

    @staticmethod
    def is_construct(line):
        # Pop off construct label
        if line[0][-1] == ':':
            line = line[1:]

        # TODO: Actual rules vary for every construct type, not just 'if'
        if line[0] in Construct.construct_types:
            if line[0] == 'if':
                return (line[0], line[-1]) == ('if', 'then')
            else:
                return True

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

        for line in lines:
            if Construct.is_construct(line):
                print('C: {}{} '.format(' ' * self.depth, ' '.join(line)))
                cons = Construct(depth=self.depth + 1)
                cons.parse(lines)

            elif line[0].startswith('end'):
                if (line[0] == 'end' and line[1] == self.ctype or
                        line[0] == 'end' + self.ctype):
                    print('C: {}{} '.format(' ' * self.depth, ' '.join(line)))
                    break
                else:
                    # Should never happen?
                    print('X: {}{} '.format(' ' * self.depth, ' '.join(line)))
            else:
                # Unhandled
                print('c: {}{} '.format(' ' * self.depth, ' '.join(line)))
