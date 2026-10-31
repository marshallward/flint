"""Spacing of commas in known callable argument lists."""
from typing import NamedTuple
from functools import partial

from flint.intrinsics import intrinsic_fns
from flint.formatting.spacing import format_spacing, propose_edit, spacing_edits
from flint.formatting.runner import Change, run_spacing


NON_CALLABLE_PAREN_NAMES = {
    'backspace', 'close', 'endfile', 'flush', 'inquire', 'open', 'read',
    'rewind', 'wait', 'write',
}


class Context(NamedTuple):
    variable_names: set[str]
    callables: set[str]


def prepare_check(source, strict=False, excluded_functions=()):
    contexts = statement_contexts(source)
    empty = Context(set(), set())
    return lambda statement: collect_spacing_edits(
        statement, contexts.get(id(statement), empty), strict=strict,
        excluded_functions=excluded_functions,
    )


def comma_spacing_edits(token, strict=False):
    newline_indices = [index for index, item in enumerate(token.tail) if '\n' in item]
    if newline_indices:
        if not strict:
            return []
        newline_index = newline_indices[0]
        prefix = token.tail[:newline_index]
        if '&' in prefix and all(item.isspace() or item == '&' for item in prefix):
            return propose_edit(token.tail, [' ', '&'] + token.tail[newline_index:])
        return []
    return spacing_edits(token, after=' ', minimum=not strict)


def collect_contexts(unit, contexts):
    for subprogram in unit.subprograms:
        collect_contexts(subprogram, contexts)
    context = Context(
        variable_names={str(var.name).lower() for var in unit.variables},
        callables={str(name).lower() for name in unit.callees},
    )
    for statement in unit.statements:
        contexts.setdefault(id(statement), context)


def statement_contexts(source):
    contexts = {}
    for unit in source.units:
        collect_contexts(unit, contexts)
    return contexts


def is_known_callable(name, context):
    lowered = name.lower()
    return lowered in context.callables or lowered in intrinsic_fns


def opens_callable_group(statement, index, context):
    if statement[index] != '(' or index == 0:
        return False
    if statement.is_call_statement():
        depth = 0
        for tok in statement[statement.code_index + 1:index]:
            if tok == '(':
                depth += 1
            elif tok == ')':
                depth -= 1
        if depth == 0:
            return True
    prior = statement[index - 1]
    if not getattr(prior, 'is_name', False):
        return False
    if str(prior).lower() in NON_CALLABLE_PAREN_NAMES:
        return False
    if index >= 2 and statement[index - 2] == '%':
        return False
    if str(prior).lower() in context.variable_names:
        return False
    return is_known_callable(str(prior), context)


def collect_spacing_edits(statement, context, strict=False, excluded_functions=()):
    """Exclude named calls individually; nested calls are checked independently."""
    if statement.kind == 'declaration':
        return []
    edits = []
    excluded = {name.lower() for name in excluded_functions}
    paren_stack = []
    for index, token in enumerate(statement.tokens):
        if token == '(':
            check_commas = opens_callable_group(statement, index, context)
            if check_commas and str(statement[index - 1]).lower() in excluded:
                check_commas = False
            paren_stack.append(check_commas)
        elif token in ('[', '{', '(/'):
            paren_stack.append(False)
        elif token in (')', ']', '}', '/)'):
            if paren_stack:
                paren_stack.pop()
        elif token == ',' and paren_stack and paren_stack[-1]:
            edits.extend(comma_spacing_edits(token, strict=strict))
    return edits


def format_statements(path, statements, contexts, source_lines=None, strict=False,
                      excluded_functions=()):
    empty = Context(set(), set())
    formatted, changes = format_spacing(
        statements,
        lambda statement: collect_spacing_edits(
            statement, contexts.get(id(statement), empty), strict=strict,
            excluded_functions=excluded_functions,
        ), source_lines,
    )
    return formatted, [Change(path, c.line_number, c.original) for c in changes]


def run(paths, write=False, report=False, diff=False, excludes=(), strict=False,
        excluded_functions=()):
    return run_spacing(
        paths, checks=(partial(prepare_check, strict=strict,
                               excluded_functions=excluded_functions),),
        excludes=excludes, write=write, report=report, diff=diff,
    )
