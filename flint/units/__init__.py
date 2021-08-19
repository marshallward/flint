"""flint program unit classes

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from flint.units.subroutine import Subroutine, is_subroutine
from flint.units.function import Function, is_function
from flint.units.module import Module, is_module
from flint.units.submodule import Submodule, is_submodule
from flint.units.program import Program

def get_program_unit_type(line):
    if is_subroutine(line):
        return Subroutine
    elif is_function(line):
        return Function
    elif is_module(line):
        return Module
    elif is_submodule(line):
        return Submodule
    else:
        # At this point, assume that there is either a program-stmt, or has no
        # declaration and is an implicit main function.
        return Program
