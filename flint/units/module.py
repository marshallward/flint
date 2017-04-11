from flint.units.unit import Unit
from flint.units.subroutine import Subroutine


class Module(Unit):
    subprograms = {
            'function': None,
            'subroutine': Subroutine,
    }

    def parse(self, lines):
        """Parse the lines of a program unit.

        Each program unit consists of three sections:

        1. Specification part (R204)
        2. Execution part (R209)
        3. Subprograms:
           a. Internal subprogram part (R211)
           b. Module subprogram part (R1107)

        None of this has yet been implemented.  Below is just some basic
        handling of DO and IF constructs.
        """
        self.parse_name(lines.current_line)
        self.parse_specification(lines)
        self.parse_subprogram(lines)

    def parse_subprogram(self, lines):
        for line in lines:
            if line[0] in Module.subprograms:
                print('{}: {}'.format(line[0][0].upper(), ' '.join(line)))

            subname = line[0]
            subprog = Module.subprograms[subname]()
            subprog.parse(lines)

        else:
            # Unresolved line
            print('X: {}'.format(' '.join(line)))
