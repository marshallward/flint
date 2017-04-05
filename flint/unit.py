class Unit(object):

    def __init__(self, name):
        self.name = name

        self.modules = []
        self.functions = []
        self.variables = []

    @staticmethod
    def parse_name(line):
        raise NotImplementedError

    def parse(self, lines):
        for line in lines:
            # Execution constructs
            if line[0] == 'do' or (line[0], line[-1] == 'if', 'then'):
                print('*: {} '.format(' '.join(line)))
                self.parse_construct(line[0], lines)

            # Termination
            elif line[0].startswith('end'):
                if (line[0] == 'end' and line[1] == 'program' or
                        line[0] == 'endprogram'):
                    print('*: {} '.format(' '.join(line)))
                else:
                    # Should never happen?
                    print('XXX: {}'.format(line))
            else:
                # Unhandled
                print('X: {}'.format(line))

    def parse_construct(self, ctype, lines):
        for line in lines:
            # Execution constructs
            if line[0] == 'do' or (line[0], line[-1] == 'if', 'then'):
                print('*: {} '.format(' '.join(line)))
                self.parse_construct(line[0], lines)

            elif line[0].startswith('end'):
                if (line[0] == 'end' and line[1] == ctype or
                        line[0] == 'end' + ctype):
                    print('*: {} '.format(' '.join(line)))
                else:
                    # Should never happen?
                    print('X: {}'.format(line))
            else:
                # Unhandled
                print('C: {}'.format(line))
