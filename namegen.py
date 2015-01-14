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
from collections import defaultdict, namedtuple
import csv
import os.path
import random
import sqlite3
import sys

DEFAULT_DBFILE = 'namegen.db'

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
                               ('personal', 'patronym', 'matronym'),
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

def nat_lookup(nat):
    '''Get suitable values for nationality arguments.

    If the argument is already a full nationality name (or if it is
    unrecognised), it is returned unchanged. If it is an abbreviation,
    the corresponding full name is returned.

    '''
    try:
        # Is this an abbreviation?
        nat = NAT_ABBREVS[nat]
    except KeyError:
        # No.
        pass
    return nat

# Data sources.
# This dictionary matches identifiers to 2-tuples, containing a filename
# for a CSV file, and a tuple of headings, which are from the following list:
# * 'name': The name in its native script.
# * 'romanisation': The name in the native script (empty if that is Latin).
# * 'counterpart': A corresponding name with the opposite ('M'/'F') gender.
# * 'from_': A name from which another (e.g. a patronym) is derived, as it
#      appears in the 'name' field (i.e. in the native script).
# * 'gender': 'M' for male names, 'F' for female, 'N' if applicable to either.
# * 'nationality': A key from the NATIONALITIES mapping.
DATA = {'personal': ('name', 'romanisation', 'gender', 'nationality'),
        'additional': ('name', 'romanisation', 'gender', 'nationality'),
        'family': ('name', 'romanisation', 'gender', 'counterpart',
                   'nationality'),
        'pmatronymic': ('name', 'romanisation', 'from_', 'gender',
                        'nationality')
        }
# Shorthand to construct a namedtuple class suitable for each data source.
nt_for = lambda source: namedtuple('{}_tuple'.format(source), DATA[source])

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

def csvdata(source):
    '''Read in data from the named CSV source file.'''
    filename = source + '.csv'
    nt = nt_for(source)

    return map(nt._make, csv.reader(open(filename, encoding='utf-8',
                                         newline='')))

def data(source, dbfilename=DEFAULT_DBFILE, randomise=False, limit=None,
         verbose=False, **kwargs):
    '''Fetch data from the SQLite database.'''
    nt = nt_for(source)

    query, qparms = ['SELECT * FROM "{}"'.format(source)], []
    if len(kwargs) > 0:
        query.append('WHERE')
        where = []
        for kw, val in kwargs.items():
            # Special handling for particular columns...
            if kw == 'gender':
                # Include neuter names when searching by gender.
                where.append('("{0}" = ? OR "{0}" = ?)'.format(kw))
                qparms.append(NEUTER)
            else:
                where.append('"{}" = ?'.format(kw))
            qparms.append(val)
        query.append(' AND '.join(where))
    if randomise:
        query.append('ORDER BY random()')
    if limit is not None:
        query.append('LIMIT {}'.format(abs(int(limit))))

    query_string = ' '.join(query)
    if verbose:
        print("Executing query '{}' with parameters {!r}".format(query_string,
                                                                 qparms))

    if not os.path.isfile(dbfilename):
        build_db(dbfilename=dbfilename, verbose=verbose)
    conn = sqlite3.connect(dbfilename)
    try:
        # The context manager probably isn't necessary. We're only running a
        # SELECT and so shouldn't be changing anything. Hence, the call to
        # commit() that the context manager automatically performs shouldn't
        # be necessary.
        with conn:
            cur = conn.cursor()
            cur.execute(query_string, qparms)
            results = map(nt._make, cur.fetchall())
    finally:
        conn.close()
    return results

