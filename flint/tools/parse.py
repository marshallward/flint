from flint.project import Project


def parse_lines(project_dirs):
    proj = Project(verbose=True)
    proj.parse(*project_dirs)
