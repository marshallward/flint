"""flint gendoc command

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import os

from flint.project import Project
import flint.units


def generate_docs(srcdirs, docdir, includes=None, excludes=None):
    proj = Project()
    if includes:
        proj.include_dirs += includes

    proj.parse(*srcdirs, excludes=excludes)

    os.makedirs(docdir, exist_ok=True)

    for mod in proj.modules:
        doc_fname = mod.name + '.rst'
        doc_fpath = os.path.join(docdir, doc_fname)
        with open(doc_fpath, 'w') as doc:
            mod_title = mod.name + ' module reference'
            doc.write('=' * len(mod_title) + '\n')
            doc.write(mod_title + '\n')
            doc.write('=' * len(mod_title) + '\n')
            doc.write(mod.doc.header + '\n')
            doc.write('\n')

            if mod.derived_types:
                doc.write('Data Types\n')
                doc.write('==========\n')

                doc.write('.. list-table::\n\n')
                for dtype in mod.derived_types:
                    doc.write('   * - |{0}|_\n'.format(dtype.name))
                    doc.write('     - {0}\n'.format(dtype.doc.header))
                    doc.write('\n')
                    doc.write('\n')

            if mod.subprograms:
                doc.write('Functions/Subroutines\n')
                doc.write('=====================\n')

                doc.write('.. list-table::\n\n')
                for prog in mod.subprograms:
                    doc.write('   * - |' + prog.name + '|_\n')
                    doc.write('     - ' + prog.doc.header + '\n')
                    doc.write('\n')
                    doc.write('\n')

            if mod.doc.footer:
                doc.write('Detailed Description\n')
                doc.write('====================\n')
                for line in mod.doc.footer.split('\n'):
                    doc.write(line + '\n')
                doc.write('\n')

            if mod.derived_types:
                depth = 0
                doc.write('Type Documentation\n')
                doc.write('==================\n')
                # TODO: Why did I even name these `blocks`?
                for dtype in mod.derived_types:
                    print_unit(doc, dtype, depth)

            if mod.subprograms:
                depth = 0
                doc.write('Functions/Subroutine Documentation\n')
                doc.write('==================================\n')
                doc.write('\n')
                for sub in mod.subprograms:
                    print_unit(doc, sub, depth)

            if mod.derived_types:
                doc.write('\n')
                doc.write('.. Type/Interface labels\n')
                doc.write('\n')
                for dtype in mod.derived_types:
                    doc.write(
                        '.. |{0}| replace:: ``{0}``\n'.format(dtype.name)
                    )

            if mod.subprograms:
                doc.write('\n')
                doc.write('.. Subprogram labels\n')
                doc.write('\n')
                for prog in mod.subprograms:
                    doc.write('.. |{0}| replace:: ``{0}``\n'.format(prog.name))


# XXX: I should probably split print_unit() from, say, print_type(), etc.
def print_unit(doc, unit, depth):
    indent = depth * ' '

    doc.write(indent + '.. _' + unit.name + ':\n')
    doc.write('\n')

    doc.write(indent + ' '.join(unit.doc.statement) + '\n')
    for line in unit.doc.header.split('\n'):
        doc.write(indent + '  ' + line + '\n')
    doc.write('\n')

    if unit.variables:
        doc.write(indent + '  ' + 'Parameters\n')

    for var in unit.variables:
        if var.doc.docstring:
            doc.write(indent + '    ' + '- **' + var.name + '** :: ')
            if var.intent:
                doc.write('[{0}] '.format(var.intent))
            doc.write(var.doc.docstring + '\n')
            doc.write('\n')

    if unit.callees:
        doc.write('\n')
        doc.write(indent + 'Calls into\n')
        doc.write(
            indent + '  '
            + ' '.join('|{0}|_'.format(callee) for callee in unit.callees)
            + '\n'
        )
        doc.write('\n')

    if unit.callers:
        doc.write('\n')
        doc.write(indent + 'Called by\n')
        doc.write(
            indent + '  '
            + ' '.join('|{0}|_'.format(caller) for caller in unit.callers)
            + '\n'
        )
        doc.write('\n')

    for dtype in unit.derived_types:
        print_unit(doc, dtype, depth + 2)

    for subprog in unit.subprograms:
        print_unit(doc, subprog, depth + 2)
