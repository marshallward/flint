"""flint Statement class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""


DECLARATION_STARTERS = {
    'character', 'class', 'complex', 'double', 'integer', 'logical',
    'procedure', 'real', 'type',
}


class Statement(list):
    def __init__(self, *args, **kwds):
        # XXX: 'tag' is a dumb name, "type" or "class" is better but namespace
        #   issues ofc...
        self.tag = kwds.pop('tag') if 'tag' in kwds else None
        self.line_number = None
        self.source_path = None
        self.source_line_number = None
        self.source_visible = True
        self.expansion_path = None
        self.expansion_line_number = None
        self.label = None
        self._code_index = 0
        self.kind = 'other'

        super(Statement, self).__init__(*args, **kwds)
        if (
            len(self) >= 3
            and self[1] == ':'
            and getattr(self[0], 'is_name', False)
        ):
            self.label = str(self[0])
            self._code_index = 2
        else:
            self.label = None
            self._code_index = 0

        self.kind = self._classify_kind()
        self._classify_token_roles()
        if (
            self.kind == 'other'
            and self.assignment_operator_index() is not None
        ):
            self.kind = 'assignment'

    @property
    def tokens(self):
        return self

    @property
    def code_index(self):
        return self._code_index

    @property
    def code_tokens(self):
        return self[self._code_index:]

    def source_text(self):
        """Return this statement with its attached source text."""
        if not self:
            return ''
        output = [''.join(self[0].head)]
        for token in self:
            output.append(str(token))
            output.append(''.join(token.tail))
        return ''.join(output)

    def source_line(self):
        """Return this statement text from its source line."""
        if not self:
            return ''
        head = ''.join(self[0].head)
        prefix = head.rsplit('\n', 1)[-1] if head else ''
        return (prefix + self.source_text()[len(head):]).rstrip('\n')

    def compact_text(self):
        """Return this statement with whitespace collapsed."""
        return ' '.join(self.source_line().split())

    def _classify_kind(self):
        if len(self) <= self._code_index:
            return 'empty'

        first = self[self._code_index]
        if first == 'call':
            return 'call'
        if first == 'do':
            return 'do'
        if str(first).lower() in DECLARATION_STARTERS:
            return 'declaration'
        return 'other'

    def _classify_token_roles(self):
        for tok in self:
            tok.syntax_role = None

        for idx, tok in enumerate(self):
            if tok != '=':
                continue
            if self.is_do_control_assignment(idx):
                tok.syntax_role = 'do_control'
            elif self.is_named_argument_assignment(idx):
                tok.syntax_role = 'name_value'
            else:
                tok.syntax_role = 'assignment'

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
        return self.kind == 'do'

    def is_call_statement(self):
        """Return true if this statement is a call statement."""
        return self.kind == 'call'

    def is_do_control_assignment(self, index):
        """Return true if token index is the equals in a do-loop control."""
        first = self.code_index
        variable = first + 1
        if (
            len(self) > variable
            and getattr(self[variable], 'is_number', False)
        ):
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
        """Return indexes of assignment-like equals tokens."""
        return [
            idx for idx, tok in enumerate(self)
            if tok == '=' and tok.syntax_role == 'assignment'
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
            if tok == '=' and tok.syntax_role == 'name_value'
        ]

    def do_control_assignment_indices(self):
        """Return indexes of equals tokens used in do-loop controls."""
        return [
            idx for idx, tok in enumerate(self)
            if tok == '=' and tok.syntax_role == 'do_control'
        ]
