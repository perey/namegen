#!/usr/bin/env python3

'''Random names generator: command-line utility.'''
# Copyright © 2014, 2015 Timothy Pederick.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__version__ = '0.2'
__author__ = 'Timothy Pederick'
__copyright__ = 'Copyright © 2014, 2015 Timothy Pederick'

# Standard library imports.
from argparse import ArgumentParser
import codecs
import sys

# Local library import.
from namechoose import generate, MASCULINE, FEMININE
from namechoose.data import build_db
from namechoose.checkdata import validate_data

def argparser():
    '''Construct the command-line argument parser.'''
    parser = ArgumentParser(description='Generate one or more random names.')
    parser.add_argument('--version', action='version',
                        version='%(prog)s {}'.format(__version__))
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help=('show detailed information (may be specified '
                              'twice for extra detail)'))

    action = parser.add_mutually_exclusive_group()
    action.add_argument('-G', '--generate', action='store_const',
                        const='generate', dest='action',
                        help='generate a name (the default action)')
    action.add_argument('-V', '--validate', action='store_const',
                        const='validate', dest='action',
                        help=('rebuild and validate the database (instead of '
                              'generating a name)'))
    parser.add_argument('--skip-rebuild', action='store_true',
                        help=("don't rebuild the database when performing "
                              "validation"))

    gen_args = parser.add_argument_group('Generation options')
    gen_args.add_argument('-o', '--outfile', help=('write output to the named '
                                                   'file (instead of standard '
                                                   'output)'))
    gen_args.add_argument('--overwrite', action='store_true',
                          help=('overwrite the output file, instead of '
                                'appending to it (the default behaviour)'))
    gen_args.add_argument('-c', '--count', type=int, default=1,
                          help=('the number of names to generate (defaults '
                                'to 1)'))
    gen_args.add_argument('-n', '--nat', help=('the nationality of the '
                                               'name(s) to be generated; '
                                               'either a full name, such as '
                                               '"Russian", or an ISO 639 two- '
                                               'or three-letter code, such as '
                                               '"ru"'))
    gen_args.add_argument('-g', '--gender', choices=[MASCULINE, FEMININE],
                          help='the gender of the name(s) generated')

    return parser

def main():
    '''Run the command-line utility.'''
    # Parse command line arguments.
    args = argparser().parse_args()

    # What are we doing?
    if args.action == 'validate':
        # We're validating.
        if not args.skip_rebuild:
            # ...after rebuilding the database.
            build_db(verbosity=args.verbose)
        validate_data(verbosity=args.verbose)
    else:
        # We're generating.
        try:
            # Choose the target for output, either stdout or a given file.
            target = sys.stdout
            if args.outfile:
                target = open(args.outfile, encoding='utf-8',
                              mode=('wt' if args.overwrite else 'at'))
            # Tell the user what's happening, if requested.
            if args.verbose:
                print('Generating {} random {}{}'
                      'name{}...'.format(args.count,
                                         {MASCULINE: 'masculine ',
                                          FEMININE: 'feminine '
                                          }.get(args.gender, ''),
                                         ('' if args.nat is None else
                                          nat_lookup(args.nat) + ' '),
                                         's' if args.count > 1 else ''),
                      file=target)
            # Perform the actual generation step(s).
            for _ in range(args.count):
                (name, romanised, gender, nationality,
                 _) = generate(nationality=args.nat, gender=args.gender,
                               verbosity=args.verbose)
                # Yes, I know, Chinese names (for one) shouldn't have a space
                # between their parts. Sorry.
                print(' '.join(name), end='', file=target)
                if len(romanised) > 0:
                    print(' ({})'.format(' '.join(romanised)), end='',
                          file=target)
                if args.verbose:
                    print(' ({}, {})'.format(gender, nationality), end='',
                          file=target)
                print(file=target)
        finally:
            if args.outfile:
                target.close()

if __name__ == '__main__':
    main()
