"""Command line interface to flint.

:copyright: Copyright 2021 Marshall Ward, see AUTHORS for details.
:license: Apache License, Version 2.0, see LICENSE for details.
"""
import argparse
import sys

import flint
import flint.tools.format
import flint.tools.gendoc
import flint.tools.tag
import flint.tools.report


def parse():
    """Parse the command line inputs and execute the subcommand."""

    # Construct the argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--version',
        action='version',
        version='flint {0}'.format(flint.__version__)
    )

    subparsers = parser.add_subparsers()

    # Subcommand setup
    # TODO: argparse has some method for registering args over multiple cmds

    # Arguments
    arg_srcdirs = {
        'flags': ('srcdirs',),
        'parameters': {
            'action': 'store',
            'metavar': 'dir',
            'type': str,
            'nargs': '+',
            'help': 'Source code directory'
        }
    }

    arg_incdirs = {
        'flags': ('--include', '-I'),
        'parameters': {
            'action': 'append',
            'dest': 'includes',
            'metavar': 'incdir',
            'type': str,
            'help': 'Preprocessor #include directories'
        }
    }

    arg_exclude = {
        'flags': ('--exclude',),
        'parameters': {
            'action': 'append',
            'dest': 'excludes',
            'metavar': 'excl',
            'type': str,
            'help': 'Exclude directory from project'
        }
    }

    # gendoc flags
    # NOTE: Should we make this mandatory (i.e. positional)?
    arg_docdir = {
        'flags': ('--output', '-o'),
        'parameters': {
            'action': 'store',
            'dest': 'docdir',
            'default': 'docs',
            'help': 'Documentation output directory',
        }
    }

    # reformat
    format_cmd = subparsers.add_parser('format')
    format_cmd.set_defaults(run_cmd=flint.tools.format.format_statements)
    format_cmd.add_argument('srcdirs', nargs='*', metavar='path', help='Source files or directories')
    format_cmd.add_argument(*arg_incdirs['flags'], **arg_incdirs['parameters'])
    format_cmd.add_argument(*arg_exclude['flags'], **arg_exclude['parameters'])
    format_cmd.add_argument('--only', action='append', help='Comma-separated rule names; repeatable')
    format_cmd.add_argument('--skip', action='append', default=[], help='Rule names to skip; repeatable')
    format_cmd.add_argument('--list-rules', action='store_true', help='List available formatting rules')
    format_cmd.add_argument('--config', metavar='PATH', help='Use this TOML file instead of discovering flint.toml')
    format_cmd.add_argument('--write', action='store_true', help='Apply spacing fixes in place')
    format_cmd.add_argument('--diff', action='store_true', help='Print proposed unified diffs')
    format_cmd.add_argument('--strict', action=argparse.BooleanOptionalAction, default=None,
                            help='Require exact spacing and two extra indent levels for declaration continuations')
    format_cmd.add_argument('--do-controls', action=argparse.BooleanOptionalAction, default=None,
                            help='Also normalize DO-control spacing')
    format_cmd.add_argument('--exclude-function', dest='excluded_functions', action='append', default=None,
                            metavar='NAME', help='Skip comma spacing for this callable; repeatable')

    # gendoc
    gendoc_cmd = subparsers.add_parser('gendoc')
    gendoc_cmd.set_defaults(run_cmd=flint.tools.gendoc.generate_docs)
    gendoc_cmd.add_argument(*arg_srcdirs['flags'], **arg_srcdirs['parameters'])
    gendoc_cmd.add_argument(*arg_docdir['flags'], **arg_docdir['parameters'])
    gendoc_cmd.add_argument(*arg_incdirs['flags'], **arg_incdirs['parameters'])
    gendoc_cmd.add_argument(*arg_exclude['flags'], **arg_exclude['parameters'])

    # tag
    tag_cmd = subparsers.add_parser('tag')
    tag_cmd.set_defaults(run_cmd=flint.tools.tag.tag_statements)
    tag_cmd.add_argument(*arg_srcdirs['flags'], **arg_srcdirs['parameters'])
    tag_cmd.add_argument(*arg_incdirs['flags'], **arg_incdirs['parameters'])
    tag_cmd.add_argument(*arg_exclude['flags'], **arg_exclude['parameters'])

    # report
    report_cmd = subparsers.add_parser('report')
    report_cmd.set_defaults(run_cmd=flint.tools.report.report_issues)
    report_cmd.add_argument(*arg_srcdirs['flags'], **arg_srcdirs['parameters'])
    report_cmd.add_argument(*arg_incdirs['flags'], **arg_incdirs['parameters'])
    report_cmd.add_argument(*arg_exclude['flags'], **arg_exclude['parameters'])

    # If no argument given, then print the help page
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    # Fetch the command line arguments
    args = parser.parse_args()
    run_cmd = args.run_cmd

    run_args = vars(args)
    run_args.pop('run_cmd')
    if run_cmd is flint.tools.format.format_statements:
        try:
            return run_cmd(**run_args)
        except ValueError as error:
            format_cmd.error(str(error))
    return run_cmd(**run_args)
