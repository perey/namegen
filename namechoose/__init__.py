#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Generate random names by choosing parts from a list of common ones.'''
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
from collections import defaultdict
import random

# Local library imports.
from .data import getdata, MASCULINE, FEMININE, NEUTER, GENDERS

__all__ = ['__version__', '__author__', '__copyright__',
           'MASCULINE', 'FEMININE', 'NEUTER', 'GENDERS',
           'generate']

__version__ = '0.2'
__author__ = 'Timothy Pederick'
__copyright__ = 'Copyright © 2014, 2015 Timothy Pederick'

# Supported name formats by nationality.
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
FORMATS = {'Armenian': (('personal', 'family'),),
           'Chinese': (('family', 'personal'),),
           'Danish': (('personal', 'family'),
                      ('personal', 'personal', 'family')),
           'English': (('personal', 'personal', 'family'),
                       ('personal', 'family')),
           'Finnish': (('personal', 'family'),
                       ('personal', 'personal', 'family')),
           'Georgian': (('personal', 'family'),),
           'Hungarian': (('family', 'personal'),),
           'Icelandic': (('personal', 'patronym'),
                         ('personal', 'matronym'),
                         ('personal', 'additional', 'patronym'),
                         ('personal', 'additional', 'matronym'),
                         ('personal', 'patronym', 'matronym'),
                         ('personal', 'patronym', 'family'),
                         ('personal', 'matronym', 'family'),),
           'Japanese': (('family', 'personal'),),
           'Latin': (('personal', 'family'),
                     ('personal', 'family', 'additional')),
           'Latvian': (('personal', 'family'),),
           'Polish': (('personal', 'personal', 'family'),
                      ('personal', 'family')),
           'Russian': (('personal', 'patronym', 'family'),),
           'Spanish': (('personal', 'patriname', 'matriname'),
                       ('personal', 'matriname', 'patriname')),
           'Turkish': (('personal', 'family'),),
           'Ukrainian': (('personal', 'patronym', 'family'),),
           'Vietnamese': (('family', 'additional', 'personal'),)
           }
# Mapping of name parts to data sources.
# This dictionary maps strings from the name-format tuples of FORMATS to the
# relevant data sources. Values of 'personal', 'family' and 'additional' come
# from data sources with the same names, while 'matronym' and 'patronym' values
# come from the source 'pmatronymic', and values of 'matriname' and 'patriname'
# come from the same source as 'family'.
NAME_PARTS = {'personal': 'personal',
              'additional': 'additional',
              'family': 'family',
              'matronym': 'pmatronymic',
              'patronym': 'pmatronymic',
              'matriname': 'family',
              'patriname': 'family'
              }

# Data on supported nationalities.
NATIONALITIES = list(FORMATS)
NAT_ABBREVS = {'hy': 'Armenian', 'hye': 'Armenian', 'arm': 'Armenian',
               'zh': 'Chinese', 'zho': 'Chinese', 'chi': 'Chinese',
               'da': 'Danish', 'dan': 'Danish',
               'en': 'English', 'eng': 'English',
               'fi': 'Finnish', 'fin': 'Finnish',
               'ka': 'Georgian', 'kat': 'Georgian', 'geo': 'Georgian',
               'hu': 'Hungarian', 'hun': 'Hungarian',
               'is': 'Icelandic', 'isl': 'Icelandic', 'ice': 'Icelandic',
               'ja': 'Japanese', 'jpn': 'Japanese',
               'la': 'Latin', 'lat': 'Latin',
               'lv': 'Latvian', 'lav': 'Latvian',
               'pl': 'Polish', 'pol': 'Polish',
               'ru': 'Russian', 'rus': 'Russian',
               'es': 'Spanish', 'spa': 'Spanish',
               'tu': 'Turkish', 'tur': 'Turkish',
               'uk': 'Ukrainian', 'ukr': 'Ukrainian',
               'vi': 'Vietnamese', 'vie': 'Vietnamese'}
# Get suitable values for nationality arguments.
# If the argument is already a full nationality name (or if it is
# unrecognised), it is returned unchanged. If it is an abbreviation,
# the corresponding full name is returned.
nat_lookup = lambda nat: NAT_ABBREVS.get(nat, nat)

def generate(nationality=None, gender=None, verbosity=0):
    '''Generate a random name.

    Keyword arguments:
        nationality, gender -- Specify values for these two name
            parameters. If omitted, random values are chosen.
        verbosity -- A numeric value that sets the amount of diagnostic
            detail dumped to standard output. The default is 0, for no
            output.
    Returns:
        A 5-tuple containing:
            * A sequence of name parts in the original script
            * A sequence of Romanised name parts (empty if the original
              script is Latin)
            * The gender of the name
            * The nationality of the name
            * The format of the name (a sequence of labels for the name
              parts)

    '''
    # If given a nationality, use it (possibly after converting it from an
    # abbreviation); otherwise, randomly choose one.
    nationality = (nat_lookup(nationality) if nationality is not None else
                   random.choice(NATIONALITIES))
    # If given a gender, use it; otherwise, randomly choose one.
    if gender is None:
        gender = random.choice([MASCULINE, FEMININE])

    # Randomly choose a format out of those offered by the nationality.
    fmt = random.choice(FORMATS[nationality])

    # Prepare to store the resulting name, in the original script and (where
    # relevant) in Latin transcription.
    original_parts = []
    romanised_parts = []

    # Keep track of names we've seen, indexed by name part, to avoid giving
    # repetitive names.
    seen_names = defaultdict(list)

    # Iterate over the different name parts in the chosen format.
    for part in fmt:
        # Look up the data source for this name part.
        source = NAME_PARTS[part]
        # Grab one random entry from the database.
        random_choices = getdata(source, gender=gender,
                                 nationality=nationality,
                                 not_name=seen_names[part], randomise=True,
                                 limit=1, verbosity=verbosity)
        # Use the first (and only) result that the database returned.
        chosen = random_choices[0]
        # Add it to our seen list.
        seen_names[part].append(chosen.name)

        # And add it to the result.
        original_parts.append(chosen.name)
        if chosen.romanisation != '':
            romanised_parts.append(chosen.romanisation)

    return (original_parts, romanised_parts, gender, nationality, fmt)
