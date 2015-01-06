#!/usr/bin/env python3

'''Random names generator.'''
# Copyright © 2014 Timothy Pederick.
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

__version__ = '0.1'
__author__ = 'Timothy Pederick'
__copyright__ = 'Copyright © 2014 Timothy Pederick'

# Standard library imports.
from argparse import ArgumentParser
from collections import namedtuple
import csv
import os
import random
import sys

MASCULINE, FEMININE, NEUTER = GENDERS = 'MFN'

# Supported nationalities and their name formats.
# This dictionary matches nationalities (specified in English) with sequences
# of one or more tuples. Each tuple contains one or more of the following
# strings:
# * 'personal': A personal or given name.
# * 'matronym': A personal name that is a derivative of the mother's name.
# * 'patronym': A personal name that is a derivative of the father's name.
# * 'additional': An additional given name that is not chosen from the same set
#      as 'personal'.
# * 'family': A family name, inherited from a parent.
# * 'matriname': A family name, specifically that inherited from the mother.
# * 'patriname': A family name, specifically that inherited from the father.
NATIONALITIES = {'Armenian': (('personal', 'family'),),
                 'Chinese': (('family', 'personal'),),
                 'English': (('personal', 'personal', 'family'),
                             ('personal', 'family')),
                 'Georgian': (('personal', 'family'),),
                 'Hungarian': (('family', 'personal'),),
                 'Icelandic': (('personal', 'patronym'),
                               ('personal', 'matronym'),
                               ('personal', 'patronym', 'family'),
                               ('personal', 'matronym', 'family'),),
                 'Japanese': (('family', 'personal'),),
                 'Latvian': (('personal', 'family'),),
                 'Polish': (('personal', 'personal', 'family'),
                            ('personal', 'family')),
                 'Russian': (('personal', 'patronym', 'family'),),
                 'Spanish': (('personal', 'patriname', 'matriname'),
                             ('personal', 'matriname', 'patriname')),
                 'Ukrainian': (('personal', 'patronym', 'family'),),
                 'Vietnamese': (('family', 'additional', 'personal'),)
                 }
NAT_ABBREVS = {'hy': 'Armenian', 'hye': 'Armenian', 'arm': 'Armenian',
               'zh': 'Chinese', 'zho': 'Chinese', 'chi': 'Chinese',
               'en': 'English', 'eng': 'English',
               'ka': 'Georgian', 'kat': 'Georgian', 'geo': 'Georgian',
               'hu': 'Hungarian', 'hun': 'Hungarian',
               'is': 'Icelandic', 'isl': 'Icelandic', 'ice': 'Icelandic',
               'ja': 'Japanese', 'jpn': 'Japanese',
               'lv': 'Latvian', 'lav': 'Latvian',
               'pl': 'Polish', 'pol': 'Polish',
               'ru': 'Russian', 'rus': 'Russian',
               'es': 'Spanish', 'spa': 'Spanish',
               'uk': 'Ukrainian', 'ukr': 'Ukrainian',
               'vi': 'Vietnamese', 'vie': 'Vietnamese'}

# Data sources.
# This dictionary matches identifiers to 2-tuples, containing a filename
# for a CSV file, and a tuple of headings, which are from the following list:
# * 'name': The Romanised name.
# * 'original': The name in the native script (empty if that is Latin).
# * 'counterpart': A corresponding name with the opposite ('M'/'F') gender.
# * 'from_': A name from which another (e.g. a patronym) is derived, as it
#      appears in the 'original' field (i.e. in the native script).
# * 'gender': 'M' for male names, 'F' for female, 'N' if applicable to either.
# * 'nationality': A key from the NATIONALITIES mapping.
DATA = {'personal': ('personal.csv', ('name', 'original', 'gender',
                                      'nationality')),
        'additional': ('additional.csv', ('name', 'original', 'gender',
                                          'nationality')),
        'family': ('family.csv', ('name', 'original', 'gender',
                                  'counterpart', 'nationality')),
        'pmatronymic': ('pmatronymic.csv', ('name', 'original', 'from_',
                                            'gender', 'nationality'))
        }

