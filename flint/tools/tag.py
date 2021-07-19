from flint.project import Project
from flint.statement import Statement

def tag_statements(project_dirs, include_dirs=None):
    proj = Project()
    if include_dirs:
        proj.include_dirs = include_dirs + proj.include_dirs

    proj.parse(*project_dirs)

    for src in proj.files:
        print_tags(src.statements)


def print_tags(statements):
    for stmt in statements:
        if isinstance(stmt, Statement):
            print(stmt.gen_stmt())
        else:
            # Should probably assert that it's a Unit, Subroutine, etc..
            print_tags(stmt)
