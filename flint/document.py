# TODO: Make this a class with a configurable token set

doc_tokens = ('!<', '!>', '!!')


def is_docstring(s):
    return any(s.startswith(tok) for tok in doc_tokens)


def docstrip(tokens, oneline=True):
    # XXX: Replace [3:] with something more robust
    docstr_tokens = [
        tok[3:] for tok in tokens
        if any(tok.startswith(d) for d in doc_tokens)
    ]

    # NOTE: When oneline is true, this converts blank lines (converted to empty
    #   strings) to spaces.  It's not really clear what we want here.  If you
    #   have paragraphs separated by blank lines, then you probably want to
    #   preserve them.
    return ' '.join(docstr_tokens) if oneline else '\n'.join(docstr_tokens)


class Document(object):
    """The document object of the program element."""

    def __init__(self):
        self.statement = ''     # Some relevant source code

        self.header = ''        # Docstring preceding a statement or unit
        self.docstring = ''     # Statement or unit docstring
        self.footer = ''        # Docstring following a program unit
