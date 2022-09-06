"""flint gendoc command

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import os
import flint

debug = False
#debug = True

proj = flint.parse('samples/mom6')

for mod in proj.modules:
    print(79 * '=')
    mod_title = mod.name if mod.name else 'External'
    print(mod_title)
    print(len(mod_title) * '=')

    for proc in mod.subprograms:
        for var in proc.variables:
            if var.type != 'real':
                continue

            # Not a great test, but syntax is probably not formal anyway...
            dim_l = var.doc.docstring.find('[')
            dim_r = var.doc.docstring.find(']') + 1

            dim_str = var.doc.docstring[dim_l:dim_r]

            print('{}: {}'.format(var.name, dim_str))
            if debug:
                print(4*' ' + var.doc.docstring)
