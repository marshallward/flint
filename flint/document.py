"""flint docstring parser and documentation interface.

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
# TODO: Make this a class with a configurable token set

doc_tokens = ('!<', '!>', '!!')
grp_tokens = ('!>@{', '!>@}')


def is_docstring(tokens):
    return any(tok.startswith(dtok) for tok in tokens for dtok in doc_tokens)


def is_docgroup(tokens):
    return any(tok.startswith(dtok) for tok in tokens for dtok in grp_tokens)


def docstrip(tokens, oneline=False):
    """Remove comment markers, retaining reST indentation and paragraph breaks."""
    docstr_tokens = []
    gap = ''
    for tok in tokens:
        if any(tok.startswith(d) for d in doc_tokens):
            if docstr_tokens and gap.count('\n') > 1 and docstr_tokens[-1]:
                docstr_tokens.append('')
            docstr_tokens.append(tok[2:].removeprefix(' '))
            gap = ''
        else:
            gap += tok

    # Flatten only when explicitly requested; markup needs the block boundaries.
    return ' '.join(docstr_tokens) if oneline else '\n'.join(docstr_tokens)


def groupstrip(tokens):
    """Read only the most recent declaration group, not preceding comments."""
    start = None
    for index, token in enumerate(tokens):
        if token.startswith(grp_tokens):
            start = index
    if start is None or tokens[start].startswith('!>@}'):
        return ''
    return docstrip(tokens[start:]).removeprefix('@{').removeprefix(' ')


class Document(object):
    """The document object of the program element."""

    def __init__(self):
        self.statement = ''     # Some relevant source code

        self.header = ''        # Docstring preceding a statement or unit
        self.docstring = ''     # Statement or unit docstring
        self.footer = ''        # Docstring following a program unit