def build_db(dbfilename=DEFAULT_DBFILE, verbose=False):
    '''(Re)build the SQLite database from the CSV files.'''
    if verbose:
        print("(Re)building database in file '{}'...".format(dbfilename))
    # Connect to the database file.
    conn = sqlite3.connect(dbfilename)
    try:
        with conn:
            cur = conn.cursor()
            # Remove views on tables.
            cur.execute('DROP VIEW IF EXISTS personal')
            cur.execute('DROP VIEW IF EXISTS additional')
            cur.execute('DROP VIEW IF EXISTS family')
            cur.execute('DROP VIEW IF EXISTS pmatronymic')
            if verbose:
                print('\tViews cleared')
            
            # Create or replace tables.
            cur.execute('DROP TABLE IF EXISTS PersonalNames')
            cur.execute('CREATE TABLE PersonalNames'
                        ' (PersonalNameID INTEGER PRIMARY KEY AUTOINCREMENT'
                        ', Name TEXT NOT NULL'
                        ', Romanisation TEXT'
                        ', Gender TEXT NOT NULL'
                        ', Nationality TEXT NOT NULL'
                        ' )')

            cur.execute('DROP TABLE IF EXISTS AdditionalNames')
            cur.execute('CREATE TABLE AdditionalNames'
                        ' (AdditionalNameID INTEGER PRIMARY KEY AUTOINCREMENT'
                        ', Name TEXT NOT NULL'
                        ', Romanisation TEXT'
                        ', Gender TEXT NOT NULL'
                        ', Nationality TEXT NOT NULL'
                        ' )')

            cur.execute('DROP TABLE IF EXISTS FamilyNames')
            cur.execute('CREATE TABLE FamilyNames'
                        ' (FamilyNameID INTEGER PRIMARY KEY AUTOINCREMENT'
                        ', Name TEXT NOT NULL'
                        ', Romanisation TEXT'
                        ', Gender TEXT NOT NULL'
                        ', CounterpartID INTEGER'
                        '   REFERENCES FamilyNames ON DELETE CASCADE'
                        ', Nationality TEXT NOT NULL'
                        ' )')

            cur.execute('DROP TABLE IF EXISTS PMatronymics')
            cur.execute('CREATE TABLE PMatronymics'
                        ' (PMatronymicID INTEGER PRIMARY KEY AUTOINCREMENT'
                        ', Name TEXT NOT NULL'
                        ', Romanisation TEXT'
                        ', FromPersonalNameID INTEGER NOT NULL'
                        '   REFERENCES PersonalNames ON DELETE CASCADE'
                        ', Gender TEXT NOT NULL'
                        ', Nationality TEXT NOT NULL'
                        ' )')
            if verbose:
                print('\tTables (re)built')

            # Read data files and populate tables.
            cur.executemany('INSERT INTO PersonalNames'
                            ' (Name, Romanisation, Gender, Nationality)'
                            ' VALUES (?, ?, ?, ?)', csvdata('personal'))
            if verbose:
                print('\tPersonal names inserted')

            cur.executemany('INSERT INTO AdditionalNames'
                            ' (Name, Romanisation, Gender, Nationality)'
                            ' VALUES (?, ?, ?, ?)', csvdata('additional'))
            if verbose:
                print('\tAdditional names inserted')

            for record in csvdata('family'):
                cur.execute('INSERT INTO FamilyNames'
                            ' (Name, Romanisation, Gender, Nationality)'
                            ' VALUES (?, ?, ?, ?)', (record.name,
                                                     record.romanisation,
                                                     record.gender,
                                                     record.nationality))
            if verbose:
                print('\tFamily names inserted')
            for record in csvdata('family'):
                if record.counterpart != '':
                    cur.execute('SELECT FamilyNameID'
                                ' FROM FamilyNames'
                                ' WHERE Name = ?', (record.name,))
                    this_id = cur.fetchone()[0]
                    cur.execute('SELECT FamilyNameID'
                                ' FROM FamilyNames'
                                ' WHERE Name = ?', (record.counterpart,))
                    that_id = cur.fetchone()[0]
                    cur.execute('UPDATE FamilyNames'
                                ' SET CounterpartID = ?'
                                ' WHERE FamilyNameID = ?', (that_id, this_id))
            if verbose:
                print('\tFamily name gender counterparts matched up')

            for record in csvdata('pmatronymic'):
                cur.execute('SELECT PersonalNameID'
                            ' FROM PersonalNames'
                            ' WHERE Name = ?', (record.from_,))
                try:
                    from_id = cur.fetchone()[0]
                except TypeError:
                    print("Can't find name '{}'!".format(record.from_))
                cur.execute('INSERT INTO PMatronymics'
                            ' (Name, Romanisation, FromPersonalNameID,'
                            '  Gender, Nationality)'
                            ' VALUES (?, ?, ?, ?, ?)', (record.name,
                                                        record.romanisation,
                                                        from_id,
                                                        record.gender,
                                                        record.nationality))
            if verbose:
                print('\tPatro-/matronymics inserted')

            cur.execute('CREATE VIEW personal AS'
                        ' SELECT pn.Name as name'
                        '  , pn.Romanisation as romanisation'
                        '  , pn.Gender as gender'
                        '  , pn.Nationality as nationality'
                        '  FROM PersonalNames pn')

            cur.execute('CREATE VIEW additional AS'
                        ' SELECT an.Name as name'
                        '  , an.Romanisation as romanisation'
                        '  , an.Gender as gender'
                        '  , an.Nationality as nationality'
                        '  FROM AdditionalNames an')

            cur.execute('CREATE VIEW family AS'
                        ' SELECT fn.Name as name'
                        '  , fn.Romanisation as romanisation'
                        '  , fn.Gender as gender'
                        '  , cn.Name as counterpart'
                        '  , fn.Nationality as nationality'
                        '  FROM FamilyNames fn LEFT JOIN FamilyNames cn'
                        '   ON fn.CounterpartID = cn.FamilyNameID')

            cur.execute('CREATE VIEW pmatronymic AS'
                        ' SELECT nym.Name as name'
                        '  , nym.Romanisation as romanisation'
                        '  , pn.Name as from_'
                        '  , nym.Gender as gender'
                        '  , nym.Nationality as nationality'
                        '  FROM PMatronymics nym JOIN PersonalNames pn'
                        '   ON nym.FromPersonalNameID = pn.PersonalNameID')
    finally:
        conn.close()

