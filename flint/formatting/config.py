"""Project formatting configuration shared by Python callers and the CLI."""
from functools import partial
import os
from pathlib import Path

from flint.formatting.rules import ALL_RULES, RULES


SCHEMA = {
    'assignment-spacing': {'strict': bool, 'do-controls': bool},
    'operator-spacing': {'strict': bool},
    'callable-comma-spacing': {'strict': bool, 'excluded-functions': list},
    'indentation': {
        'strict': bool, 'width': int, 'module-contents': bool,
        'continuation-width': int, 'declaration-continuation-width': int,
    },
}
ARGUMENTS = {
    'width': 'indent', 'module-contents': 'module_contents',
    'continuation-width': 'continuation_width',
    'declaration-continuation-width': 'declaration_continuation_width',
    'do-controls': 'do_controls', 'excluded-functions': 'excluded_functions',
}


def validate_config(config):
    """Validate a parsed formatting table before parsing any source files."""
    if not isinstance(config, dict):
        raise ValueError('format must be a table')
    for key, value in config.items():
        if key in ('rules', 'exclude'):
            _validate_value(key, value, list)
            if key == 'rules':
                _validate_names(value)
        elif key in SCHEMA:
            if not isinstance(value, dict):
                raise ValueError(f'format.{key} must be a table')
            for option, setting in value.items():
                if option not in SCHEMA[key]:
                    raise ValueError(f'Unknown option: format.{key}.{option}')
                _validate_value(f'{key}.{option}', setting, SCHEMA[key][option])
        else:
            raise ValueError(f'Unknown formatting option or rule: {key}')
    return config


def _validate_value(name, value, kind):
    if type(value) is not kind:
        raise ValueError(f'{name} must be {kind.__name__}')
    if kind is int and value < 1:
        raise ValueError(f'{name} must be a positive integer')
    if kind is list and any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f'{name} must contain nonempty strings')


def _validate_names(names):
    unknown = set(names) - ALL_RULES.keys()
    if unknown:
        raise ValueError('Unknown formatting rule(s): ' + ', '.join(sorted(unknown)))


def load_config(path=None, *, start=None):
    """Load the nearest flint.toml above start/CWD, or an explicit file.

    Return its validated ``format`` table. Exclusions are resolved relative to
    the configuration file. No file found during discovery means empty settings.
    """
    if path is None:
        directory = Path(start or Path.cwd()).resolve()
        path = next((parent / 'flint.toml' for parent in (directory, *directory.parents)
                     if (parent / 'flint.toml').is_file()), None)
        if path is None:
            return {}
    path = Path(path).resolve()
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    try:
        with path.open('rb') as stream:
            document = tomllib.load(stream)
        if set(document) - {'format'}:
            raise ValueError('Unknown top-level configuration table; expected format')
        config = validate_config(document.get('format', {}))
    except (OSError, ValueError) as error:
        raise ValueError(f'{path}: {error}') from error
    if 'exclude' in config:
        # Project accepts both relative and absolute source paths; match either.
        paths = [(path.parent / item).resolve() for item in config['exclude']]
        config['exclude'] = [item for p in paths for item in (str(p), os.path.relpath(p))]
    return config


def configured_rules(config, *, only=None, skip=(), strict=None,
                     do_controls=None, excluded_functions=None, indent=None):
    """Return (spacing checks, diagnostic checks) with explicit overrides.

    None means omitted. Explicit values override each rule's configuration.
    Input mappings are never modified; both outputs reuse a parsed project.
    """
    validate_config(config)
    names = tuple(config.get('rules', ALL_RULES) if only is None else only)
    skip = set(skip)
    _validate_names((*names, *skip))
    overrides = {'strict': strict, 'do-controls': do_controls,
                 'excluded-functions': excluded_functions, 'width': indent}
    for key, value in overrides.items():
        if value is not None:
            _validate_value(key, value, {'strict': bool, 'do-controls': bool,
                                        'excluded-functions': list, 'width': int}[key])
    spacing, diagnostics = {}, {}
    for name in names:
        if name in skip:
            continue
        options = dict(config.get(name, {}))
        options.update({key: value for key, value in overrides.items()
                        if value is not None and key in SCHEMA[name]})
        kwargs = {ARGUMENTS.get(key, key): value for key, value in options.items()}
        target = spacing if name in RULES else diagnostics
        target[name] = partial(ALL_RULES[name], **kwargs)
    return spacing, diagnostics
