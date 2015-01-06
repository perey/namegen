==============================
Namegen: Random name generator
==============================

Namegen generates random, (vaguely) realistic names, conforming to the naming
conventions of several nationalities.

At present, Namegen has data files and support for these nationalities:

* Armenian (50 personal names, 33 family names)
* Chinese (22 family names, 23 personal names) in simplified characters and in
  pinyin
* English (87 personal names, 57 family names)
* Georgian (40 personal names, 22 family names)
* Hungarian (21 family names, 52 personal names)
* Icelandic (66 personal names and corresponding patro-/matronyms, plus 33
  family names)
* Japanese (33 family names, 107 personal names, including different kanji and
  even different readings in rōmaji)
* Latvian (33 personal names, 21 family names with both masculine and feminine
  forms)
* Polish (111 personal names, 53 family names including 30 with both masculine
  and feminine forms)
* Russian (79 personal names with corresponding patronyms for masculine
  names, 56 family names with both masculine and feminine forms)
* Spanish (50 personal names including two-part names, 41 family names)
* Ukrainian (76 personal names with corresponding patronyms for masculine
  names, 50 family names)
* Vietnamese (16 family names, 14 middle names, 63 personal names)

Command-line usage
==================
``namegen.py [-h] [--version] [-v] [-G | -V] [-c COUNT] [-n NAT] [-g {M,F}]``

``-v``, ``--verbose``
    Show detailed information on operations performed.

-------
Actions
-------

``-h``, ``--help``
    Show a help message and exit.
``--version``
    Show version information and exit.
``-G``, ``--generate``
    Generate one or more names. (This is the default action.)
``-V``, ``--validate``
    Perform validation of data files.

---------------------
Generation parameters
---------------------

``-c COUNT``, ``--count COUNT``
    Generate ``COUNT`` names (defaults to 1).
``-n NAT``, ``--nat NAT``
    Generate names of nationality ``NAT``. This may be a full name (in
    English), such as "Russian", or an ISO 639 two- or three-letter code, such
    as "ru".
``-g {M,F}``, ``--gender {M,F}``
    The gender of the name(s) generated.
