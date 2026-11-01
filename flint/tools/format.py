"""flint format command

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import flint
from flint.formatting.rules import ALL_RULES
from flint.formatting.config import configured_rules, load_config
from flint.formatting.runner import check_spacing, report_spacing


def _names(values):
    if values is None:
        return None
    return [name.strip() for value in values for name in value.split(',') if name.strip()]


def format_statements(srcdirs=(), includes=None, excludes=None, *, only=None,
                      skip=(), list_rules=False, write=False, diff=False,
                      strict=None, do_controls=None, excluded_functions=None, indent=None,
                      config=None):
    """Report formatting issues; preview or write available spacing fixes."""
    if list_rules:
        print('\n'.join(ALL_RULES))
        return 0
    settings = load_config(config)
    checks, diagnostics = configured_rules(
        settings, only=_names(only), skip=_names(skip), strict=strict,
        do_controls=do_controls, excluded_functions=excluded_functions, indent=indent,
    )
    if excludes is None:
        excludes = settings.get('exclude')
    if not srcdirs:
        raise ValueError('Provide at least one source path, or use --list-rules')
    if not checks and not diagnostics:
        return 0
    project = flint.parse(*srcdirs, includes=includes, excludes=excludes)
    found = False
    # Diagnose before writing: source locations belong to the parsed snapshot.
    for name, check in diagnostics.items():
        for source in project.sources:
            for issue in check(source):
                found = True
                print(f'{issue.path}:{issue.line_number}: {name}: {issue.message}')
                print(f'  {issue.original}')
    if write or diff:
        status = report_spacing(check_spacing(project, checks.values()), write=write, diff=diff)
        return int(found or status)
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
