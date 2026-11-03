"""Callable symbol tracker.

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""


_IO_STATEMENTS = frozenset((
    'read', 'write', 'open', 'close', 'inquire', 'backspace', 'rewind',
    'endfile', 'flush', 'wait',
))


def _statement_keyword_indices(line):
    """Locate control and I/O keywords, including a logical IF's action.

    Fortran keywords are not reserved: only exclude the keyword at the action
    position, never a same-named procedure inside an expression or CALL.
    """
    start = getattr(line, 'code_index', 0)
    keywords = ()
    if start < len(line) and line[start].isdigit():
        start += 1
    if line[start:start + 3] == ['else', 'if', '(']:
        return (start + 1,)
    if line[start:start + 3] == ['select', 'case', '(']:
        return (start + 1,)
    if line[start:start + 2] == ['case', '(']:
        return (start,)
    if start < len(line) and line[start] == 'do':
        control = start + 1
        # A DO may have a termination label and an optional separating comma.
        if control < len(line) and line[control].isdigit():
            control += 1
        if control < len(line) and line[control] == ',':
            control += 1
        if line[control:control + 2] == ['while', '(']:
            return (control,)
    if line[start:start + 2] == ['if', '(']:
        keywords = (start,)
        depth = 0
        for index in range(start + 1, len(line)):
            if line[index] == '(':
                depth += 1
            elif line[index] == ')':
                depth -= 1
                if depth == 0:
                    start = index + 1
                    break
        else:
            return keywords
    if start < len(line) and line[start] in _IO_STATEMENTS:
        return (*keywords, start)
    return keywords


def get_callable_symbols(line, variables, *, variable_names=None):
    """Find callables, optionally reusing normalized variable names for a scope."""
    start = getattr(line, 'code_index', 0)
    if (start < len(line) and line[start].isdigit()
            and line[start + 1:start + 3] == ['format', '(']):
        # FORMAT descriptors (including nested groups and DT edit descriptors)
        # are not executable expressions and cannot contain procedure calls.
        return []
    keyword_indices = _statement_keyword_indices(line)
    candidates = [
        b for index, (a, b, c) in enumerate(zip(line, line[1:], line[2:]), 1)
        # TODO: Resolve derived-type components so type-bound procedures can be
        # distinguished from array/data components like obj%field(i,j).
        if c == '(' and a != '%' and b[0].isalpha() and index not in keyword_indices
    ]
    if not candidates:
        return []
    if variable_names is None:
        variable_names = {var.name.lower() for var in variables}
    return [name for name in candidates if name not in variable_names]
