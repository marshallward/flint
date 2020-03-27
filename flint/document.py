# TODO: Make this a class with a configurable token set

doc_tokens = ('!<', '!>', '!!')


def is_docstring(s):
    return any(s.startswith(tok) for tok in doc_tokens)


class Document(object):
    """The document object of the program element."""

    def __init__(self):
        self.header = ''        # The header in source code
        self.docstring = ''     # The principal docstring
        self.footer = ''        # Additional content outside of the docstring
