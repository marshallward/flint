"""Command line interface to flint."""
import argparse
import sys

import flint
import flint.tools.gendoc

def parse():
    """Parse the command line inputs and execute the subcommand."""

    # 1. Construct the argument parser

    parser = argparse.ArgumentParser()
    parser.add_argument('--version',
            action='version',
            version='flint {0}'.format(flint.__version__)
    )

    subparsers = parser.add_subparsers()

    # Subcommand setup
    # XXX: This is more of a placeholder for now
    #   These will presumably be defined in a separate module
    # Setup gendoc
    gendoc_cmd = subparsers.add_parser('gendoc')
    gendoc_cmd.set_defaults(run_cmd=flint.tools.gendoc.generate_docs)

    arg_srcdirs = {
        'flags': ('srcdir',),
        'parameters': {
            'action': 'store',
            'metavar': 'dir',
            'type': str,
            'nargs': '+',
            'help': 'Source code directory'
        }
    }
    gendoc_cmd.add_argument(*arg_srcdirs['flags'], **arg_srcdirs['parameters'])

    arg_docdir = {
        'flags': ('--output', '-o'),
        'parameters': {
            'action': 'store',
            'dest': 'docdir',
            'default':  None,
            'help': 'Documentation output directory',
        }
    }
    gendoc_cmd.add_argument(*arg_docdir['flags'], **arg_docdir['parameters'])

    # If no argument given, then print the help page
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    # Fetch the command line arguments
    args = parser.parse_args()
    run_cmd = args.run_cmd

    srcdir = args.srcdirs
    docdir = args.docdir

    run_cmd(args.srcdir, args.docdir)
