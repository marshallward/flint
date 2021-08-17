"""flint tag command

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import flint


def tag_statements(srcdirs, includes=None, excludes=None):
    proj = flint.parse(*srcdirs, includes=includes, excludes=excludes)

    for src in proj.sources:
        for stmt in src.statements:
            print(stmt.gen_stmt())
