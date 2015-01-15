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
         verbosity=0, **kwargs):
    '''Fetch data from the SQLite database.'''
    nt = nt_for(source)

    query, qparms = ['SELECT * FROM "{}"'.format(source)], []

    # Handle additional keyword arguments as selection criteria (i.e. the WHERE
    # clause): the argument name is the column and its value is what to match
    # in that column. (A keyword prefixed with 'not_' means to return records
    # that don't match instead.)
    NEGATE_PREFIX = 'not_'
    if len(kwargs) > 0:
        query.append('WHERE')
        where = []
        for kw, val in kwargs.items():
            # Are there multiple values specified?
            val_is_multipart = not isinstance(val, str) # Strings don't count.
            if val_is_multipart: # Actually only a maybe at this point.
                try:
                    # Non-sequence types choke on len()...
                    len(val)
                except TypeError:
                    val_is_multipart = False

            # Handle columns prefixed with 'not_'. Aside from looking for non-
            # matches ('<>') instead of matches ('='), this also means joining
            # each of multiple values (if present) with 'AND' rather than 'OR'.
            if kw.startswith(NEGATE_PREFIX):
                # Strip the 'not_' prefix and search for non-matches ('<>').
                colname = kw[len(NEGATE_PREFIX):]
                if val_is_multipart:
                    unmatches = ('"{}" <> ?'.format(colname) for _ in val)
                    where.append('(' + ' AND '.join(unmatches) + ')')
                else:
                    where.append('"{}" <> ?'.format(colname))

            # Special handling for the 'gender' column (include neuter names
            # when searching by gender), unless it's negated (handled above),
            # we're looking for neuter names, or multiple values have been
            # specified.
            elif kw == 'gender' and not val_is_multipart and val is not NEUTER:
                where.append('("{0}" = ? OR "{0}" = ?)'.format(kw))
                qparms.append(NEUTER)

            # Handle every other case.
            else:
                if val_is_multipart:
                    matches = ('"{}" = ?'.format(kw) for _ in val)
                    where.append('(' + ' OR '.join(matches) + ')')
                else:
                    where.append('"{}" = ?'.format(kw))

            # Add the value(s) to the query parameters.
            if val_is_multipart:
                qparms.extend(val)
            else:
                qparms.append(val)
        # Add the WHERE clause to the query.
        query.append(' AND '.join(where))
    if randomise:
        query.append('ORDER BY random()')
    if limit is not None:
        query.append('LIMIT {}'.format(abs(int(limit))))

    # Assemble the query.
    query_string = ' '.join(query)
    # Only display the query if extra verbosity was requested.
    if verbosity > 1:
        print("Executing query '{}' with parameters {!r}".format(query_string,
                                                                 qparms))

    # Pass it to the database.
    if not os.path.isfile(dbfilename):
        build_db(dbfilename=dbfilename, verbosity=verbosity)
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

def build_db(dbfilename=DEFAULT_DBFILE, verbosity=0):
    '''(Re)build the SQLite database from the CSV files.'''
    if verbosity:
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
            # Only detail individual steps if extra verbosity was requested.
            if verbosity > 1:
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
            # Only detail individual steps if extra verbosity was requested.
            if verbosity > 1:
                print('\tTables (re)built')

            # Read data files and populate tables.
            cur.executemany('INSERT INTO PersonalNames'
                            ' (Name, Romanisation, Gender, Nationality)'
                            ' VALUES (?, ?, ?, ?)', csvdata('personal'))
            # Only detail individual steps if extra verbosity was requested.
            if verbosity > 1:
                print('\tPersonal names inserted')

            cur.executemany('INSERT INTO AdditionalNames'
                            ' (Name, Romanisation, Gender, Nationality)'
                            ' VALUES (?, ?, ?, ?)', csvdata('additional'))
            # Only detail individual steps if extra verbosity was requested.
            if verbosity > 1:
                print('\tAdditional names inserted')

            for record in csvdata('family'):
                cur.execute('INSERT INTO FamilyNames'
                            ' (Name, Romanisation, Gender, Nationality)'
                            ' VALUES (?, ?, ?, ?)', (record.name,
                                                     record.romanisation,
                                                     record.gender,
                                                     record.nationality))
            # Only detail individual steps if extra verbosity was requested.
            if verbosity > 1:
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
            # Only detail individual steps if extra verbosity was requested.
            if verbosity > 1:
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
            # Only detail individual steps if extra verbosity was requested.
            if verbosity > 1:
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
            # Only detail individual steps if extra verbosity was requested.
            if verbosity > 1:
                print('\tViews created')
    finally:
        conn.close()

TABLES = ('PersonalNames', 'AdditionalNames', 'FamilyNames', 'PMatronymics')

