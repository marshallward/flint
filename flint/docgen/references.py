"""Scope-aware documentation references, independent of output format.

This resolves ordinary procedures, named procedure-list interfaces, host
association, and USE imports. Other unsupported bindings remain unresolved, rather than being
guessed from a globally matching name.
"""
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalSymbol:
    library: str
    module: str
    name: str


@dataclass(frozen=True)
class Reference:
    label: str
    target: str | None
    reason: str = ''
    external: ExternalSymbol | None = None


class ReferenceIndex:
    def __init__(self, modules, *, external_modules=None):
        # Publication projects supply dependency ownership; Flint has no
        # built-in library names or filename/prefix guesses.
        self.external_modules = {name.lower(): library
                                 for name, library in (external_modules or {}).items()}
        self.units = {}
        self.parents = {}
        self.pages = {}
        self.modules = defaultdict(list)
        self.children = defaultdict(lambda: defaultdict(list))
        self.calls = {}
        self.implementations = {}
        self.callers = defaultdict(list)
        self.diagnostics = []
        self.externals = defaultdict(list)
        for module in modules:
            self._add(module, None, module.name)
            if module.kind == 'module':
                self.modules[module.name.lower()].append(module.qualified_name)
            elif module.name == 'External':
                for procedure in module.procedures:
                    if procedure.kind in ('function', 'subroutine'):
                        self.externals[procedure.name.lower()].append(procedure.qualified_name)
        for key, unit in self.units.items():
            self.implementations[key] = tuple(
                self._implementation(key, name) for name in unit.implementations)
            calls = tuple(self.resolve(key, name) for name in unit.callees)
            self.calls[key] = calls
            for reference in calls:
                if reference.target is not None:
                    self.callers[reference.target].append(Reference(key, key))
                elif reference.external is None:
                    self.diagnostics.append(f'{key}: {reference.label}: {reference.reason}')
        for key, references in self.callers.items():
            self.callers[key] = tuple(sorted(set(references), key=lambda ref: ref.label))

    def _add(self, unit, parent, page):
        key = unit.qualified_name
        if key in self.units:
            raise ValueError(f'Duplicate documentation identity: {key}')
        self.units[key] = unit
        self.parents[key] = parent
        self.pages[key] = page
        if parent is not None:
            self.children[parent][unit.name.lower()].append(key)
        for child in (*unit.derived_types, *unit.procedures, *unit.interfaces):
            self._add(child, key, page)

    def is_public(self, target):
        """Whether an entity is public through its defining scope.

        Internal procedures are implementation details even when their host
        procedure is public. This does not change name resolution.
        """
        parent = self.parents[target]
        if parent is None:
            return True
        scope = self.units[parent]
        if scope.kind in ('function', 'subroutine', 'program'):
            return False
        name = self.units[target].name.lower()
        return (dict(scope.access).get(name, scope.default_public)
                and self.is_public(parent))

    def _implementation(self, interface, name):
        scope = self.parents[interface]
        # A generic may legally share its name with one of its specifics.
        specifics = [key for key in self.children[scope].get(name.lower(), ())
                     if self.units[key].kind in ('function', 'subroutine')]
        if len(specifics) == 1:
            return Reference(name, specifics[0])
        reference = self.resolve(scope, name)
        if reference.target is not None and self.units[reference.target].kind == 'interface':
            return Reference(name, None, 'unresolved implementation')
        return reference

    def _local(self, scope, name, visiting):
        """Return (targets, uncertain, bound) at one lexical scope."""
        unit = self.units[scope]
        if name in unit.opaque_names:
            return set(), True, True
        children = self.children[scope].get(name, ())
        if children:
            interfaces = {key for key in children if self.units[key].kind == 'interface'}
            if interfaces:
                return interfaces, len(interfaces) != 1, True
            targets = {key for key in children
                       if self.units[key].kind in ('function', 'subroutine')}
            return targets, len(targets) != len(children), True
        if unit.name.lower() == name and unit.kind in ('function', 'subroutine'):
            return {scope}, False, True
        if any(v.name.lower() == name for v in unit.variables):
            return set(), True, True
        targets, uncertain, bound = set(), False, False
        for use in unit.uses:
            names = dict(use.names)
            if name in names:
                remote = names[name]
                explicit = True
            elif use.only or name in names.values():
                continue
            else:
                remote = name
                explicit = False
            modules = () if use.intrinsic else self.modules.get(use.module, ())
            if not modules:
                if explicit and not use.intrinsic and use.module in self.external_modules:
                    targets.add(ExternalSymbol(self.external_modules[use.module], use.module, remote))
                    bound = True
                    continue
                uncertain = bound = True
                continue
            found = set()
            unknown = len(modules) != 1
            for module in modules:
                exported, incomplete = self._export(module, remote, visiting)
                found.update(exported)
                unknown |= incomplete
            targets.update(found)
            uncertain |= unknown or (explicit and not found)
            bound |= bool(found) or unknown or explicit
        return targets, uncertain, bound

    def _export(self, module, name, visiting):
        key = (module, name)
        if key in visiting:
            return set(), True
        unit = self.units[module]
        if not dict(unit.access).get(name, unit.default_public):
            return set(), False
        targets, uncertain, _ = self._local(module, name, visiting | {key})
        return targets, uncertain

    def resolve(self, scope, name):
        label = name
        name = name.lower()
        current = scope
        while current is not None:
            targets, uncertain, bound = self._local(current, name, set())
            if bound:
                if len(targets) == 1 and not uncertain:
                    target = next(iter(targets))
                    if isinstance(target, ExternalSymbol):
                        return Reference(label, None, external=target)
                    return Reference(label, target)
                reason = 'ambiguous reference' if len(targets) > 1 else 'unresolved reference'
                return Reference(label, None, reason)
            current = self.parents[current]
        targets = self.externals.get(name, ())
        if len(targets) == 1:
            return Reference(label, targets[0])
        reason = 'ambiguous reference' if targets else 'unresolved reference'
        return Reference(label, None, reason)


def anchor(qualified_name):
    """A stable reST/HTML identifier with reversible Fortran-name escaping."""
    return 'flint-' + qualified_name.lower().replace('_', '-0').replace('::', '-1')


class HtmlDestinations:
    """Map resolved identities to HTML URLs; the resolver knows no filenames."""
    def __init__(self, references):
        self.references = references

    def destination(self, target, current):
        page = self.references.pages[target]
        prefix = '' if page == self.references.pages[current] else page + '.html'
        return prefix + '#' + anchor(target)
