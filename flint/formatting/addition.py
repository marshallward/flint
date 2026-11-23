"""Diagnose ungrouped real addition chains without changing evaluation order.

Type inference is deliberately conservative: unresolved names/calls and
non-numeric operands do not establish a real addition. Parentheses delimit
chains, including inside arguments, subscripts and declaration initializers.
"""
from pathlib import Path
from typing import NamedTuple

from flint.locations import statement_locations
from flint.token import TokenKind


class Issue(NamedTuple):
    path: Path
    line_number: int
    original: str
    message: str


def _numeric_type(left, right):
    if left not in ('integer', 'real', 'complex') or right not in ('integer', 'real', 'complex'):
        return None
    if 'complex' in (left, right):
        return 'complex'
    return 'real' if 'real' in (left, right) else 'integer'


class _Expressions:
    """Small precedence parser; statement syntax acts as expression separators."""

    def __init__(self, statement, symbols, types):
        self.tokens = statement
        self.symbols = symbols
        self.types = types
        self.index = 0
        self.chains = []

    def peek(self):
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def scan(self, end=None):
        values = []
        while self.peek() is not None and self.peek() != end:
            before = self.index
            value = self.addition()
            if self.index == before:
                self.index += 1
            else:
                values.append(value)
        if end is not None and self.peek() == end:
            self.index += 1
        return values

    def addition(self):
        start = self.index
        value = self.product()
        count = 1
        while self.peek() in ('+', '-'):
            operator = self.peek()
            if operator == '-':
                self.record(start, count, value)
                count = 1
            self.index += 1
            before = self.index
            right = self.product()
            if self.index == before:
                return None
            value = _numeric_type(value, right)
            if operator == '+':
                count += 1
            # A subtraction ends the preceding chain. Its result can be the
            # first operand of a new chain, but '-' does not increase count.
        self.record(start, count, value)
        return value

    def record(self, start, count, value):
        if count >= 3 and value == 'real':
            self.chains.append((start, count))

    def product(self):
        value = self.primary()
        while self.peek() in ('*', '/', '**'):
            self.index += 1
            value = _numeric_type(value, self.primary())
        return value

    def primary(self):
        token = self.peek()
        if token is None:
            return None
        if token in ('+', '-'):
            self.index += 1
            return self.primary()
        if token in ('(', '[', '(/'):
            self.index += 1
            values = self.scan({'(': ')', '[': ']', '(/': '/)'}[token])
            return values[0] if len(values) == 1 else None
        if token.is_number:
            self.index += 1
            # Kind suffixes may themselves contain e/d; only inspect the
            # literal part when distinguishing integer and real constants.
            literal = token.lower().split('_', 1)[0]
            return 'real' if any(c in literal for c in '.ed') else 'integer'
        if token.kind != TokenKind.NAME:
            return None
        self.index += 1
        name = token.lower()
        variable = self.symbols.get(name)
        value = variable.type.lower() if variable is not None else None
        while True:
            if self.peek() == '(':
                self.index += 1
                arguments = self.scan(')')
                if variable is None:
                    if name in ('real', 'dble', 'float'):
                        value = 'real'
                    elif name in ('int', 'nint', 'ceiling', 'floor', 'size', 'lbound', 'ubound', 'len'):
                        value = 'integer'
                    elif name in ('abs', 'min', 'max', 'sum') and arguments:
                        value = arguments[0]
                        for argument in arguments[1:]:
                            value = _numeric_type(value, argument)
            elif self.peek() == '%':
                self.index += 1
                component = self.peek()
                if component is None or not component.is_name:
                    return None
                self.index += 1
                variable = self.types.get(value, {}).get(component.lower())
                value = variable.type.lower() if variable is not None else None
                name = ''
            else:
                return value


def addition_issues(source):
    """Return locations of chains with at least two ungrouped real additions.

    Resolve explicit local/host declarations and local derived-type components.
    Unknown types (including unresolved USE imports and external function
    results) are skipped, rather than inferred from the assignment target.
    """
    issues = []
    seen = set()

    def visit(unit, host_symbols, host_types):
        symbols = {**host_symbols, **{v.name.lower(): v for v in unit.variables}}
        types = dict(host_types)
        for dtype in unit.derived_types:
            types[dtype.name.lower()] = {v.name.lower(): v for v in dtype.variables}
        children = [*unit.subprograms, *unit.derived_types]
        for interface in unit.interfaces:
            children.extend(interface.subprograms)
        nested = {id(stmt) for child in children for stmt in child.statements}
        for statement in unit.statements:
            if id(statement) in nested or id(statement) in seen:
                continue
            seen.add(id(statement))
            if not statement.source_visible or sum(tok == '+' for tok in statement) < 2:
                continue
            parser = _Expressions(statement, symbols, types)
            parser.scan()
            locations = {loc.index: loc.line for loc in statement_locations(statement)}
            for start, count in parser.chains:
                issues.append(Issue(
                    Path(source.path), locations.get(start, statement.line_number),
                    statement.compact_text(),
                    f'{count} terms in an unparenthesized real addition chain',
                ))
        for child in children:
            visit(child, symbols, types)

    for unit in source.units:
        visit(unit, {}, {})
    return sorted(issues, key=lambda issue: issue.line_number)
