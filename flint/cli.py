"""Command line interface to flint."""
import argparse
import sys

import flint
import flint.tools.gendoc
import flint.tools.parse
import flint.tools.report


def parse():
    """Parse the command line inputs and execute the subcommand."""

    # 1. Construct the argument parser

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--version',
        action='version',
        version='flint {0}'.format(flint.__version__)
    )

    subparsers = parser.add_subparsers()

    # Subcommand setup
    # XXX: This is more of a placeholder for now
    #   These will presumably be defined in a separate module
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

    arg_docdir = {
        'flags': ('--output', '-o'),
        'parameters': {
            'action': 'store',
            'dest': 'docdir',
            'default':  None,
            'help': 'Documentation output directory',
        }
    }

    # gendoc
    gendoc_cmd = subparsers.add_parser('gendoc')
    gendoc_cmd.set_defaults(run_cmd=flint.tools.gendoc.generate_docs)
    gendoc_cmd.add_argument(*arg_srcdirs['flags'], **arg_srcdirs['parameters'])
    gendoc_cmd.add_argument(*arg_docdir['flags'], **arg_docdir['parameters'])

    # parse
    report_cmd = subparsers.add_parser('parse')
    report_cmd.set_defaults(run_cmd=flint.tools.parse.parse_lines)
    report_cmd.add_argument(*arg_srcdirs['flags'], **arg_srcdirs['parameters'])

    # report
    report_cmd = subparsers.add_parser('report')
    report_cmd.set_defaults(run_cmd=flint.tools.report.report_whitespace)
    report_cmd.add_argument(*arg_srcdirs['flags'], **arg_srcdirs['parameters'])

    # If no argument given, then print the help page
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    # Fetch the command line arguments
    args = parser.parse_args()
    run_cmd = args.run_cmd

    # TODO: This is a very rough method for generating a tuple of command
    #   arguments and will probably be revised.
    run_args = vars(args)
    run_args.pop('run_cmd')
    run_cmd(*run_args.values())