def validate_data(dbfilename=DEFAULT_DBFILE, verbose=False):
    '''Validate non-SQL database constraints.'''
    if not os.path.isfile(dbfilename):
        build_db(dbfilename=dbfilename, verbose=verbose)
    conn = sqlite3.connect(dbfilename)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        # 0. Do only known values exist for gender and nationality?
        # TODO

        # 1. Is the name unique?
        # Uniqueness constraints are not applied in the database, since there
        # are a few legitimate reasons for a record to duplicate some fields of
        # another record (e.g. different Japanese readings). For our purposes,
        # two names are duplicates if they are from the same nationality, and
        # are written the same in their native script.

        # 1a. Are personal names unique?
        if verbose:
            print('Checking personal names for uniqueness...')
        cur.execute('SELECT p1.Name as Name'
                    ' , p1.Romanisation as RomA'
                    ' , p2.Romanisation as RomB'
                    ' , p1.Gender as GenA'
                    ' , p2.Gender as GenB'
                    ' , p1.Nationality as Nat'
                    ' FROM PersonalNames p1 JOIN PersonalNames p2'
                    '  ON p1.Name = p2.Name AND'
                    '     p1.Nationality = p2.Nationality AND'
                    '     p1.PersonalNameID < p2.PersonalNameID')
        for row in cur:
            show_duplicate_warning(row, ('Rom', 'Gen'),
                                   ('romanised as', 'gender'))

        # 1b. Are additional names unique?
        if verbose:
            print('Checking additional names for uniqueness...')
        cur.execute('SELECT a1.Name as Name'
                    ' , a1.Romanisation as RomA'
                    ' , a2.Romanisation as RomB'
                    ' , a1.Gender as GenA'
                    ' , a2.Gender as GenB'
                    ' , a1.Nationality as Nat'
                    ' FROM AdditionalNames a1 JOIN AdditionalNames a2'
                    '  ON a1.Name = a2.Name AND'
                    '     a1.Nationality = a2.Nationality AND'
                    '     a1.AdditionalNameID < a2.AdditionalNameID')
        for row in cur:
            show_duplicate_warning(row, ('Rom', 'Gen'),
                                   ('romanised as', 'gender'))

        # 1c. Are family names unique?
        if verbose:
            print('Checking family names for uniqueness...')
        cur.execute('SELECT f1.Name as Name'
                    ' , f1.Romanisation as RomA'
                    ' , f2.Romanisation as RomB'
                    ' , f1.Gender as GenA'
                    ' , f2.Gender as GenB'
                    ' , fc1.Name as CtpA'
                    ' , fc2.Name as CtpB'
                    ' , f1.Nationality as Nat'
                    ' FROM FamilyNames f1'
                    '  JOIN FamilyNames f2'
                    '   ON f1.Name = f2.Name AND'
                    '      f1.Nationality = f2.Nationality AND'
                    '      f1.FamilyNameID < f2.FamilyNameID'
                    '  JOIN FamilyNames fc1'
                    '   ON f1.CounterpartID = fc1.FamilyNameID'
                    '  JOIN FamilyNames fc2'
                    '   ON f2.CounterpartID = fc2.FamilyNameID')
        for row in cur:
            show_duplicate_warning(row, ('Rom', 'Gen', 'Ctp'),
                                   ('romanised as', 'gender', 'counterpart'))

        # 1d. Are patro-/matronymics unique?
        if verbose:
            print('Checking patro-/matronymics names for uniqueness...')
        cur.execute('SELECT nym1.Name as Name'
                    ' , nym1.Romanisation as RomA'
                    ' , nym2.Romanisation as RomB'
                    ' , nym1.Gender as GenA'
                    ' , nym2.Gender as GenB'
                    ' , pn1.Name as FromA'
                    ' , pn2.Name as FromB'
                    ' , nym1.Nationality as Nat'
                    ' FROM PMatronymics nym1'
                    '  JOIN PMatronymics nym2'
                    '   ON nym1.Name = nym2.Name AND'
                    '      nym1.Nationality = nym2.Nationality AND'
                    '      nym1.PMatronymicID < nym2.PMatronymicID'
                    '  JOIN PersonalNames pn1'
                    '   ON nym1.FromPersonalNameID = pn1.PersonalNameID'
                    '  JOIN PersonalNames pn2'
                    '   ON nym2.FromPersonalNameID = pn2.PersonalNameID')
        for row in cur:
            show_duplicate_warning(row, ('Rom', 'Gen', 'From'),
                                   ('romanised as', 'gender', 'source name'))

        # 2. Do all nationalities provide names for fields listed in their
        # format specifiers, and only for those fields?
        # TODO

        # 3. Do all family name counterparts form mutual cross-gender pairs?
        # TODO

        # 4. Do gendered patro-/matronymics come in pairs?
        # TODO

    finally:
        # Do not commit! No changes should have been made anyway.
        conn.close()

