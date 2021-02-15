"""Installation script for flint."""
import os
import sys

try:
    from setuptools import setup
    from setuptools import Command
except ImportError:
    from distutils.core import setup
    from distutils.core import Command

# Project details
project_name = 'flint'
project_version = __import__(project_name).__version__
project_readme_fname = 'README.rst'
project_pkgs = [path for (path, dirs, files) in os.walk(project_name)
                if '__init__.py' in files]


# README
with open(project_readme_fname) as f:
    project_readme = f.read()


# Project setup
setup(
    name = project_name,
    version = project_version,
    description = 'Fortran code analysis tool',
    long_description = project_readme,
    author = 'Marshall Ward',
    author_email = 'flint@marshallward.org',
    url = 'http://github.com/marshallward/flint',

    packages = project_pkgs,

    entry_points={
        'console_scripts': [
            'flint = flint.cli:parse',
        ]
    },

    classifiers = [
        'Development Status :: 1 - Planning',
        'Programming Language :: Python :: 3.9',
        'Topic :: Utilities',
    ]
)
