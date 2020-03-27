import os

from flint.project import Project

# TODO: Use docutils to produce formatted output?  Is this a thing?
#   - It seems possible but is very convoluted.
#   - docutils has no Writer() for reST, but it can write XML if you give
#     it some template file? (.xsd?)
#   - This is all beyond my skillset.  But I doubt that it is worth pursuing.


def main():
    proj = Project()
    proj.parse('mom6')

    doc_path = 'docs'
    os.makedirs(doc_path, exist_ok=True)

    for src in proj.files:
        src_fname = os.path.basename(src.path)
        doc_fname = os.path.splitext(src_fname)[0] + '.rst'
        doc_fpath = os.path.join(doc_path, doc_fname) 
        with open(doc_fpath, 'w') as doc:
            # TODO: Prepare a list, then use doc.writelines()
            doc.write('=' * len(src.path) + '\n')
            doc.write(src.path + '\n')
            doc.write('=' * len(src.path) + '\n')
            doc.write('\n')

            depth = 0
            for unit in src.units:
                print_unit(doc, unit, depth)


def print_unit(doc, unit, depth):
    indent = depth * ' '
    doc.write(indent + unit.name + '\n')
    doc.write(indent + len(unit.name) * '-' + '\n')
    doc.write(unit.doc.header)
    doc.write(indent + len(unit.name) * '-' + '\n')
    if unit.doc.docstring:
        for line in unit.doc.docstring.split('\n'):
            doc.write(indent + line + '\n')
        doc.write('\n')

    for var in unit.variables:
        if var.doc.docstring:
            doc.write(indent + '- ' + var.name + '\n')
            for line in var.doc.docstring.split('\n'):
                doc.write(indent + '  ' + line + '\n')
            doc.write('\n')

    for subprog in unit.subprograms:
        print_unit(doc, subprog, depth + 2)

    if unit.doc.footer:
        for line in unit.doc.footer.split('\n'):
            doc.write(indent + line + '\n')
        doc.write('\n')

if __name__ == '__main__':
    main()
