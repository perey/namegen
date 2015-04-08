#!/usr/bin/env python3

'''Validate the contents of the namechoose database.'''
# Copyright © 2014, 2015 Timothy Pederick.
#
# This file is part of namechoose.
#
# Namechoose is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Namechoose is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with namechoose.  If not, see <http://www.gnu.org/licenses/>.

# Standard library imports.
import os.path
import sqlite3
import sys

# Local library imports.
from . import (GENDERS, MASCULINE, FEMININE, NEUTER, FORMATS, NAME_PARTS,
               NATIONALITIES)
from .data import getdata, DEFAULT_DBFILE, DATA_COLUMNS
from . import translit

__all__ = ['validate_data']

TABLES = ('PersonalNames', 'AdditionalNames', 'FamilyNames', 'PMatronymics')

TRANSLIT_RULESETS = {'Russian': 'ru_BGN_PCGN_modified',
                     'Ukrainian': 'uk_BGN_PCGN_simple'}

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
        check_for_unknowns(conn, 'Nationality', NATIONALITIES)

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
        for nat, fmts in FORMATS.items():
            expected_sources = set(NAME_PARTS[part] for fmt in fmts
                                   for part in fmt)
            if verbosity:
                print('Checking whether {} names appear in {}, and nowhere '
                      'else...'.format(nat, ', '.join(expected_sources)))

            for source in DATA_COLUMNS:
                cur = conn.cursor()
                cur.execute('SELECT COUNT(*) AS Count'
                            ' FROM "{}"'
                            ' WHERE nationality = ?'.format(source),
                            (nat,))
                count = cur.fetchone()['Count']
                if verbosity > 1:
                    print("\tFound {} names in '{}'.".format(count, source))

                if source in expected_sources and count == 0:
                    print("ERROR: no {} names found in source "
                          "'{}'".format(nat, source), file=sys.stderr)
                elif source not in expected_sources and count > 0:
                    print("WARNING: found {} {} names in source "
                          "'{}'".format(count, nat, source), file=sys.stderr)

        # 3. Do all family name counterparts form mutual cross-gender pairs?
        if verbosity:
            print('Checking whether surname counterparts match up...')
        masc_to_fem = {}

        cur = conn.cursor()
        cur.execute('SELECT name'
                    ' , gender'
                    ' , counterpart'
                    ' , nationality'
                    ' FROM "family"'
                    ' WHERE counterpart IS NOT NULL')
        for row in cur:
            if row['gender'] not in (MASCULINE, FEMININE):
                print("ERROR: ungendered {0[nationality]} name '{0[name]}' "
                      "has a counterpart ('{0[counterpart]}')".format(row),
                      file=sys.stderr)
            else:
                masc, fem = ((row['name'], row['counterpart'])
                             if row['gender'] == MASCULINE else
                             (row['counterpart'], row['name']))
                try:
                    if masc_to_fem[masc] != fem:
                        print("ERROR: mismatched {} surnames (masculine '{}', "
                              "feminine '{}')".format(row['nationality'],
                                                      masc, fem),
                              file=sys.stderr)
                except KeyError:
                    masc_to_fem[masc] = fem

        # 4. Do gendered patro-/matronymics come in pairs?
        if verbosity:
            print('Checking whether gendered patro-/matronymics come in '
                  'pairs...')
        child_of = {}

        cur = conn.cursor()
        cur.execute('SELECT name'
                    ' , gender'
                    ' , from_'
                    ' , nationality'
                    ' FROM "pmatronymic"'
                    ' WHERE gender <> ?', (NEUTER,))
        for row in cur:
            try:
                child_names = child_of[(row['nationality'], row['from_'])]

                try:
                    child_names[row['gender']].append(row['name'])
                except KeyError:
                    child_names[row['gender']] = [row['name']]
            except KeyError:
                child_of[(row['nationality'],
                          row['from_'])] = {row['gender']: [row['name']]}

        for (nat, name), childnames in child_of.items():
            for gword, gender in (('masculine', MASCULINE),
                                  ('feminine', FEMININE)):
                if len(childnames[gender]) == 0:
                    print("ERROR: {} name '{}' lacks {} child "
                          "name(s)".format(nat, name, gword), file=sys.stderr)

        # 5. Do patro-/matronymics cover all names from nationalities that
        # use them?
        # TODO

        # 6. Do all transliterated names obey a transliteration standard, if
        # one is available?
        for nat, ruleset_id in TRANSLIT_RULESETS.items():
            if verbosity:
                print('Checking whether {} transliterations are '
                      'correct...'.format(nat))

            if translit.ruleset(ruleset_id) is None:
                print('WARNING: transliteration rules for {} could not be '
                      'found. Skipping...'.format(nat), file=sys.stderr)
                continue

            fmts = FORMATS[nat]
            sources_to_check = set(NAME_PARTS[part] for fmt in fmts
                                   for part in fmt)

            for source in sources_to_check:
                cur = conn.cursor()
                cur.execute('SELECT name'
                            ' , romanisation'
                            ' FROM "{}"'
                            ' WHERE nationality = ?'.format(source),
                            (nat,))
                for row in cur:
                    if verbosity > 1:
                        print("\t'{}' to '{}': ".format(row['name'],
                                                        row['romanisation']),
                              end='')

                    expected_translit = translit.translit(row['name'],
                                                          ruleset_id)
                    if (expected_translit != row['romanisation']):
                        if verbosity > 1:
                            print("no, got '{}'".format(expected_translit))

                        print("WARNING: {0} name '{1[name]}' is romanised as "
                              "'{1[romanisation]}', expected "
                              "'{2}'".format(nat, row, expected_translit),
                              file=sys.stderr)
                    elif verbosity > 1:
                        print('OK')

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
                print("WARNING: unknown {0} '{1[Checked]}' (appears "
                      "{1[Count]} time{3} in table "
                      "'{2}')".format(col.lower(), row, table,
                                      ('' if row['Count'] == 1 else 's')),
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
