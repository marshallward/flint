# This probably ought to be somewhere else, but leaving it here for now.
def gen_stmt(line, depth=0, reformat=False):
    """Recreate the statement by gathering tokens and null tokens."""
    if reformat:
        s = ' ' * depth + ' '.join([tok for tok in line])
    else:
        # Pad newlines by two spaces to match tagged lines
        # XXX: This works, but alters the tail of the token.
        #   We only want to do this inside the function.
        for tok in line:
            for i, ntok in enumerate(tok.tail):
                if ntok == '\n':
                    tok.tail.insert(i+1, ' : ')

        s = ''.join([tok + ''.join(tok.tail) for tok in line])
        if line:
            s = ''.join(line[0].head) + s

    return s
