"""Run composable spacing checks against one parsed project.

Each check is a callable taking a Source and returning a statement edit
collector. This lets a rule prepare scope context once per source. Collectors
inspect the same unchanged tokens; their proposals are merged before rendering.
"""
import difflib
from itertools import chain
from pathlib import Path
from typing import NamedTuple

import flint
from flint.formatting.spacing import format_spacing


class Change(NamedTuple):
    """A changed physical line and its source path."""

    path: Path
    line_number: int
    original: str


class FileChange(NamedTuple):
    """Proposed output for one file, without modifying the parsed source."""

    path: Path
    original: str
    formatted: str
    changes: tuple[Change, ...]


def check_spacing(project, checks):
    """Yield changed files for checks sharing an already parsed project.

    Each ``check(source)`` returns ``collect_edits(statement)``. Identical edits
    coalesce and incompatible proposals raise ValueError through format_spacing.
    The caller must keep the source files unchanged since parsing: the current
    source model does not retain a complete original file snapshot.
    """
    checks = tuple(checks)
    if not checks:
        return
    for source in project.sources:
        path = Path(source.path)
        original = path.read_text(encoding='utf-8', errors='ignore')
        collectors = [check(source) for check in checks]
        formatted, changes = format_spacing(
            source.statements,
            lambda statement: chain.from_iterable(
                collect(statement) for collect in collectors
            ),
            original.splitlines(),
        )
        if formatted != original:
            yield FileChange(path, original, formatted, tuple(
                Change(path, change.line_number, change.original)
                for change in changes
            ))


def report_spacing(results, *, write=False, report=False, diff=False):
    """Report/apply proposed file changes; return the existing CLI exit status."""
    changed = []
    all_changes = []
    for result in results:
        changed.append(result.path)
        all_changes.extend(result.changes)
        if diff:
            print(''.join(difflib.unified_diff(
                result.original.splitlines(True), result.formatted.splitlines(True),
                fromfile=str(result.path), tofile=str(result.path),
            )), end='')
        if write:
            result.path.write_text(result.formatted, encoding='utf-8')
    if report:
        seen = set()
        for change in all_changes:
            key = (change.path, change.line_number)
            if key not in seen:
                seen.add(key)
                print(f'{change.path}:{change.line_number}: {change.original}')
    elif not diff:
        for path in changed:
            print(path)
    return int(bool(changed) and not write)


def run_spacing(paths=(), *, checks, project=None, excludes=(),
                write=False, report=False, diff=False):
    """CLI convenience wrapper, optionally reusing a caller's parsed project.

    Pass either paths (plus excludes) or project. For structured results without
    printing or writing, use check_spacing directly.
    """
    if project is not None:
        if paths or excludes:
            raise ValueError('Pass either project or paths/excludes, not both')
    else:
        project = flint.parse(*(str(path) for path in paths), excludes=excludes)
    return report_spacing(check_spacing(project, checks),
                          write=write, report=report, diff=diff)
