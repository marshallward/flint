# TODO: Make this a class with a configurable token set

doc_tokens = ('!<', '!>', '!!')

def is_docstring(s):
    return any(s.startswith(tok) for tok in doc_tokens)
