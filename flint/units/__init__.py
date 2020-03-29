from flint.units.subroutine import Subroutine, is_subroutine
from flint.units.function import Function, is_function
from flint.units.module import Module, is_module


def get_program_unit_type(line):
    if is_subroutine(line):
        return Subroutine()
    elif is_function(line):
        return Function()
    elif is_module(line):
        return Module()
    else:
        # TODO: Submodule, block
        raise ValueError
