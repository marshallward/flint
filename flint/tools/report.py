"""flint report command

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import os
import sys

from flint.lines import Lines
from flint.project import Project
from flint.statement import Statement

MAX_STMT_LENGTH = 132
MAX_LINE_LENGTH = 512


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
            # XXX: Keep this?  Or just re-compute when needed?
            out = ''.join(line)

            # NOTE: Each of these tests should be packed up and moved to a
            #  separate function, or even into a module.  But for now, we 
            #  provide light implementations in this function.

            # Trailing whitespace
            if line and line[-1] and line[-1][-1].isspace():
                mesg = 'Trailing whitespace'
                print('{}({}): {}'.format(filename, line_number, mesg))

                if sys.stdout.isatty():
                    idx = len(out.rstrip())
                    print(out[:idx] + '\033[41m' + out[idx:] + '\033[0m')
                else:
                    print(out + '↵')

            # Statement length
            if line and line[-1].startswith('!'):
                stmt_len = len(''.join(line[:-1]).rstrip())
            else:
                stmt_len = len(''.join(line).rstrip())

            if stmt_len > MAX_STMT_LENGTH:
                mesg = 'Excessive statement length'
                print('{}({}): {}'.format(filename, line_number, mesg))

                idx = MAX_STMT_LENGTH

                if sys.stdout.isatty():
                    print(out[:idx] + '\033[31m' + out[idx:] + '\033[0m')
                else:
                    print(out[:idx] + '|' + out[idx:] + '|')

            # Line length
            # NOTE: This is a "soft limit" which includes comments
            if len(out) > MAX_LINE_LENGTH:
                mesg = 'Excessive line length'
                print('{}({}): {}'.format(filename, line_number, mesg))

                idx = MAX_LINE_LENGTH

                if sys.stdout.isatty():
                    print(out[:idx] + '\033[31m' + out[idx:] + '\033[0m')
                else:
                    print(out[:idx] + '|' + out[idx:] + '|')

            # Mixed tabs and spaces

            # First check indentation header
            if line and line[0].isspace() and all(c in line[0] for c in ' \t'):
                mesg = 'Indentation has mixed tabs and spaces.'
                print('{}({}): {}'.format(filename, line_number, mesg))

                if sys.stdout.isatty():
                    sample = (
                        line[0].replace('\t', '\033[31m\\t\033[0m')
                        + ''.join(line[1:])
                    )
                else:
                    sample = (
                        line[0].replace('\t', '\\t')
                        + ''.join(line[1:])
                    )
                print(sample)

            # Next check for tabs in source code separators
            # NOTE: By starting at index 1, we exclude either an indent if
            #   present, or the first semantic token if absent.  Neither should
            #   be part of this test, so it ought to remain correct.
            if any('\t' in tok for tok in line[1:] if tok.isspace()):
                mesg = 'Tab stop in statement of source code'
                print('{}({}): {}'.format(filename, line_number, mesg))
                if sys.stdout.isatty():
                    print(line[0]
                        + ''.join(line[1:]).replace('\t','\033[31m\\t\033[0m')
                    )
                else:
                    print(line[0] + ''.join(line[1:]).replace('\t','\\t'))
