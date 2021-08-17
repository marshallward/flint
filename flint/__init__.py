"""A Fortran source code analysis tool.

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
from flint.project import Project

# Is epsilon a valid version?
__version__ = '0.0.1'


def parse(*paths, includes=None, excludes=None):
    include_dirs = includes if includes else []
    exclude_dirs = excludes if excludes else []

    project = Project()
    project.include_dirs = include_dirs

    project.parse(*paths, excludes=exclude_dirs)

    return project
