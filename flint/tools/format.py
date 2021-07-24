from flint.project import Project
from flint.statement import Statement

def format_statements(project_dirs, include_dirs=None):
    proj = Project()
    if include_dirs:
        proj.include_dirs = include_dirs + proj.include_dirs

    proj.parse(*project_dirs)

    for src in proj.files:
        for stmt in src.statements:
            print(stmt.reformat())
