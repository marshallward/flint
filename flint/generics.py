"""Names and comma-separated lists used by Fortran generic specifications."""


def canonical_generic_name(name):
    """Normalize case and equivalent intrinsic relational-operator spellings."""
    name = name.lower()
    aliases = {'.eq.': '==', '.ne.': '/=', '.lt.': '<', '.le.': '<=', '.gt.': '>', '.ge.': '>='}
    if name.startswith('operator(') and name.endswith(')'):
        operand = name[9:-1]
        return 'operator(' + aliases.get(operand, operand) + ')'
    return name


def generic_spec(words):
    """Return a semantic generic name, or None for an unsupported token group."""
    words = [word[:].lower() for word in words]
    if len(words) == 1 and words[0].isidentifier():
        return words[0]
    if (len(words) == 4 and words[0] in ('operator', 'assignment', 'read', 'write')
            and words[1] == '(' and words[3] == ')'):
        return canonical_generic_name(''.join(words))
    return None


def comma_groups(words):
    """Split a name/rename list without splitting parenthesized generic specs."""
    group, depth = [], 0
    for word in words:
        if word == ',' and depth == 0:
            yield group
            group = []
            continue
        group.append(word)
        if word == '(':
            depth += 1
        elif word == ')':
            depth -= 1
    if group:
        yield group
