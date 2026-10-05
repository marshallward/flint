"""flint Statement class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""

from flint.token import TokenKind


DECLARATION_STARTERS = {
    'character', 'class', 'complex', 'double', 'integer', 'logical',
    'procedure', 'real', 'type',
}

GROUP_STARTERS = {'(', '[', '{', '(/'}
GROUP_ENDERS = {')': '(', ']': '[', '}': '{', '/)': '(/'}
NON_CALLABLE_GROUP_NAMES = {
    'associate', 'do', 'else', 'elseif', 'forall', 'if', 'select', 'where',
    'while',
}
UNARY_SIGN_CONTEXT = {
    '(', '[', '{', '(/', ',', ':', '::', '=', '=>', '+', '-', '*', '/', '//',
    '<', '>', '<=', '>=', '==', '/=', '.and.', '.or.', '.eqv.', '.neqv.',
    '.not.',
}


class Statement(list):
    def __init__(self, *args, **kwds):
        # XXX: 'tag' is a dumb name, "type" or "class" is better but namespace
        #   issues ofc...
        self.tag = kwds.pop('tag') if 'tag' in kwds else None
        self.line_number = None
        self.source_visible = True
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
            tok.operator_role = None

        for idx, tok in enumerate(self):
            if tok != '=':
                continue
            if self.is_do_control_assignment(idx):
                tok.syntax_role = 'do_control'
            elif self.is_generic_assignment_spec(idx):
                tok.syntax_role = 'generic_spec'
            elif self.is_named_argument_assignment(idx):
                tok.syntax_role = 'name_value'
            else:
                tok.syntax_role = 'assignment'

        self._classify_operator_roles()

    def _classify_operator_roles(self):
        group_stack = []
        callable_or_subscript_depth = 0
        operator_spec_depth = 0
        try:
            declaration_end = self.index('::')
        except ValueError:
            declaration_end = None

        for idx, tok in enumerate(self):
            if tok in GROUP_ENDERS and group_stack:
                _, in_callable_or_subscript, in_operator_spec = group_stack.pop()
                if in_callable_or_subscript:
                    callable_or_subscript_depth -= 1
                if in_operator_spec:
                    operator_spec_depth -= 1

            if getattr(tok, 'is_operator', False):
                tok.operator_role = self._operator_role(
                    idx,
                    declaration_end,
                    callable_or_subscript_depth,
                    operator_spec_depth,
                )

            if tok in GROUP_STARTERS:
                in_callable_or_subscript = self.opens_callable_or_subscript_group(idx)
                in_operator_spec = (
                    tok == '('
                    and idx > 0
                    and self[idx - 1] == 'operator'
                )
                group_stack.append((
                    str(tok), in_callable_or_subscript, in_operator_spec,
                ))
                if in_callable_or_subscript:
                    callable_or_subscript_depth += 1
                if in_operator_spec:
                    operator_spec_depth += 1

    def _operator_role(
        self,
        index,
        declaration_end,
        callable_or_subscript_depth,
        operator_spec_depth,
    ):
        tok = self[index]
        if tok.kind == TokenKind.ASSIGNMENT:
            return None
        if self.in_declaration_prefix(index, declaration_end):
            return 'declaration_specifier'
        if operator_spec_depth > 0:
            return 'generic_operator_specifier'
        if self.is_print_format_star(index):
            return 'format_specifier'
        if tok == '**':
            return 'exponentiation'
        if tok == '//':
            return 'concatenation'
        if (
            tok.kind == TokenKind.ARITHMETIC_OPERATOR
            and self.in_do_control(index)
        ):
            return 'do_control_operator'
        if (
            tok.kind == TokenKind.ARITHMETIC_OPERATOR
            and callable_or_subscript_depth > 0
        ):
            return 'callable_or_subscript_operator'
        if tok == '.not.' or self.is_unary_sign(index):
            return 'unary_operator'
        if tok.kind in (
            TokenKind.POINTER_ASSIGNMENT,
            TokenKind.ARITHMETIC_OPERATOR,
            TokenKind.RELATIONAL_OPERATOR,
            TokenKind.LOGICAL_OPERATOR,
            TokenKind.DEFINED_OPERATOR,
        ):
            return 'binary_operator'
        return None

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

    def in_declaration_prefix(self, index, declaration_end=None):
        """Return true for tokens before declaration declarators."""
        if self.kind != 'declaration':
            return False
        if declaration_end is None:
            try:
                declaration_end = self.index('::')
            except ValueError:
                return True
        return index < declaration_end

    def opens_callable_or_subscript_group(self, index):
        """Return true if a delimiter opens an argument/subscript group."""
        token = self[index]
        if token in ('[', '{', '(/'):
            return True
        if token != '(' or index == 0:
            return False

        prior = self[index - 1]
        return (
            getattr(prior, 'is_name', False)
            and str(prior).lower() not in NON_CALLABLE_GROUP_NAMES
        )

    def in_do_control(self, index):
        """Return true for tokens in a do-loop control clause."""
        return self.is_do_statement() and index > self.code_index

    def is_print_format_star(self, index):
        """Return true for the star in print *, output statements."""
        return (
            index > self.code_index
            and self[self.code_index] == 'print'
            and self[index] == '*'
            and getattr(self[index - 1], 'is_name', False)
            and self[index - 1] == 'print'
            and len(self) > index + 1
            and self[index + 1] == ','
        )

    def is_unary_sign(self, index):
        """Return true if plus or minus is acting as a unary sign."""
        token = self[index]
        if token not in ('+', '-'):
            return False
        if index <= self.code_index:
            return True
        prior = self[index - 1]
        return prior in UNARY_SIGN_CONTEXT or prior.is_operator

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

    def is_generic_assignment_spec(self, index):
        """Return true for the equals in generic spec assignment(=)."""
        return (
            index >= 2
            and len(self) > index + 1
            and self[index - 2] == 'assignment'
            and self[index - 1] == '('
            and self[index + 1] == ')'
        )

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
