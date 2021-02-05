import os

from flint.project import Project
import flint.units

# TODO: Use docutils to produce formatted output?  Is this a thing?
#   - It seems possible but is very convoluted.
#   - docutils has no Writer() for reST, but it can write XML if you give
#     it some template file? (.xsd?)
#   - This is all beyond my skillset.  But I doubt that it is worth pursuing.


def main():
    proj = Project()
    #proj = Project(verbose=True)

    proj.parse(
        'mom6/src',
        'mom6/config_src/solo_driver',
        'mom6/config_src/dynamic_symmetric'
    )
    doc_path = 'docs'

    #proj.parse('core')
    #doc_path = 'cdoc'

    os.makedirs(doc_path, exist_ok=True)

    # Gather modules
    ## NOTE: parse() should probably add these to proj
    #modules = []
    #for src in proj.files:
    #    for unit in src.units:
    #        if isinstance(unit, flint.units.Module):
    #            modules.append(unit)

    for mod in proj.modules:
        doc_fname = mod.name + '.rst'
        doc_fpath = os.path.join(doc_path, doc_fname)
        with open(doc_fpath, 'w') as doc:
            mod_title = mod.name + ' module reference'
            doc.write('=' * len(mod_title) + '\n')
            doc.write(mod_title + '\n')
            doc.write('=' * len(mod_title) + '\n')
            doc.write(mod.doc.header + '\n')
            doc.write('\n')

            if mod.blocks:
                doc.write('Data Types\n')
                doc.write('==========\n')

                doc.write('.. list-table::\n\n')
                for dtype in mod.blocks:
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

            if mod.blocks:
                depth = 0
                doc.write('Type Documentation\n')
                doc.write('==================\n')
                # TODO: Why did I even name these `blocks`?
                for unit in mod.blocks:
                    print_unit(doc, unit, depth)

            if mod.subprograms:
                depth = 0
                doc.write('Functions/Subroutine Documentation\n')
                doc.write('==================================\n')
                doc.write('\n')
                for sub in mod.subprograms:
                    print_unit(doc, sub, depth)

            if mod.blocks:
                doc.write('\n')
                doc.write('.. Type/Interface labels\n')
                doc.write('\n')
                for block in mod.blocks:
                    doc.write('.. |{0}| replace:: ``{0}``\n'.format(block.name))

            if mod.subprograms:
                doc.write('\n')
                doc.write('.. Subprogram labels\n')
                doc.write('\n')
                for prog in mod.subprograms:
                    doc.write('.. |{0}| replace:: ``{0}``\n'.format(prog.name))

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
            doc.write(var.doc.docstring + '\n')
            doc.write('\n')

    if unit.callees:
        doc.write('\n')
        doc.write(indent + 'Calls into\n')
        doc.write(indent + '  ' + ' '.join('|{0}|_'.format(callee) for callee in unit.callees) + '\n')
        doc.write('\n')

    for block in unit.blocks:
        print_unit(doc, block, depth + 2)

    for subprog in unit.subprograms:
        print_unit(doc, subprog, depth + 2)

    # Only modules have footers, I think...
    #if unit.doc.footer:
    #    doc.write(indent + 'Detailed Description\n')
    #    doc.write(indent + '--------------------\n')
    #    for line in unit.doc.footer.split('\n'):
    #        doc.write(indent + line + '\n')
    #    doc.write('\n')

if __name__ == '__main__':
    main()
