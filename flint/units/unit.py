"""flint Unit class

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import itertools

from flint.calls import get_callable_symbols
from flint.construct import Construct
from flint.document import is_docstring, is_docgroup, docstrip, Document
from flint.interface import Interface
from flint.intrinsics import intrinsic_fns
from flint.statement import Statement
from flint.variable import Variable


class Unit(object):
    unit_types = [
        'program',
        'function',
        'subroutine',
        'module',
        'submodule',
        'block',
        # XXX: Currently `type` shares enough with program units to justify its
        # presence here.  But it should not be here.
        'type',
    ]

    # access-spec
    access_specs = [
        'public',
        'private',
    ]

    # attr-spec
    attribute_specs = access_specs + [
        'allocatable',
        'asynchronous',
        'codimension',
        'contiguous',
        'dimension',
        'external',
        'intent',
        'intrinsic',
        'namelist',     # NOTE: Not an attribute...
        # language-binding-spec
        'optional',
        'pointer',
        'protected',
        'save',
        'target',
        'value',
        'volatile',
        # Deprecated
        'common',
        'equivalence',
    ]

    declaration_types = Variable.intrinsic_types + attribute_specs + [
        'type',
        'enum',         # ENUM, BIND(C)
        'generic',
        'interface',
        'parameter',
        'procedure',
        'data',
        'format',
        'entry',
    ]

    unit_prefix = Variable.intrinsic_types + [
        'elemental',
        'impure',
        'non_recursive',
        'pure',
        'recursive',
    ]

    def __init__(self):
        self.name = None
        self.utype = None

        self.subprograms = []
        self.variables = []
        self.interfaces = []
        self.derived_types = []
        self.namelists = {}

        # Internal set of array namespace, to rule out potential external functions
        self._arrays = set()

        # Call tree properties
        self.used_modules = set()
        self.callees = set()

        self.doc = Document()
        # XXX: Does this need to be here?
        #   This could be tracked inside Document and provided by docstrip()
        self.grp_docstr = None

        # Testing
        self.statements = []

    @staticmethod
    def statement(stmt):
        # TODO: If this ends up being a full type-statement parser, then it
        # needs to be moved into its own class
        idx = next((i for i, w in enumerate(stmt) if w in Unit.unit_types), -1)

        if idx == 0:
            return True
        elif idx > 0:
            words = iter(stmt[:idx])

            word = next(words)
            while True:
                try:
                    if word in Variable.intrinsic_types:
                        word = next(words)
                        if word == '(':
                            # TODO: Parse this more formally
                            while word != ')':
                                word = next(words)
                    elif word not in Unit.unit_prefix:
                        return False

                    word = next(words)
                except StopIteration:
                    break
            return True

        else:
            return False

    def end_statement(self, stmt):
        assert self.utype

        # TODO: Very similar to construct... can I merge somehow?
        if stmt[0].startswith('end'):
            if len(stmt) == 1 and stmt[0] in ('end', 'end' + self.utype):
                return True
            elif len(stmt) >= 2 and (stmt[0], stmt[1]) == ('end', self.utype):
                return True
            else:
                return False

    def parse(self, statements, graph=None):
        """Parse the statements of a program unit.

        Program units are generally very similar, but we leave it undefined
        here due to some slight differences.
        """
        self.parse_header(statements.current_line)
        self.parse_specification(statements)
        self.parse_execution(statements)
        self.parse_subprogram(statements, graph=graph)

        # Remove intrinsic functions from the set of callables
        self.callees = self.callees - set(intrinsic_fns)

        # Assign this unit as caller for each callee
        if graph is not None:
            for proc in self.callees:
                try:
                    graph[proc].add(self.name)
                except KeyError:
                    graph[proc] = set()
                    graph[proc].add(self.name)

        # Finalisation
        stmt = statements.current_line
        stmt.tag = self.utype[0].upper()
        self.statements.append(stmt)

        self.doc.footer = docstrip(
            statements.current_line[0].head,
            oneline=False
        )

    def parse_header(self, stmt):
        """Parse the name of the program unit, if present.

        Each program unit has a different header format, so this method must be
        overridden by each subclass.
        """
        if any(tok in Unit.unit_types for tok in stmt):
            self.utype = next(w for w in stmt if w in Unit.unit_types)
            utype_idx = stmt.index(self.utype)
        else:
            # Assume anonymous main
            self.utype = 'program'
            utype_idx = None
            # TODO: But now we need to re-parse stmt??

        self.doc.header = docstrip(stmt[0].head)
        self.doc.docstring = docstrip(stmt[-1].tail)
        self.doc.statement = stmt

        # TODO: A safer approach may be to formally parse the first non-unit
        # type as a variable type.  A temporary step is to split the
        # declaration into its (potential) output type and the rest.
        # But for now we just grab the name and ignore the rest.
        # TODO: Could also be that `function` is the only one that is not
        # the first character...

        if utype_idx is not None and len(stmt) >= 2:
            # This fails for derived types (which aren't program units and
            # don't belong here but we're stuck with it for now..)
            self.name = stmt[utype_idx + 1]
            # A dumb fix for the moment..
            if self.name == '::':
                self.name = stmt[utype_idx + 2]
        else:
            self.name = None

        stmt.tag = self.utype[0].upper()
        self.statements.append(stmt)

    # Specification

    def parse_specification(self, statements):
        """Parse the specification-part of a program-unit

        [use-stmt]
          [import-stmt]
          [implicit-part]
          [declaration-construct]
        """
        # TODO: `use`, `implicit`, and declarations must appear in that order.
        #       This loop does not check order.
        for stmt in statements:
            if stmt[0] == 'use':
                self.parse_use_stmt(stmt)
            elif stmt[0] == 'import':
                self.parse_import_stmt(stmt)
            elif stmt[0] == 'implicit':
                # TODO: PARAMETER, FORMAT, ENTRY
                self.parse_implicit_stmt(stmt)
            elif stmt[0] in Unit.declaration_types:
                self.parse_declaration_construct(statements, stmt)
            else:
                break

    def parse_use_stmt(self, stmt):
        """Parse a use-stmt from the grammar

        * USE [[, module-nature] ::] module-name [, rename-list]
        * USE [[, module-nature] ::] module-name, ONLY : [only-list]
        """
        idx = 1
        if stmt[idx] == ',':
            idx = idx + 2
        if stmt[idx] == '::':
            idx = idx + 1

        self.used_modules.add(stmt[idx])

        stmt.tag = 'U'
        self.statements.append(stmt)

    def parse_import_stmt(self, stmt):
        stmt.tag = 'i'
        self.statements.append(stmt)

    def parse_implicit_stmt(self, stmt):
        stmt.tag = 'I'
        self.statements.append(stmt)

    def parse_declaration_construct(self, statements, stmt):
        if stmt[0] == 'interface' or (
                len(stmt) > 1 and stmt[:2] == ('abstract', 'interface')
        ):
            block = Interface()
            block.parse(statements)
            self.interfaces.append(block)
            self.statements.extend(block.statements)

        # TODO: Parse out type
        elif (stmt[0] == 'enum' or (stmt[0] == 'type' and stmt[1] != '(')):
            dtype = Unit()
            dtype.parse(statements)

            # TODO: I think this is OK, since these are never defined as
            #   comma-separated lists, but need to check into this
            dtype.name = stmt[-1]
            self.derived_types.append(dtype)
            self.statements.extend(dtype.statements)

        elif stmt[0] in Unit.access_specs:
            stmt.tag = 'd'
            self.statements.append(stmt)

        # Placeholder
        elif stmt[0] == 'data':
            stmt.tag = 'd'
            self.statements.append(stmt)

        # Placeholder
        elif stmt[0] == 'parameter':
            stmt.tag = 'p'
            self.statements.append(stmt)

        else:
            stmt_vars = []
            tokens = iter(stmt)

            tok = next(tokens)

            # Check for any group tokens
            if (is_docstring(tok.head) and is_docgroup(tok.head)):
                # XXX: Use [2:] to strip '{ ', maybe do this in docstrip...?
                self.grp_docstr = docstrip(tok.head)[2:]

            if tok in Variable.intrinsic_types:
                vtype = tok
            elif tok in ('type', 'class'):
                assert next(tokens) == '('
                vtype = next(tokens)
                assert next(tokens) == ')'
            elif tok == 'namelist':
                self.parse_namelist(stmt)
                return
            else:
                # Unhandled
                stmt.tag = 'X'
                self.statements.append(stmt)
                return

            # Character length parsing
            tok = next(tokens)
            if vtype == 'character':
                if tok == '*':
                    tok = next(tokens)

            # Kind (or len) statement
            if tok == '(':
                while tok != ')':
                    tok = next(tokens)
                tok = next(tokens)

            # Attributes

            # Set defaults
            var_intent = None
            is_array = False

            while tok == ',':
                tok = next(tokens)
                attr = tok

                if attr == 'intent':
                    tok = next(tokens)
                    assert tok == '('
                    var_intent = next(tokens)
                    assert var_intent in ('in', 'out', 'inout')
                    tok = next(tokens)

                    # Fortran permits a space between `inout`, so check the
                    # next token.  (NOTE: `out in` is not allowed!)
                    if var_intent == 'in' and tok == 'out':
                        var_intent += tok
                        tok = next(tokens)

                    assert tok == ')'

                # TODO: We mostly skip over this information
                elif attr == 'dimension':
                    is_array = True

                    tok = next(tokens)
                    assert tok == '('
                    par_count = 1
                    while par_count > 0:
                        tok = next(tokens)
                        if tok == '(':
                            par_count += 1
                        elif tok == ')':
                            par_count -= 1

                tok = next(tokens)

            if tok == '::':
                tok = next(tokens)

            var = Variable(tok, vtype)
            var.intent = var_intent
            if is_array:
                self._arrays.add(var.name)

            # First doc attempt: After the variable name
            #   Also, attempt to apply the group docstring if it's been set
            if is_docstring(tok.tail) and not is_docgroup(tok.tail):
                var.doc.docstring = docstrip(tok.tail)
            elif self.grp_docstr:
                var.doc.docstring = self.grp_docstr

            stmt_vars.append(var)

            for tok in tokens:
                is_inline_array = False
                if tok == '(':
                    is_inline_array = True

                    #while tok != ')':
                    #    tok = next(tokens)
                    par_count = 1
                    while par_count > 0:
                        tok = next(tokens)
                        if tok == '(':
                            par_count += 1
                        elif tok == ')':
                            par_count -= 1

                # Skip over potential array assignments
                if tok == '(/':
                    while tok != '/)':
                        tok = next(tokens)

                # Second doc attempt: After the index right parenthesis
                if is_docstring(tok.tail) and not is_docgroup(tok.tail):
                    stmt_vars[-1].doc.docstring = docstrip(tok.tail)
                elif self.grp_docstr:
                    var.doc.docstring = self.grp_docstr

                if tok == ',':
                    # Third doc attempt: After the comma
                    # XXX: Can this one be removed?
                    if is_docstring(tok.tail) and not is_docgroup(tok.tail):
                        stmt_vars[-1].doc.docstring = docstrip(tok.tail)
                    elif self.grp_docstr:
                        var.doc.docstring = self.grp_docstr

                    tok = next(tokens)

                    var = Variable(tok, vtype)
                    var.intent = var_intent
                    if is_docstring(tok.tail):
                        var.doc.docstring = docstrip(tok.tail)

                    stmt_vars.append(var)
                    if is_array or is_inline_array:
                        self._arrays.add(var.name)

            # Retroactively apply docstrings to any comma-separated variables
            stmt_docstring = stmt_vars[-1].doc.docstring
            for svar in stmt_vars[:-1]:
                if stmt_docstring and not svar.doc.docstring:
                    svar.doc.docstring = stmt_docstring

            # Clear the group docstring
            if is_docstring(stmt[-1].tail) and is_docgroup(stmt[-1].tail):
                self.grp_docstr = None

            # Transfer variablest to the AST
            self.variables.extend(stmt_vars)

            stmt.tag = 'D'
            self.statements.append(stmt)

    def parse_namelist(self, stmt):
        assert stmt[0] == 'namelist'
        tokens = iter(stmt[1:])

        tok = next(tokens)
        while tok:
            assert tok == '/'
            # TODO: Validate group name
            nml_group = next(tokens)
            self.namelists[nml_group] = []
            assert next(tokens) == '/'

            tok = next(tokens)
            while tok and tok != '/':
                # TODO: Validate object name
                self.namelists[nml_group].append(tok)
                tok = next(tokens, None)
                assert tok in (',', '/', None)
                if tok == ',':
                    tok = next(tokens)

        stmt.tag = 'N'
        self.statements.append(stmt)

    # Execution

    def parse_execution(self, statements):
        stmt = statements.current_line

        # Gather up any callable symbols
        self.callees.update(get_callable_symbols(stmt, self._arrays))

        # First parse the statement which terminated specification
        # TODO: How to merge with iteration below? Lookahead in parse_spec()?
        if Construct.construct_stmt(stmt):
            cons = Construct(self)
            cons.parse(statements)
            self.statements.extend(cons.statements)
        elif self.end_statement(stmt) or stmt[0] == 'contains':
            return
        else:
            # Unhandled
            stmt.tag = 'E'
            self.statements.append(stmt)

        # Now iterate over the rest of the statements
        for stmt in statements:
            self.callees.update(get_callable_symbols(stmt, self._arrays))

            # Execution constructs
            if Construct.construct_stmt(stmt):
                cons = Construct(self)
                cons.parse(statements)
                self.statements.extend(cons.statements)
            elif self.end_statement(stmt) or stmt[0] == 'contains':
                # TODO: Use return?
                break
            else:
                # Unhandled
                stmt.tag = 'E'
                self.statements.append(stmt)

    def parse_subprogram(self, statements, graph=None):
        stmt = statements.current_line

        # XXX: This is an odd code block.  It mostly checks the following:
        #  1. Am I new subprogram?  Launch a new parser
        #  2. Am I the end statement for the parent Unit?  Exit immediately
        #  3. Otherwise keep going.
        #
        # In practice, I think 1 can never happen, and 3 is always 'contains'.
        # So the logic here seems very flawed.
        # But it hasn't yet caused any problems, so I leave it for now.
        #
        # (Historical note: When interfaces were piggybacking off of Unit,
        # this may have made more sense.  But that is no longer the case.)
        if Unit.statement(stmt):
            subprog = Unit()
            subprog.parse(statements)
            self.subprograms.append(subprog)
            self.statements.extend(subprog.statements)
        elif self.end_statement(stmt):
            return
        else:
            stmt.tag = self.utype[0].upper()
            self.statements.append(stmt)

        for stmt in statements:
            if Unit.statement(stmt):
                subprog = Unit()
                subprog.parse(statements, graph=graph)
                self.subprograms.append(subprog)
                self.statements.extend(subprog.statements)
            elif self.end_statement(stmt):
                # TODO: Use return?
                break
            else:
                stmt.tag = 'X'
                self.statements.append(stmt)
