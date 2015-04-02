#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''Access the namechoose data files.'''
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

# Compatibility features.
from __future__ import absolute_import, print_function, unicode_literals
try:
    # Python 2
    basestring
except NameError:
    # Python 3
    basestring = str

# Standard library imports.
from collections import namedtuple
import csv
import os.path
import sqlite3

__all__ = ['MASCULINE', 'FEMININE', 'NEUTER', 'GENDERS', 'DEFAULT_DBFILE',
           'DATA_COLUMNS', 'build_db', 'getdata']

# Symbolic constants for genders, and a list of nationalities for validation.
MASCULINE, FEMININE, NEUTER = GENDERS = 'MFN'
NATIONALITIES = ['Armenian', 'Chinese', 'Danish', 'English', 'Finnish',
                 'Georgian', 'Hungarian', 'Icelandic', 'Japanese', 'Latin',
                 'Latvian', 'Polish', 'Russian', 'Spanish', 'Turkish',
                 'Ukrainian', 'Vietnamese']

# Locate the data files.
THIS_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(THIS_DIR, 'dat')
if not os.path.isdir(DATA_DIR):
    raise IOError('data directory not found')
DEFAULT_DBFILE = os.path.join(DATA_DIR, 'namechoose.db')

# Data source layouts.
# This dictionary matches identifiers to tuples of headings, which are from
# the following list:
# * 'name': The name in its native script.
# * 'romanisation': The name in the native script (empty if that is Latin).
# * 'counterpart': A corresponding name with the opposite ('M'/'F') gender.
# * 'from_': A name from which another (e.g. a patronym) is derived, as it
#      appears in the 'name' field (i.e. in the native script).
# * 'gender': 'M' for male names, 'F' for female, 'N' if applicable to either.
# * 'nationality': A key from the NATIONALITIES mapping.
DATA_COLUMNS = {'personal': ('name', 'romanisation', 'gender', 'nationality'),
                'additional': ('name', 'romanisation', 'gender',
                               'nationality'),
                'family': ('name', 'romanisation', 'gender', 'counterpart',
                           'nationality'),
                'pmatronymic': ('name', 'romanisation', 'from_', 'gender',
                                'nationality')
                }
# Shorthand to construct a namedtuple class suitable for each data source.
nt_for = lambda source: namedtuple('{}_tuple'.format(source),
                                   DATA_COLUMNS[source])

def csvdata(source):
    '''Read in data from the named CSV source file.'''
    filename = os.path.join(DATA_DIR, source + '.csv')
    nt = nt_for(source)

    try:
        reader = csv.reader(open(filename, encoding='utf-8'))
    except TypeError:
        # Under Python 2, open() doesn't support the encoding argument. We
        # could switch to codecs.open() instead, but the underlying problem
        # is that the csv module doesn't support Unicode. So, we want to read
        # bytes from the file, and then encode them after csv has used them but
        # before they go anywhere else. This is taken from the csv module docs,
        # with unneeded code stripped and the call to unicode() replaced with
        # decode().
        def unicode_csv_reader(unicode_csv_data):
            csv_reader = csv.reader(unicode_csv_data)
            for row in csv_reader:
                yield [cell.decode('utf-8') for cell in row]

        reader = unicode_csv_reader(open(filename))

    return map(nt._make, reader)

def getdata(source, dbfilename=DEFAULT_DBFILE, randomise=False, limit=None,
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
            # Are there multiple values specified? (Strings don't count.)
            val_is_multipart = not isinstance(val, basestring)
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
                    if len(val) == 0:
                        # Empty list. Abort! Abort!
                        continue
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
        cur = conn.cursor()
        cur.execute(query_string, qparms)
        results = map(nt._make, cur.fetchall())
    finally:
        # Do not commit (as no changes ought to have been made). Just close it.
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
