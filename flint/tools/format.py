from flint.project import Project

def format_statements(project_dirs, include_dirs=None):
    proj = Project()

    if include_dirs:
        proj.include_dirs = include_dirs + proj.include_dirs

    proj.reformat = True

    proj.parse(*project_dirs)