def validate_data(dbfilename=DEFAULT_DBFILE, verbosity=0):
    '''Validate non-SQL database constraints.'''
    if not os.path.isfile(dbfilename):
        build_db(dbfilename=dbfilename, verbosity=verbosity)
    conn = sqlite3.connect(dbfilename)
    conn.row_factory = sqlite3.Row
    try:
        # 0. Do only known values exist for gender and nationality?
        if verbosity:
            print('Checking for unknown genders...')
        check_for_unknowns(conn, 'Gender', GENDERS)
        if verbosity:
            print('Checking for unknown nationalities...')
        check_for_unknowns(conn, 'Nationality', NATIONALITIES.keys())

        # 1. Is each name unique?
        if verbosity:
            print('Checking personal names for uniqueness...')
        check_for_uniqueness(conn, 'PersonalNames', 'PersonalNameID')

        if verbosity:
            print('Checking additional names for uniqueness...')
        check_for_uniqueness(conn, 'AdditionalNames', 'AdditionalNameID')

        if verbosity:
            print('Checking family names for uniqueness...')
        check_for_uniqueness(conn, 'FamilyNames', 'FamilyNameID',
                             (('FamilyNames', 'Name', 'Ctp', 'counterpart',
                               'CounterpartID', 'FamilyNameID'),))
        if verbosity:
            print('Checking patro-/matronymics for uniqueness...')
        check_for_uniqueness(conn, 'PMatronymics', 'PMatronymicID',
                             (('PersonalNames', 'Name', 'From', 'source name',
                               'FromPersonalNameID', 'PersonalNameID'),))

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

def check_for_unknowns(conn, col, known_values, tables=TABLES):
    '''Check the database for unknown values in a given column.'''
    cur = conn.cursor()

    for table in tables:
        cur.execute('SELECT {0} AS Checked, COUNT(Name) AS Count'
                    ' FROM {1}'
                    ' GROUP BY {0}'.format(col, table))
        for row in cur:
            if row['Checked'] not in known_values:
                print("ERROR: unknown {0} '{1[Checked]}' (appears {1[Count]} "
                      "time{2} in table '{3}')".format(col.lower(), row,
                                                       ('' if row['Count'] == 1
                                                        else 's'), table),
                      file=sys.stderr)

def check_for_uniqueness(conn, table, id_col, extra_joins=()):
    '''Check that all rows in a given table are unique.

    Unique, in this instance, means that no two rows list the same name
    from the same nationality. The database does not enforce this as a
    uniqueness constraint anywhere, since there are a few legitimate
    reasons for two records to duplicate these fields (e.g. different
    Japanese readings).

    '''
    compare_cols = ['Rom', 'Gen']
    compare_labels = ['romanised as', 'gender']

    select_clause = ['SELECT tblA.Name AS Name'
                     ' , tblA.Romanisation AS RomA'
                     ' , tblB.Romanisation AS RomB'
                     ' , tblA.Gender AS GenA'
                     ' , tblB.Gender AS GenB'
                     ' , tblA.Nationality as Nat']
    from_clause = [' FROM {0} tblA'
                   '  JOIN {0} tblB'
                   '   ON tblA.Name = tblB.Name AND'
                   '      tblA.Nationality = tblB.Nationality AND'
                   '      tblA.{1} < tblB.{1}'.format(table, id_col)]
    for n, (to_table, col, alias, natural_alias,
            from_col, to_col) in enumerate(extra_joins):
        select_clause.append(' , ex{0}A.{1} AS {2}A'
                             ' , ex{0}B.{1} AS {2}B'.format(n, col, alias))
        from_clause.append('  JOIN {0} ex{1}A'
                           '   ON tblA.{2} = ex{1}A.{3}'
                           '  JOIN {0} ex{1}B'
                           '   ON tblB.{2} = ex{1}B.{3}'.format(to_table, n,
                                                                from_col,
                                                                to_col))
        compare_cols.append(alias)
        compare_labels.append(natural_alias)

    # Execute the query.
    cur = conn.cursor()
    cur.execute(''.join(select_clause + from_clause))

    # Warn about any duplicate rows.
    for row in cur:
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

def generate(nationality=None, gender=None, verbosity=0):
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
                              randomise=True, limit=1, verbosity=verbosity)
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
            build_db(verbosity=args.verbose)
        validate_data(verbosity=args.verbose)
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
                                             verbosity=args.verbose)
            print(name, end='')
            if original != '':
                print(' ({})'.format(original), end='')
            if args.verbose:
                print(' ({}, {})'.format(gender, nationality), end='')
            print()

if __name__ == '__main__':
    main()
