"""Format-independent snapshots for generated API references.

These records contain ordinary Python values, not parser objects. Rebuild a
snapshot after editing source. Extraction currently preserves gendoc's legacy
documentation interpretation and coverage; it is not a public-API filter.
"""
from dataclasses import dataclass

from flint.document import docstrip


@dataclass(frozen=True)
class UseAssociation:
    module: str
    only: bool = False
    names: tuple[tuple[str, str], ...] = ()
    intrinsic: bool = False


@dataclass(frozen=True)
class VariableDocumentation:
    name: str
    intent: str | None
    description: str


@dataclass(frozen=True)
class UnitDocumentation:
    name: str
    qualified_name: str
    kind: str
    signature: str
    summary: str
    description: str
    variables: tuple[VariableDocumentation, ...] = ()
    derived_types: tuple['UnitDocumentation', ...] = ()
    procedures: tuple['UnitDocumentation', ...] = ()
    callees: tuple[str, ...] = ()
    callers: tuple[str, ...] = ()
    display_name: str = ''
    uses: tuple[UseAssociation, ...] = ()
    default_public: bool = True
    access: tuple[tuple[str, bool], ...] = ()
    opaque_names: tuple[str, ...] = ()


def _text(value):
    # Token slices preserve semantic names even for undisplayed macro tokens,
    # and produce plain strings rather than retaining mutable Token objects.
    return value[:] if value is not None else ''


def _scope_metadata(unit):
    """Snapshot USE/access declarations without descending into child scopes."""
    ends = {id(child.statements[0]): child.statements[-1]
            for child in (*unit.subprograms, *unit.derived_types, *unit.interfaces)
            if child.statements}
    end = None
    uses, access = [], {}
    default_public = True
    for statement in unit.statements:
        if end is None:
            end = ends.get(id(statement))
        if end is not None:
            if statement is end:
                end = None
            continue
        words = [_text(token).lower() for token in statement]
        if not words:
            continue
        if words[0] == 'contains':
            break
        if words[0] in ('public', 'private'):
            names = [word for word in words[1:] if word not in (',', '::')]
            if not names:
                default_public = words[0] == 'public'
            access.update((name, words[0] == 'public') for name in names)
        elif words[0] == 'use':
            start = words.index('::') + 1 if '::' in words else 1
            module = words[start]
            rest = words[start + 1:]
            only = rest[:3] == [',', 'only', ':']
            rest = rest[3:] if only else rest[1:]
            names = []
            # Operators and assignment interfaces are outside this
            # procedure-name index.
            group = []
            for word in [*rest, ',']:
                if word == ',':
                    if len(group) == 1 and group[0].isidentifier():
                        names.append((group[0], group[0]))
                    elif len(group) == 3 and group[1] == '=>' and group[0].isidentifier():
                        names.append((group[0], group[2]))
                    group = []
                else:
                    group.append(word)
            uses.append(UseAssociation(module, only, tuple(names), 'intrinsic' in words[:start]))
    for variable in unit.variables:
        for attribute in variable.attributes:
            if attribute[0] in ('public', 'private'):
                access[_text(variable.name).lower()] = attribute[0] == 'public'
    return tuple(uses), default_public, tuple(sorted(access.items()))


def build_unit_documentation(unit, *, scope=(), graph=None):
    """Extract one unit and its children without rendering or changing source.

    Qualified names identify documentation entries. Call relationships remain
    unqualified evidence from the parser's existing graph, not resolved links.
    """
    name = _text(unit.name) or 'External'
    path = (*scope, name)
    uses, default_public, access = _scope_metadata(unit)
    return UnitDocumentation(
        name=name,
        qualified_name='::'.join(path),
        kind=_text(unit.utype),
        signature=' '.join(unit.doc.statement),
        summary=(docstrip(unit.doc.statement[0].head, oneline=False)
                 if unit.doc.statement else unit.doc.header),
        description=unit.doc.footer,
        variables=tuple(VariableDocumentation(
            _text(variable.name), _text(variable.intent) or None,
            variable.doc.docstring,
        ) for variable in unit.variables),
        derived_types=tuple(build_unit_documentation(child, scope=path, graph=graph)
                            for child in unit.derived_types),
        procedures=tuple(build_unit_documentation(child, scope=path, graph=graph)
                         for child in unit.subprograms),
        callees=tuple(sorted(str(name) for name in unit.callees)),
        callers=tuple(sorted(str(name) for name in (graph or {}).get(unit.name, ()))),
        display_name=str(unit.name) if unit.name is not None else name,
        uses=uses,
        default_public=default_public,
        access=access,
        opaque_names=tuple(_text(interface.name).lower() for interface in unit.interfaces
                           if getattr(interface, 'name', None)),
    )


def iter_module_documentation(project):
    """Yield one module snapshot at a time, including the external-unit group."""
    for module in project.modules:
        yield build_unit_documentation(module, graph=project.graph)
