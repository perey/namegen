#!/usr/bin/env python3

"""Transliteration tools."""
# Copyright © 2015 Timothy Pederick.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Standard library imports.
from collections import OrderedDict
import json
import os.path
import re

# LRU caches.
_CACHE_LIMIT = 10
_cached_rulefiles = OrderedDict()
_cached_rulesets = OrderedDict()

# Locate the data file.
THIS_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(THIS_DIR, 'dat')
if not os.path.isdir(DATA_DIR):
    raise IOError('data directory not found')
DEFAULT_FILENAME = os.path.join(DATA_DIR, 'translit.json')

# Bicameral scripts have bicameral transliteration rules.
BICAMERAL = ['Armn', 'Cyrl', 'Grek', 'Latn']

def ruleset_by_id(ruleset_id, filename=None):
    """Load a transliteration ruleset from a file.

    Keyword arguments:
        ruleset_id -- The identifier for the transliteration ruleset.
        filename -- The name of a JSON file containing one or more
            transliteration rulesets. If omitted, the default file
            ('dat/translit.json') is tried.

    """
    if filename is None:
        filename = DEFAULT_FILENAME

    try:
        from_cache = _cached_rulesets[(filename, ruleset_id)]
        # Update the recent-use status of this cache entry.
        _cached_rulesets.move_to_end((filename, ruleset_id))

        return from_cache
    except KeyError:
        # This ruleset is not cached. Is the file it's in cached?
        try:
            rulefile = _cached_rulefiles[filename]
            # Update the recent-use status of this cache entry.
            _cached_rulefiles.move_to_end(filename)
        except KeyError:
            # Nope. Load the file.
            rulefile = json.load(open(filename))
            _cached_rulefiles[filename] = rulefile

            # Maintain the LRU cache size.
            if len(_cached_rulefiles) > _CACHE_LIMIT:
                _cached_rulefiles.popitem()

        ruleset = rulefile.get(ruleset_id)
        if ruleset is not None:
            # Compile the regexes in this ruleset.
            ruleset['rules'] = list((re.compile(regex), output)
                                    for regex, output in ruleset['rules'])

        _cached_rulesets[(filename, ruleset_id)] = ruleset
        # Maintain the LRU cache size.
        if len(_cached_rulesets) > _CACHE_LIMIT:
            _cached_rulesets.popitem()

        return ruleset

def translit(s, ruleset_id, filename=None):
    """Transliterate a string according to a given set of rules.

    Keyword arguments:
        s -- The string to transliterate.
        ruleset_id -- The identifier for the set of rules to use.
        filename -- The name of a JSON file containing the
            transliteration ruleset. If omitted, the default file
            set by the ruleset() function is used.

    """
    ruleset = ruleset_by_id(ruleset_id, filename)
    if ruleset is None:
        # No transliteration rules available. Return the string unchanged.
        return s

    result = []
    pos = 0
    while pos < len(s):
        for regex, output in ruleset['rules']:
            match = regex.match(s, pos)
            if match:
                # We have a match! Transliterate it.
                result.append(output)
                # Consume the characters used in the match and advance.
                pos += len(match.group())
                break
        else:
            # No match at this position. Consume one character,
            # untransliterated, and try again.
            result.append(s[pos])
            pos += 1
    return ''.join(result)

def is_translit(expected, s, ruleset_id, filename=None):
    """Determine whether a string is a correct transliteration of another."""
    actual_translit = translit(s, ruleset_id, filename)
    ruleset = ruleset_by_id(ruleset_id, filename)

    if ruleset["from_script"] in BICAMERAL:
        # Don't case-fold bicameral scripts.
        return actual_translit == expected
    else:
        try:
            # Python 3.3 introduced real case-folding.
            return actual_translit.casefold() == expected.casefold()
        except AttributeError:
            return actual_translit.lower() == expected.lower()
