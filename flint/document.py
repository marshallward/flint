# TODO: Make this a class with a configurable token set

doc_tokens = ('!<', '!>', '!!')


def is_docstring(s):
    return any(s.startswith(tok) for tok in doc_tokens)


def docstrip(s):
    """Stip a docstring of its marker tokens."""
    # TODO: There are still unanswered questions here with respect to when
    #   whitespace should be preserved.  We should look to Python docstring
    #   support for guidance.
    doc = s
    for tok in doc_tokens:
        doc = doc.replace(tok + ' ', '')
        doc = doc.replace(tok + '\n', '\n')
    return doc


class Document(object):
    """The document object of the program element."""

    def __init__(self):
        self.statement = ''     # Some relevant source code

        self.header = ''        # Docstring preceding a statement or unit
        self.docstring = ''     # Statement or unit docstring
        self.footer = ''        # Docstring following a program unit
