"""Documentation-presence checks, independent of markup and site rendering.

Check modules, procedures, types, named interfaces, module variables and type
components, including private entities. Procedure-local variables are excluded.
Argument checks are opt-in; this is not a documentation-quality assessment.
"""
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from flint.document import docstrip
from flint.documentation import documentation_pass, declaration_comments, _comments, _groups
from flint.docgen.model import _scope_metadata
from flint.token import semantic_tokens
from flint.variable import Variable

@dataclass(frozen=True)
class DocumentationIssue:
    path: str
    line: int
    kind: str
    name: str

    def __str__(self):
        return f'{self.path}:{self.line}: missing-documentation: {self.kind} {self.name}'


def _variable_documented(variable):
    origin = getattr(variable.stmt, 'origin_statement', None)
    if origin is not None:
        index = next(i for i, token in enumerate(variable.stmt) if token is variable.name)
        variable = Variable.from_token(origin[index], variable.type, stmt=origin)
    if variable.doc.group_description.strip():
        return True
    blocks = variable.documentation
    if blocks is None:
        # Older declaration forms without a structured association still have
        # the parser's legacy docstring. Standard declarations use precise blocks
        # so an unrelated comment on a continuation cannot document every name.
        return bool(variable.doc.docstring.strip())
    return any(docstrip([text for text in block.comments
                         if not text.startswith(('!>@{', '!>@}'))]).strip()
               for block in blocks)


def _leading_scope_documented(statement, *, first=False):
    """A preceding declaration's backward comment does not describe this scope."""
    statement = getattr(statement, 'origin_statement', statement)
    head = statement[0].head
    start_line = statement.line_number - sum(text.count('\n') for text in head)
    for group in reversed(list(_groups(_comments(head, start_line)))):
        marked = [(line, text) for line, text in group if text.startswith(('!>', '!<', '!!'))]
        if not marked:
            continue
        line, marker = marked[0]
        if marker.startswith('!<'):
            continue
        if marker.startswith('!!') and not first and line == start_line:
            continue  # Inline on the previous statement, not a leading block.
        return bool(docstrip([text for _, text in marked
                              if not text.startswith(('!>@{', '!>@}'))]).strip())
    return False


def _unit_documented(unit, *, first_statement=None):
    """Check source-owned scope descriptions rather than overlapping legacy gaps."""
    header = unit.doc.statement
    if not header:
        return False
    if _leading_scope_documented(header, first=header is first_statement):
        return True
    original = getattr(header, 'origin_statement', header)
    entity = SimpleNamespace(name_index=0, span=(0, len(original)),
                             location=SimpleNamespace(line=original.line_number))
    blocks = declaration_comments(original, (entity,))
    if any(block.placement != 'leading' and docstrip(block.comments).strip() for block in blocks):
        return True
    # Scientific module descriptions may appear before END MODULE. Only forward
    # or standalone !! documentation there belongs to the enclosing scope.
    return (len(unit.statements) > 1
            and _leading_scope_documented(unit.statements[-1]))


@documentation_pass()
def check_documentation(source, *, arguments=False, strict=False, defer_includes=()):
    """Return missing-documentation diagnostics for one parsed Source.

    Explicit !>, !< and !! documentation and !>@{ declaration groups count.
    Ordinary comments do not. USE-associated names and procedure-local variables
    are not checked. Named interfaces and their explicit procedure bodies are
    visited, including abstract interfaces. Diagnostics describe parser coverage,
    not complete Doxygen compatibility. Macro-hidden tokens use the declaration
    line when a physical name-token location is unavailable. ``strict`` also
    requires module/submodule, program, function, subroutine, abstract-type,
    type-bound procedure, and finalization-procedure descriptions. Generic
    bindings are checked like named interfaces, including in relaxed mode.
    Their contents are always visited, regardless of visibility. Declarations
    originating in ``defer_includes`` are deferred only in relaxed mode.
    """
    issues = []
    seen = set()
    deferred = {Path(path).resolve() for path in defer_includes}

    def issue(statement, kind, name, line=None):
        if not strict and kind in ('module', 'submodule', 'program', 'subroutine', 'function',
                                   'procedure', 'binding', 'final-binding'):
            return
        origin = getattr(statement, 'origin_statement', None)
        if origin is not None:
            path = getattr(statement, 'source_path', None) or source.path
            if not strict and Path(path).resolve() in deferred:
                return
            line = origin.line_number
        else:
            path = source.path
        issues.append(DocumentationIssue(str(path),
                                        line or statement.line_number or 1, kind, name))

    def visit(unit, scope=()):
        if id(unit) in seen:
            return
        seen.add(id(unit))
        name = getattr(unit.name, 'original', str(unit.name)) if unit.name is not None else ''
        path = (*scope, name) if name else scope
        qualified = '::'.join(path)
        statement = unit.doc.statement
        kind = str(unit.utype)
        _, default_public, access_items = _scope_metadata(unit)
        access = dict(access_items)
        header = list(semantic_tokens(statement)) if statement else []
        attributes = header[:header.index('::')] if '::' in header else header
        abstract_type = kind == 'type' and 'abstract' in attributes
        if (name and statement and (strict or not abstract_type)
                and not _unit_documented(unit, first_statement=source.statements[0])):
            issue(statement, kind, qualified)
        arg_names = set()
        if arguments and kind in ('function', 'subroutine') and statement:
            tokens = list(semantic_tokens(statement))
            start = unit.header_index(tokens) + 2
            if tokens[start:start + 1] == ['(']:
                end = tokens.index(')', start)
                arg_names = {str(t).lower() for t in tokens[start + 1:end] if str(t).isidentifier()}
        declared = set()
        for variable in unit.variables:
            varname = getattr(variable.name, 'original', str(variable.name))
            declared.add(varname.lower())
            if kind in ('module', 'submodule', 'type'):
                category = 'component' if kind == 'type' else 'variable'
                if kind != 'type' and variable.is_procedure and not variable.is_pointer:
                    category = 'procedure'
            elif varname.lower() in arg_names:
                category = 'argument'
            else:
                continue
            if (not strict and kind in ('module', 'submodule')
                    and not access.get(variable.name[:].lower(), default_public)
                    and any(attribute[0] == 'parameter' for attribute in variable.attributes)):
                continue
            if not _variable_documented(variable):
                location = variable.location
                issue(variable.stmt, category, '::'.join((*path, varname)),
                      location.line if location else None)
        for arg in sorted(arg_names - declared):
            issue(statement, 'argument', '::'.join((*path, arg)))
        for child in (*unit.derived_types, *unit.subprograms):
            visit(child, path)
        for binding in unit.bindings:
            if not binding.description.strip():
                location = binding.location
                issue(binding.statement, binding.kind, '::'.join((*path, binding.name)),
                      location.line if location else None)
        for interface in unit.interfaces:
            header = interface.statements[0]
            if interface.name is not None:
                iname = str(interface.name)
                if not docstrip(header[0].head).strip() and not docstrip(header[-1].tail).strip():
                    issue(header, 'interface', '::'.join((*path, iname)))
            for child in interface.subprograms:
                visit(child, path)

    for unit in source.units:
        visit(unit)
    return sorted(issues, key=lambda item: (item.line, item.name, item.kind))
