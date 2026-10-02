"""flint Statement class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
class Statement(list):
    def __init__(self, *args, **kwds):
        # XXX: 'tag' is a dumb name, "type" or "class" is better but namespace
        #   issues ofc...
        self.tag = kwds.pop('tag') if 'tag' in kwds else None
        self.line_number = None
        self.label = None
        self.code_index = 0

        super(Statement, self).__init__(*args, **kwds)
        if (
            len(self) >= 3
            and self[1] == ':'
            and getattr(self[0], 'is_name', False)
        ):
            self.label = self[0]
            self.code_index = 2
        else:
            self.label = None
            self.code_index = 0

    # XXX: Dumb name... override __str__?
    def gen_stmt(self):
        """Recreate the statement by gathering tokens and null tokens."""
        header = ''.join(self[0].head)
        footer = ''.join(self[-1].tail)
        tag = getattr(self, 'tag', None) or '~'

        stmt = '{}│ '.format(tag)
        stmt += header.rsplit('\n')[-1] if header else ''
        stmt += ''.join([str(tok) + ''.join(tok.tail) for tok in self[:-1]])
        stmt += str(self[-1])
        stmt += ''.join(footer.rsplit('\n', 1)[:-1]) if footer else ''

        return stmt.replace('\n', '\n │ ')

    def reformat(self):
        """This is just a placeholder at the moment, but the idea is that this
        will 'reformat' the text according to a style guide."""
        return ' '.join([str(tok) for tok in self])

    def is_do_statement(self):
        """Return true if this statement begins a do construct or do loop."""
        index = self.code_index
        return len(self) > index and self[index] == 'do'

    def is_call_statement(self):
        """Return true if this statement is a call statement."""
        index = self.code_index
        return len(self) > index and self[index] == 'call'

    def is_do_control_assignment(self, index):
        """Return true if token index is the equals in a do-loop control."""
        first = self.code_index
        variable = first + 1
        if len(self) > variable and getattr(self[variable], 'is_number', False):
            variable += 1
        return (
            self.is_do_statement()
            and index == variable + 1
            and self[index] == '='
            and getattr(self[variable], 'is_name', False)
        )

    def is_named_argument_assignment(self, index):
        """Return true if token index is an equals for a named argument."""
        if index == 0 or self[index] != '=':
            return False
        if not getattr(self[index - 1], 'is_name', False):
            return False

        depth = 0
        for j in range(index - 2, -1, -1):
            tok = self[j]
            if tok == ')':
                depth += 1
            elif tok == '(':
                if depth == 0:
                    return True
                depth -= 1
        return False

    def assignment_operator_indices(self):
        """Return indexes of equals tokens used as assignment-like operators."""
        return [
            idx for idx, tok in enumerate(self)
            if tok == '='
            and not self.is_do_control_assignment(idx)
            and not self.is_named_argument_assignment(idx)
        ]

    def assignment_operator_index(self):
        """Return the first assignment-like equals token index, if any."""
        try:
            return self.assignment_operator_indices()[0]
        except IndexError:
            return None

    def named_argument_indices(self):
        """Return indexes of equals tokens used for named arguments."""
        return [
            idx for idx, tok in enumerate(self)
            if tok == '=' and self.is_named_argument_assignment(idx)
        ]

    def do_control_assignment_indices(self):
        """Return indexes of equals tokens used in do-loop controls."""
        return [
            idx for idx, tok in enumerate(self)
            if tok == '=' and self.is_do_control_assignment(idx)
        ]
