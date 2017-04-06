from flint.unit import Unit


class Module(Unit):

    def __init__(self):
        self.name = None

        self.modules = []
        self.functions = []
        self.variables = []

    def parse_name(self, line):
        assert(len(line) <= 2)
        assert(line[0] == 'module')

        if len(line) == 2:
            name = line[1]
        else:
            name = None

        self.name
