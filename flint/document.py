"""flint docstring parser and documentation interface.

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
# TODO: Make this a class with a configurable token set

doc_tokens = ('!<', '!>', '!!', '!')
#doc_tokens = ('!<', '!>', '!!')
grp_tokens = ('!>@{', '!>@}')


def is_docstring(tokens):
    return any(tok.startswith(dtok) for tok in tokens for dtok in doc_tokens)


def is_docgroup(tokens):
    return any(tok.startswith(dtok) for tok in tokens for dtok in grp_tokens)


def docstrip(tokens, oneline=True):
    docstr_tokens = [
        tok.lstrip('!>< ') for tok in tokens
        if any(tok.startswith(d) for d in doc_tokens)
    ]
    #docstr_tokens = [
    #    tok[len(d)+1:]
    #    for tok in tokens
    #    for d in doc_tokens if tok.startswith(d)
    #]
    #docstr_tokens = [
    #    tok[len(next(d for d in doc_tokens if tok.startswith(d)))+1:]
    #    for tok in tokens if is_docstring(tok)
    #]

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
