"""flint report command

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import os
import sys

from flint.lines import Lines
from flint.project import Project
from flint.statement import Statement

MAX_LINE_LENGTH = 120


def report_issues(project_dirs, include_dirs=None):
    proj = Project()
    if include_dirs:
        proj.include_dirs = include_dirs + proj.include_dirs

    proj.parse(*project_dirs)

    for src in proj.files:
        filename = os.path.basename(src.path)

        lines = Lines(src.statements)
        line_number = 0

        for line in lines:
            line_number += 1
            out = ''.join(line)

            # Trailing whitespace
            if line and line[-1] and line[-1][-1].isspace():
                idx = len(out.rstrip())

                if sys.stdout.isatty():
                    mesg = out[:idx] + '\033[41m' + out[idx:] + '\033[0m'
                else:
                    mesg = out + '↵'

                print('{}({}): {}'.format(filename, line_number, mesg))

            # Line length
            if len(out) > MAX_LINE_LENGTH:
                idx = MAX_LINE_LENGTH

                if sys.stdout.isatty():
                    mesg = out[:idx] + '\033[31m' + out[idx:] + '\033[0m'
                else:
                    mesg = out[:idx] + '|' + out[idx:] + '|'

                print('{}({}): {}'.format(filename, line_number, mesg))
