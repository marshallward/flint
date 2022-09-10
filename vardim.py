"""flint gendoc command

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import os
import flint

debug = False
#debug = True

def main():
    var_dim_missing = {}

    proj = flint.parse('samples/mom6',
                       excludes='samples/mom6/src/equation_of_state/TEOS10')

    for src in proj.sources:
        vmiss = []
        for unit in src.units:

            # First parse the module variables
            for var in unit.variables:
                # This will have to be a function

                # Only parse real variables
                if var.type != 'real':
                    continue

                # Weak test, but good enough for now
                dim_l = var.doc.docstring.find('[')
                dim_r = var.doc.docstring.find(']') + 1
                dim_str = var.doc.docstring[dim_l:dim_r]

                if debug:
                    print('{}: {}'.format(src.path, var.doc.docstring))

                if not dim_str:
                    vmiss.append(var)

            # TODO: Derived types
            for dtype in unit.derived_types:
                # Durr
                for var in dtype.variables:
                    if var.type != 'real':
                        continue

                    # Weak test, but good enough for now
                    dim_l = var.doc.docstring.find('[')
                    dim_r = var.doc.docstring.find(']') + 1
                    dim_str = var.doc.docstring[dim_l:dim_r]

                    if debug:
                        print('{}: {}'.format(src.path, var.doc.docstring))

                    if not dim_str:
                        vmiss.append(var)

            for prog in unit.subprograms:
                # Durr x2
                for var in prog.variables:
                    if var.type != 'real':
                        continue

                    # Weak test, but good enough for now
                    dim_l = var.doc.docstring.find('[')
                    dim_r = var.doc.docstring.find(']') + 1
                    dim_str = var.doc.docstring[dim_l:dim_r]

                    if debug:
                        print('{}: {}'.format(src.path, var.doc.docstring))

                    if not dim_str:
                        vmiss.append(var)

        if vmiss:
            var_dim_missing[src] = vmiss

    # Print output
    for src in var_dim_missing:
        print(79 * '=')
        print(src.path)
        print(len(src.path) * '-')

        for var in var_dim_missing[src]:
            print('L{}: {}'.format(var.stmt.line_number, var.name))

if __name__ == '__main__':
    main()
