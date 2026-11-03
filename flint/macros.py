"""Token substitution for the object and function macros used in Fortran headers.

Expansion is separate from source rendering: the lexer retains each original
invocation while these routines return its semantic replacement.
"""


def arguments(tokens, start):
    """Collect parenthesized actual arguments, returning arguments and end index."""
    depth = 0
    args, current = [], []
    for index in range(start, len(tokens)):
        value = tokens[index]
        if value == '(':
            depth += 1
        elif value == ')':
            depth -= 1
            if depth == 0:
                args.append(current)
                return args, index + 1
        if depth == 1 and value == ',':
            args.append(current)
            current = []
        elif index != start:
            current.append(value)
    raise ValueError('Unterminated function-like macro invocation')


def expand_at(tokens, index, objects, functions, disabled=frozenset()):
    """Return (end, replacement) for a macro at index, or None."""
    name = tokens[index]
    if name in disabled:
        return None
    if name in functions:
        if tokens[index + 1:index + 2] != ['(']:
            return None
        params, body = functions[name]
        if any(not param.isidentifier() for param in params):
            raise ValueError(f'Macro {name}: only named, non-variadic parameters are supported')
        actuals, end = arguments(tokens, index + 1)
        if not params and actuals == [[]]:
            actuals = []
        if len(actuals) != len(params):
            raise ValueError(f'Macro {name} expects {len(params)} arguments, got {len(actuals)}')
        values = {param: expand(actual, objects, functions, disabled)
                  for param, actual in zip(params, actuals)}
        replacement = [value for token in body for value in values.get(token, [token])]
    elif name in objects:
        body = objects[name][1:]
        replacement, end = body, index + 1
    else:
        return None
    if any(token in ('#', '##') for token in body):
        raise ValueError(f'Macro {name}: stringification and token pasting are not supported')
    blocked = disabled | {name}
    expanded = expand(replacement, objects, functions, blocked)
    # An object alias (or a function's result) can supply the function macro
    # name while its parentheses come from the remaining source tokens.
    if expanded and expanded[-1] in functions and tokens[end:end + 1] == ['(']:
        invocation = expand_at([expanded[-1], *tokens[end:]], 0, objects, functions, blocked)
        if invocation is not None:
            consumed, values = invocation
            expanded = [*expanded[:-1], *values]
            end += consumed - 1
    return end, expanded


def expand(tokens, objects, functions, disabled=frozenset()):
    result = []
    index = 0
    while index < len(tokens):
        replacement = expand_at(tokens, index, objects, functions, disabled)
        if replacement is None:
            result.append(tokens[index])
            index += 1
        else:
            index, values = replacement
            result.extend(values)
    return result
