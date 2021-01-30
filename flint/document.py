# TODO: Make this a class with a configurable token set

doc_tokens = ('!<', '!>', '!!')


def is_docstring(s):
    return any(s.startswith(tok) for tok in doc_tokens)


class Document(object):
    """The document object of the program element."""

    def __init__(self):
        self.statement = '' # Some relevant source code
                            # (Currently not well-defined, should probably point
                            # to a relevant Statement().)

        self.header = ''    # Docstring preceding a definition (usually `source`)
        self.docstring = '' # Principal docstring, following a definition.
        self.footer = ''    # Docstring following an element (usually `end`)
