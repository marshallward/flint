from flint.unit import Unit

class Module(Unit):

    def __init__(self, name):
        self.name = name

        self.modules = []
        self.functions = []
        self.variables = []

    @staticmethod
    def parse_name(line):
        assert(len(line) <= 2)
        assert(line[0] == 'module')

        if len(line) == 2:
            name = line[1]
        else:
            name = None

        return name
