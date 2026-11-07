"""Run documentation checks without generating a site or call graphs."""
import os
import contextlib
import io
from pathlib import Path
import sys

import flint
from flint.docgen.check import check_documentation


def source_files(paths, excludes=()):
    """Select Fortran sources, excluding whole lexical or resolved subtrees."""
    excluded = [Path(p).absolute() for p in excludes]
    excluded += [p.resolve() for p in excluded]

    def skip(path):
        return any(path.absolute().is_relative_to(root) or path.resolve().is_relative_to(root)
                   for root in excluded)

    files = {}
    for item in paths:
        path = Path(item)
        if not path.exists():
            raise ValueError(f'Source path does not exist: {path}')
        if path.is_file():
            candidates = [path]
        else:
            candidates = []
            for root, dirs, names in os.walk(path):
                dirs[:] = sorted(d for d in dirs if not skip(Path(root) / d))
                if not skip(Path(root)):
                    candidates.extend(Path(root) / name for name in sorted(names))
        for candidate in candidates:
            if candidate.suffix.lower() == '.f90' and not skip(candidate):
                files.setdefault(candidate.resolve(), candidate)
    if not files:
        raise ValueError('No Fortran source files selected')
    return sorted(files.values())


def check_docs(srcdirs, includes=None, excludes=None, *, arguments=False, strict=False,
               defer_includes=()):
    """Return 0 for complete docs, 1 for omissions, 2 for parse/input failures."""
    paths = source_files(srcdirs, excludes or ())
    include_dirs = list(dict.fromkeys([*(includes or ()), *(str(p.parent) for p in paths)]))
    count = 0
    for path in paths:
        diagnostics = io.StringIO()
        with contextlib.redirect_stderr(diagnostics):
            project = flint.parse(str(path), includes=include_dirs)
        if diagnostics.getvalue():
            raise ValueError(f'Incomplete parse of {path}:\n{diagnostics.getvalue().rstrip()}')
        if len(project.sources) != 1:
            raise ValueError(f'Unable to parse {path}')
        for issue in check_documentation(project.sources[0], arguments=arguments, strict=strict,
                                          defer_includes=defer_includes):
            print(issue)
            count += 1
    print(f'Checked {len(paths)} source files: {count} undocumented API entities.', file=sys.stderr)
    return int(count > 0)
