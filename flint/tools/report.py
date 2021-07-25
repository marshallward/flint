import os

from flint.project import Project
from flint.statement import Statement


def report_issues(project_dirs, include_dirs=None):
    proj = Project()
    if include_dirs:
        proj.include_dirs = include_dirs + proj.include_dirs

    proj.parse(*project_dirs)

    ws_events = []
    for src in proj.files:
        events = report_trailing_whitespace(src.statements)
        # XXX: DO this in Statement, not here!!
        for event in events:
            event.src = src
        ws_events.extend(events)

    for event in ws_events:
        filename = os.path.basename(event.src.path)
        # TODO: Print statement with whitespace but not comments, etc
        print('{}({}): {}'.format(filename, event.line_number, event.gen_stmt()))


def report_trailing_whitespace(statements):
    events = []
    for stmt in statements:
        # TODO: Check for whitespace after line breaks (&)
        # TODO: Non-statements also should not have whitespace (comments)
        tail = stmt[-1].tail
        if '\n' in tail:
            end = tail[:tail.index('\n')]
            if end and end[-1] and end[-1][-1] in ' \t':
                events.append(stmt)

    return events
