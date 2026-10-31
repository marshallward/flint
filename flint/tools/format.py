"""flint format command

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import flint
from flint.formatting.rules import RULES, select_rules
from flint.formatting.runner import check_spacing, report_spacing


def _names(values):
    if values is None:
        return None
    return [name.strip() for value in values for name in value.split(',') if name.strip()]


def format_statements(srcdirs=(), includes=None, excludes=None, *, only=None,
                      skip=(), list_rules=False, write=False, diff=False,
                      strict=False, do_controls=False, excluded_functions=()):
    """Report spacing violations by default; preview or write on request."""
    if list_rules:
        print('\n'.join(RULES))
        return 0
    checks = select_rules(_names(only), _names(skip), strict=strict,
                          do_controls=do_controls, excluded_functions=excluded_functions)
    if not srcdirs:
        raise ValueError('Provide at least one source path, or use --list-rules')
    if not checks:
        return 0
    project = flint.parse(*srcdirs, includes=includes, excludes=excludes)
    if write or diff:
        return report_spacing(check_spacing(project, checks.values()), write=write, diff=diff)
    found = False
    # Named reports use the same project. Per-rule results identify precisely
    # which policy proposed a change; fixing combines all rules before writing.
    for name, check in checks.items():
        for result in check_spacing(project, (check,)):
            found = True
            seen = set()
            for change in result.changes:
                if change.line_number not in seen:
                    seen.add(change.line_number)
                    print(f'{change.path}:{change.line_number}: {name}: {change.original}')
    return int(found)