# Mapping of name parts to data sources.
# This dictionary maps strings from the name-format tuples of NATIONALITIES to
# the relevant data sources, i.e. keys of DATA. Values of 'personal', 'family'
# and 'additional' come from the respective data sources in the DATA mapping,
# while 'matronym' and 'patronym' values come from the source 'pmatronymic',
# and 'matriname' and 'patriname' values come from the same source as 'family'.
NAME_PARTS = {'personal': 'personal',
              'additional': 'additional',
              'family': 'family',
              'matronym': 'pmatronymic',
              'patronym': 'pmatronymic',
              'matriname': 'family',
              'patriname': 'family'
              }

def data(source):
    '''Read in data from the named source.'''
    filename, headings = DATA[source]
    nt = namedtuple('{}_tuple'.format(source), headings)

    return map(nt._make, csv.reader(open(filename, encoding='utf-8',
                                         newline='')))

def validate_formats(verbose=False, out=sys.stdout, err=sys.stderr):
    '''Validate name formats.'''
    try:
        if not verbose:
            # The verbose argument being False overrides the out argument.
            out = open(os.devnull, mode='w')

        for nationality, formats in NATIONALITIES.items():
            print('Checking {} formats...'.format(nationality), file=out)

            matches = {}
            for fmt in formats:
                for part in fmt:
                    try:
                        source = NAME_PARTS[part]
                    except KeyError:
                        print("ERROR: no source known for '{}'".format(part),
                              file=err)
                        continue

                    # Count records that match this nationality...
                    if source in matches:
                        # ...but only the first time.
                        continue

                    matches[source] = 0
                    gender_counts = {'M': 0, 'F': 0, 'N': 0}
                    for fields in data(source):
                        if fields.nationality == nationality:
                            matches[source] += 1
                            gender_counts[fields.gender] += 1

                    if matches[source] == 0:
                        print("ERROR: no {} records in source "
                              "'{}'".format(nationality, source), file=err)
                    else:
                        print("\tFound {0} {1} records in source "
                              "'{2}' ({3[M]} masculine, {3[F]} feminine, "
                              "{3[N]} both)".format(matches[source],
                                                      nationality, source,
                                                      gender_counts), file=out)
    finally:
        # Close a substitute output stream we opened, but not one passed to us.
        if not verbose:
            out.close()

def validate_data(verbose=False, out=sys.stdout, err=sys.stderr):
    '''Validate data sources.'''
    try:
        if not verbose:
            # The verbose argument being False overrides the out argument.
            out = open(os.devnull, mode='w')

        for (source, (filename, headings)) in DATA.items():
            print("Checking data source '{}'...".format(source), file=out)
            try:
                datasource = data(source)
            except OSError as ose:
                print("ERROR opening '{}' "
                      "(Python says '{!s}')".format(filename, ose),
                      file=err)
                continue
            except ValueError as ve:
                print("ERROR (with encoding?) opening '{}' "
                      "(Python says '{!s}')".format(filename, ve),
                      file=err)
                continue
            except Exception as e:
                print("ERROR (dunno what) opening or reading '{}' "
                      "(Python says '{!s}')".format(filename, e),
                      file=err)
                continue

            seen = {}

            print('\t', end='', file=out)
            for n, fields in enumerate(datasource):
                # Only indicate progress every ten records.
                if (n + 1) % 10 == 0:
                    print('{} records... '.format(n + 1), end='', file=out)

                # Is the record unique? By "unique", we mean the name (in its
                # native script) has not been previously seen, for the same
                # gender and same nationality, and (if a patro- or matronymic)
                # with the same source name.
                recordkey = ((fields.name if fields.original == '' else
                              fields.original),
                             fields.gender, fields.nationality,
                             ('' if not hasattr(fields, 'from_') else
                              fields.from_))
                try:
                    existing = seen[recordkey]
                except KeyError:
                    # Yes it is.
                    seen[recordkey] = fields
                else:
                    # No it's not.
                    if fields == existing:
                        # The exact same record already exists.
                        print("WARNING: record identical to '{!r}' "
                              "already exists".format(fields), file=err)
                    else:
                        # The same name is already recorded, but it differs in
                        # some aspect; there might be a legitimate reason
                        # (e.g. different Japanese readings), or it might be an
                        # error (e.g. different Romanisations, one right and
                        # the other wrong).
                        print("WARNING: record matching '{!r}' exists "
                              "with different values "
                              "('{!r}')".format(fields, existing),
                              file=err)

                try:
                    formats = NATIONALITIES[fields.nationality]
                except KeyError:
                    print("WARNING: unknown nationality in record "
                          "'{!r}'".format(fields))
                else:
                    if not any((NAME_PARTS[part] == source)
                               for fmt in formats
                               for part in fmt):
                        print("WARNING: no {} name format uses data from "
                              "'{}'".format(fields.nationality, source))
            print('{} records.'.format(n + 1), end='\n\n', file=out)
    finally:
        # Close a substitute output stream we opened, but not one passed to us.
        if not verbose:
            out.close()

