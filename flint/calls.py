def get_callable_symbols(line, variables):
    # XXX: Checking against intrinsic_fns on every line is very costly.
    #   Perhaps a better solution is to just scoop up symbols on every line
    #   then do this check at the end?
    names = [
        b for a, b, c in zip(line, line[1:], line[2:])
        if a != '%' and c == '(' and b[0].isalpha()
        and b not in variables
    ]

    return names
