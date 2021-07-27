"""flint format command

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
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
