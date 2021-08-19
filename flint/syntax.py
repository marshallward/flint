"""Low-level syntax tests."""


def is_name(name):
    """Return `True` if `name` is a valid Fortran name."""
    return name.isidentifier() and name[0].isalpha()