def show_duplicate_warning(row, compare_cols, compare_labels=None):
    '''Format a duplicate-row warning and print it to sys.stderr.

    Keyword arguments:
        row -- A mapping (such as a row from the sqlite3.Row factory).
            The mapping must have at least the keys 'Name', 'Nat', and
            'RomA'.
        compare_cols -- A sequence of strings that indicate pairs of
            keys in row; the keys are formed by appending 'A' and 'B' to
            each string. These values may be different even though the
            rows are considered duplicates.
        compare_labels -- An optional sequence giving a label for each
            string in compare_cols.

    '''
    if compare_labels is None:
        compare_labels = compare_cols
    mismatches = []
    for label, col in zip(compare_labels, compare_cols):
        if row[col + 'A'] != row[col + 'B']:
            mismatches.append("{} '{}' vs. '{}'".format(label,
                                                        row[col + 'A'],
                                                        row[col + 'B']))
    if len(mismatches) == 0:
        print("WARNING: {0[Nat]} name '{0[Name]}'{1} has multiple "
              "entries".format(row,
                               '' if row['RomA'] == '' else
                               " ('{}')".format(row['RomA'])),
              file=sys.stderr)
    else:
        print("WARNING: {0[Nat]} name '{0[Name]}' has multiple "
              "similar entries ({1})".format(row,
                                             ', '.join(mismatches)),
              file=sys.stderr)

def generate(nationality=None, gender=None, verbose=False):
    '''Generate a random name.'''
    nationality = (nat_lookup(nationality) if nationality is not None else
                   random.choice(list(NATIONALITIES)))
    if gender is None:
        gender = random.choice([MASCULINE, FEMININE])

    fmt = random.choice(NATIONALITIES[nationality])

    latin_parts = []
    original_parts = []

    for part in fmt:
        source = NAME_PARTS[part]
        
        random_choices = data(source, gender=gender, nationality=nationality,
                              randomise=True, limit=1, verbose=verbose)
        # TODO: Don't double up on names if one part is used more than once.

        chosen = next(random_choices)
        if chosen.romanisation == '':
            latin_parts.append(chosen.name)
        else:
            original_parts.append(chosen.romanisation)
            latin_parts.append(chosen.name)

    return (' '.join(latin_parts), ' '.join(original_parts),
            gender, nationality)

def argparser():
    '''Construct the command-line argument parser.'''
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
                        help=('rebuild and validate the database (instead of '
                              'generating a name)'))
    parser.add_argument('--skip-rebuild', action='store_true',
                        help=("don't rebuild the database when performing "
                              "validation"))

    gen_args = parser.add_argument_group('Generation options')
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
    '''Handle command-line options and run the name generator.'''
    args = argparser().parse_args()
    if args.action == 'validate':
        if not args.skip_rebuild:
            build_db(verbose=args.verbose)
        validate_data(verbose=args.verbose)
    else:
        if args.verbose:
            print('Generating {} random {}{}'
                  'name{}...'.format(args.count,
                                     {MASCULINE: 'masculine ',
                                      FEMININE: 'feminine '}.get(args.gender,
                                                                 ''),
                                     ('' if args.nat is None else
                                      nat_lookup(args.nat) + ' '),
                                     's' if args.count > 1 else ''))
        for _ in range(args.count):
            (name, original,
             gender, nationality) = generate(nationality=args.nat,
                                             gender=args.gender,
                                             verbose=args.verbose)
            print(name, end='')
            if original != '':
                print(' ({})'.format(original), end='')
            if args.verbose:
                print(' ({}, {})'.format(gender, nationality), end='')
            print()

if __name__ == '__main__':
    main()
