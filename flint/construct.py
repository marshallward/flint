class Construct(object):

    construct_kw = [
            'associate',
            'block',
            'critical',
            'do',
            'if',
            'forall',
            'where',
    ]

    construct_kw_pairs = [
            ('change', 'team'),
            ('select', 'case'),
            ('select', 'rank'),
            ('select', 'type'),
    ]

    def __init__(self):
        self.ctype = None
        self.name = None

    def parse(self, lines):
        line = self.current_line

        if line[0][-1] == ':':
            self.name = line[0][:-1]
            line = line[1:]

        self.ctype = self.get_block_type(line)

        for line in lines:
            # Execution constructs
            if line[0] == 'do' or (line[0], line[-1]) == ('if', 'then'):
                print('C: {} '.format(' '.join(line)))
                self.parse_construct(line[0], lines)

            elif line[0].startswith('end'):
                if (line[0] == 'end' and line[1] == ctype or
                        line[0] == 'end' + ctype):
                    print('C: {} '.format(' '.join(line)))
                    break
                else:
                    # Should never happen?
                    print('X: {}'.format(' '.join(line)))
            else:
                # Unhandled
                print('C: {}'.format(' '.join(line)))

    def get_block_type(self, line):