def generate(nationality=None, gender=None, verbose=False):
    '''Generate a random name.'''
    if nationality is None:
        nationality = random.choice(list(NATIONALITIES))
    else:
        try:
            # Is this an abbreviation?
            nationality = NAT_ABBREVS[nationality]
        except KeyError:
            # This is, we hope, a key from NATIONALITIES. If it's not, it will
            # cause another KeyError a few lines down.
            pass
    if gender is None:
        gender = random.choice([MASCULINE, FEMININE])
    if verbose:
        print('Generating {} {} name...'.format(nationality,
                                                {MASCULINE: 'masculine',
                                                 FEMININE: 'feminine'}[gender]))

    fmt = random.choice(NATIONALITIES[nationality])

    latin_parts = []
    original_parts = []

    matching = {}
    for part in fmt:
        source = NAME_PARTS[part]
        if source not in matching:
            matching[source] = []
            for fields in data(source):
                if (fields.nationality == nationality and
                    fields.gender in (gender, NEUTER)):
                    matching[source].append((fields.name, fields.original))

        pos = random.randrange(len(matching[source]))
        # Don't reselect this name for the same person--pop() it from the list.
        latin, original = matching[source].pop(pos)
        latin_parts.append(latin)
        if original != '':
            original_parts.append(original)

    result = ' '.join(latin_parts)
    if len(original_parts) != 0:
        result += ' (' + ' '.join(original_parts) + ')'
    return result

def main():
    '''Handle command-line options and run the name generator.'''
    parser = ArgumentParser(description='Generate one or more random names.')
    parser.add_argument('--version', action='version',
                        version='%(prog)s {}'.format(__version__))
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show detailed information')

    action = parser.add_mutually_exclusive_group()
    action.add_argument('-G', '--generate', action='store_const',
                        const='generate', dest='action',
                        help='generate a name (the default action)')
    action.add_argument('-V', '--validate', action='store_const',
                        const='validate', dest='action',
                        help=('perform validation of data files (instead of '
                              'generating a name)'))

    parser.add_argument('-c', '--count', type=int, default=1,
                        help=('the number of names to generate '
                              '(defaults to 1)'))
    parser.add_argument('-n', '--nat', help=('the nationality of the name(s) '
                                             'to be generated; either a full '
                                             'name, such as "Russian", or an '
                                             'ISO 639 two- or three-letter '
                                             'code, such as "ru"'))
    parser.add_argument('-g', '--gender', choices=[MASCULINE, FEMININE],
                        help='the gender of the name(s) generated')
    args = parser.parse_args()
    if args.action == 'validate':
        validate_data(verbose=args.verbose)
        validate_formats(verbose=args.verbose)
    else:
        for _ in range(args.count):
            print(generate(verbose=args.verbose, nationality=args.nat,
                           gender=args.gender))

if __name__ == '__main__':
    main()
