# TODO: Make this a class with a configurable token set

doc_tokens = ('!<', '!>', '!!')


def is_docstring(s):
    return any(s.startswith(tok) for tok in doc_tokens)


def docstrip(docstr, oneline=True):
    """Stip a docstring of its marker tokens."""
    # TODO: There are still unanswered questions here with respect to when
    #   whitespace should be preserved.  We should look to Python docstring
    #   support for guidance.
    doc = docstr
    for tok in doc_tokens:
        # First strip the docstring tokens
        doc = doc.replace(tok + ' ', '')
        doc = doc.replace(tok + '\n', '\n')

        # XXX: `oneline` is a dumb variable name
        if oneline:
            # Next convert the lines into a single bytestream:
            doc = ' '.join([s.strip() for s in doc.split('\n')])
    return doc


class Document(object):
    """The document object of the program element."""

    def __init__(self):
        self.statement = ''     # Some relevant source code

        self.header = ''        # Docstring preceding a statement or unit
        self.docstring = ''     # Statement or unit docstring
        self.footer = ''        # Docstring following a program unit
