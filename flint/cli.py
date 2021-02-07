"""Command line interface to flint."""
import argparse
import sys

import flint
import flint.tools.gendoc

def parse():
    """Parse the command line inputs and execute the subcommand."""

    # Construct the argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--version',
            action='version',
            version='flint {0}'.format(flint.__version__)
    )

    subparsers = parser.add_subparsers()

    # Setup gendoc
    # XXX: This is more of a placeholder for now
    gendoc_cmd = subparsers.add_parser('gendoc')
    gendoc_cmd.set_defaults(run_cmd=flint.tools.gendoc.generate_docs)

    # If no argument given, then print the help page
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    # Fetch the command line arguments
    args = vars(parser.parse_args())
    run_cmd = args.pop('run_cmd')

    # XXX: Hard-coded to generate MOM6 code, but this needs to be
    # user-defined!

    mom6_dirs = (
            'mom6/src',
            'mom6/config_src/solo_driver',
            'mom6/config_src/dynamic_symmetric'
    )
    
    mom6_docpath = 'docs'
    run_cmd(mom6_dirs, mom6_docpath)
