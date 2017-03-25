class Program(object):

    def __init__(self, name):
        self.name = name

        self.modules = []
        self.functions = []
        self.variables = []

    def parse(self, lines):
        for line in lines:
            # Termination
            if line[0].startswith('end'):
                if (line[0] == 'end' and line[1] == 'program' or
                        line[0] == 'endprogram'):
                    print(' '.join(line))
                    break
                else:
                    print('XX: {}'.format(line))
            else:
                # Unhandled
                print('X: {}'.format(line))
