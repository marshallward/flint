"""Format-independent snapshots for generated API references.

These records contain ordinary Python values, not parser objects. Rebuild a
snapshot after editing source. Extraction currently preserves gendoc's legacy
documentation interpretation and coverage; it is not a public-API filter.
"""
from dataclasses import dataclass

from flint.document import docstrip


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


def _text(value):
    # Token slices preserve semantic names even for undisplayed macro tokens,
    # and produce plain strings rather than retaining mutable Token objects.
    return value[:] if value is not None else ''


def build_unit_documentation(unit, *, scope=(), graph=None):
    """Extract one unit and its children without rendering or changing source.

    Qualified names identify documentation entries. Call relationships remain
    unqualified evidence from the parser's existing graph, not resolved links.
    """
    name = _text(unit.name) or 'External'
    path = (*scope, name)
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
    )


def iter_module_documentation(project):
    """Yield one module snapshot at a time, including the external-unit group."""
    for module in project.modules:
        yield build_unit_documentation(module, graph=project.graph)
