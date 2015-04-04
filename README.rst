==============================
Namegen: Random name generator
==============================

Namegen generates random, (vaguely) realistic names, conforming to the naming
conventions of several nationalities.

At present, Namegen has data files and support for these modern nationalities:

* Armenian (50 personal names, 33 family names)
* Chinese (56 family names, 108 personal names) in simplified characters and in
  pinyin
* Danish (72 personal names, 38 family names)
* English (99 personal names, 71 family names)
* Finnish (120 personal names, 81 family names)
* French (140 personal names, 85 family names)
* Georgian (40 personal names, 22 family names)
* Hungarian (21 family names, 52 personal names)
* Icelandic (71 personal names and corresponding patro-/matronyms, plus 12
  middle names and 33 family names)
* Japanese (33 family names, 107 personal names, including different kanji and
  even different readings in rōmaji)
* Latvian (33 personal names, 21 family names with both masculine and feminine
  forms)
* Polish (111 personal names, 53 family names including 30 with both masculine
  and feminine forms)
* Russian (79 personal names with corresponding patronyms for masculine
  names, 56 family names with both masculine and feminine forms)
* Spanish (58 personal names including two-part names, 41 family names)
* Turkish (33 personal names, 20 family names)
* Ukrainian (76 personal names with corresponding patronyms for masculine
  names, 50 family names)
* Vietnamese (16 family names, 14 middle names, 63 personal names)

Additionally, historical names from these periods are supported:

* Latin, *circa* the first centuries BC and AD (74 praenomina, 49 nomina in
  masculine and feminine forms, 71 cognomina including 53 with both masculine
  and feminine forms)
* Old Spanish, *circa* the tenth to twelfth centuries (91 personal names with
  corresponding patronyms for masculine names)

Command-line usage
==================
``namegen.py [-h] [--version] [-v] [-G | -V [--skip-rebuild]]
[-o OUTFILE [--overwrite]] [-c COUNT] [-n NAT] [-g {M,F}]``

-v, --verbose      Show detailed information on operations performed.

-------
Actions
-------

-h, --help         Show a help message and exit.
--version          Show version information and exit.
-G, --generate     Generate one or more names. (This is the default action.)
-V, --validate     Rebuild and validate the database.
--skip-rebuild     Do not rebuild the database before validation. This option
                   only has an effect if ``--validate`` is specified.

---------------------
Generation parameters
---------------------

-o OUTFILE, --outfile OUTFILE  Write output to the named file, instead of to
                               standard output. If the file already exists,
                               the new text will be appended to it.
--overwrite                    Overwrite an existing file instead of appending
                               to it. This option only has an effect if
                               ``--outfile`` is specified.
-c COUNT, --count COUNT        Generate ``COUNT`` names (defaults to 1).
-n NAT, --nat NAT              Generate names of nationality ``NAT``. This may
                               be a full name (in English), such as "Russian",
                               or an ISO 639 two- or three-letter code, such
                               as "ru".
-g G, --gender G               The gender of the name(s) generated (either
                               ``M`` or ``F``; must be capitalised).

Copyright and Licence
=====================

Namegen is copyright © 2014, 2015 Timothy Pederick. It is licensed under the
GNU Affero General Public License, either version 3, or (at your option) any
later version.

The author disclaims any copyright in the CSV data files, considering them
mere collections of fact. For the avoidance of doubt, if any copyright is held 
to exist in the data files, it is licensed under the terms of the Creative
Commons Public Domain Dedication ("`CC-zero`__").

__ https://creativecommons.org/publicdomain/zero/1.0/deed.en
