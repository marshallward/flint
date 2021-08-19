"""flint Module class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from flint.syntax import is_name
from flint.units.unit import Unit


class Module(Unit):
    intrinsics = [
        # ISO/IEC Technical Report (TR) 15580:1998(E)
        'ieee_arithmetic',
        'ieee_exceptions',
        'ieee_features',

        # Fortran 2003
        'iso_c_binding',
        'iso_fortran_env',

        # OpenMP (version?)
        'omp_lib',
        'omp_lib_kinds',
    ]

    # Placeholder class for now
    def __init__(self):
        super(Module, self).__init__()


def is_module(line):
    """Return True if the line is a valid *module-stmt*."""
    return len(line) == 2 and line[0] == 'module' and is_name(line[1])
