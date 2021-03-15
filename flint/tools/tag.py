from flint.project import Project


def tag_statements(project_dirs, reformat=False):
    proj = Project(verbose=True)
    proj.reformat = reformat
    proj.parse(*project_dirs)
