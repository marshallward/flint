import sys

# This probably ought to be somewhere else, but leaving it here for now.
def gen_stmt(line, depth=0):
    """Recreate the statement by gathering tokens and null tokens."""
    header = ''.join(line[0].head)
    footer = ''.join(line[-1].tail)

    s = header.rsplit('\n')[-1] if header else ''
    s += ''.join([tok + ''.join(tok.tail) for tok in line[:-1]])
    s += line[-1]
    s += ''.join(footer.rsplit('\n', 1)[:-1]) if footer else ''


    return  s.replace('\n', '\n │  ')
