# This probably ought to be somewhere else, but leaving it here for now.
def gen_stmt(line, depth=0):
    """Recreate the statement by gathering tokens and null tokens."""
    header = ''.join(line[0].head)
    footer = ''.join(line[-1].tail)

    try:
        ihead = 1 + header.rindex('\n')
    except:
        ihead = header.rindex(';')

    try:
        ifoot = footer.rindex('\n')
    except:
        ifoot = footer.rindex(';')

    s = header[ihead:]
    s += ''.join([tok + ''.join(tok.tail) for tok in line[:-1]])
    s += line[-1]
    s += footer[:ifoot]

    return  s.replace('\n', '\n : ')
