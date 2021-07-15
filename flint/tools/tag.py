from flint.project import Project

def tag_statements(project_dirs, include_dirs=None, reformat=False):
    proj = Project(verbose=True)

    if include_dirs:
        proj.include_dirs = include_dirs + proj.include_dirs

    proj.reformat = reformat

    proj.parse(*project_dirs)
