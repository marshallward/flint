import os

from flint.project import Project

proj = Project()
proj.parse('mom6')

def main():
    doc_path = 'docs'
    os.makedirs(doc_path, exist_ok=True)

    for src in proj.files:
        src_fname = os.path.basename(src.path)
        doc_fname = os.path.splitext(src_fname)[0] + '.rst'
        doc_fpath = os.path.join(doc_path, doc_fname) 
        with open(doc_fpath, 'w') as doc:
            # TODO: Use docutils to produce formatted output?  Is this a thing?
            # TODO: Prepare a list, then use doc.writelines()
            doc.write(src.path + '\n')
            doc.write('=' * len(src.path) + '\n')
            doc.write('\n')

            depth = 0
            for unit in src.units:
                print_unit(doc, unit, depth)


def print_unit(doc, unit, depth):
    indent = depth * ' '
    doc.write(indent + unit.name + '\n')
    for subprog in unit.subprograms:
        print_unit(doc, subprog, depth + 2)

if __name__ == '__main__':
    main()
