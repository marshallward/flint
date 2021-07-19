from flint.project import Project
from flint.statement import Statement

def format_statements(project_dirs, include_dirs=None):
    proj = Project()
    if include_dirs:
        proj.include_dirs = include_dirs + proj.include_dirs

    proj.parse(*project_dirs)

    for src in proj.files:
        print_formatted_stmt(src.statements)


def print_formatted_stmt(statements, depth=None):
    if depth is None:
        depth = 0

    for stmt in statements:
        if isinstance(stmt, Statement):
            indent = '  ' * depth
            print(indent + stmt.reformat())
        else:
            print_formatted_stmt(stmt, depth+1)
