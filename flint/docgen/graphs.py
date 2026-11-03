"""Small, deterministic call graphs built from resolved documentation references."""
from dataclasses import dataclass
import json

from flint.docgen.references import anchor


@dataclass(frozen=True)
class CallGraph:
    root: str
    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]


def call_graph(references, root, *, depth=1, direction='callees'):
    """Follow callees or callers up to depth hops from a procedure.

    Edges always point from caller to callee. Private and internal procedures
    are included; unresolved and external targets are omitted. Generic interfaces remain interface
    nodes: their specific procedures are not guessed call targets.
    """
    if depth < 0:
        raise ValueError('Graph depth must be nonnegative')
    if direction not in ('callees', 'callers'):
        raise ValueError(f'Unsupported graph direction: {direction}')
    if root not in references.units:
        raise KeyError(root)
    nodes = {root}
    frontier = {root}
    edges = set()
    for _ in range(depth):
        neighbors = set()
        for key in frontier:
            links = (references.calls[key] if direction == 'callees'
                     else references.callers.get(key, ()))
            for ref in links:
                if ref.target is not None:
                    neighbors.add(ref.target)
                    edges.add((key, ref.target) if direction == 'callees' else (ref.target, key))
        frontier = neighbors - nodes
        nodes.update(frontier)
        if not frontier:
            break
    return CallGraph(root, tuple(sorted(nodes)), tuple(sorted(edges)))


def write_dot(stream, graph, references, *, html_links=False):
    """Write Graphviz DOT; rendering is separate and requires Graphviz."""
    def quote(text):
        return json.dumps(text, ensure_ascii=False)

    stream.write('digraph calls {\n')
    stream.write('  graph [rankdir=LR, bgcolor="transparent"];\n')
    stream.write('  node [shape=box, style="rounded,filled", fontname="Helvetica"];\n')
    stream.write('  edge [color="#64748b"];\n')
    groups = {}
    for key in graph.nodes:
        groups.setdefault(references.pages[key], []).append(key)
    for page, keys in sorted(groups.items()):
        owner = keys[0]
        while references.parents[owner] is not None:
            owner = references.parents[owner]
        module = references.units[owner]
        stream.write(f'  subgraph {quote("cluster_" + page)} {{\n')
        stream.write(f'    label={quote(module.display_name or module.name)};\n')
        stream.write('    color="#cbd5e1"; style="rounded"; fontname="Helvetica";\n')
        for key in keys:
            unit = references.units[key]
            label = unit.display_name or unit.name
            # Retain nested scope names, but let the cluster name the module.
            parent = references.parents[key]
            if parent not in (None, owner):
                label = parent.removeprefix(owner + '::') + '\n' + label
            if unit.kind == 'interface':
                label += ' (interface)'
            if not references.is_public(key):
                label += ' [private/internal]'
            color = '#bfdbfe' if key == graph.root else '#f1f5f9'
            attributes = [f'label={quote(label)}', f'fillcolor={quote(color)}']
            if html_links:
                url = page + '.html#' + anchor(key)
                attributes.extend((f'URL={quote(url)}', 'target="_top"'))
            stream.write(f'    {quote(key)} [{", ".join(attributes)}];\n')
        stream.write('  }\n')
    for caller, callee in graph.edges:
        stream.write(f'  {quote(caller)} -> {quote(callee)};\n')
    stream.write('}\n')
