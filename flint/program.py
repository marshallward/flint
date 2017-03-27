CONSTRUCTS = ['do', 'if']

class Program(object):

    def __init__(self, name):
        self.name = name

        self.modules = []
        self.functions = []
        self.variables = []

    def parse(self, lines):
        for line in lines:
            # Join extended lines
            # (TODO: Roll this into a lines iterator)
            while (line[-1] == '&'):
                line = line[:-1] + next(lines)

            # Execution constructs
            if line[0] in CONSTRUCTS:
                print(' '.join(line))
                self.parse_construct(line[0], lines)

            # Termination
            elif line[0].startswith('end'):
                if (line[0] == 'end' and line[1] == 'program' or
                        line[0] == 'endprogram'):
                    print(' '.join(line))
                    break
                else:
                    # Should never happen?
                    print('X: {}'.format(line))
            else:
                # Unhandled
                print('P: {}'.format(line))

    def parse_construct(self, ctype, lines):
        for line in lines:
            if line[0].startswith('end'):
                if (line[0] == 'end' and line[1] == ctype or
                        line[0] == 'end' + ctype):
                    print(' '.join(line))
                    break
                else:
                    # Should never happen?
                    print('X: {}'.format(line))
            else:
                # Unhandled
                print('C: {}'.format(line))
