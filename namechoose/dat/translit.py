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
import re

# LRU caches.
_CACHE_LIMIT = 10
_cached_rulefiles = OrderedDict()
_cached_rulesets = OrderedDict()

DEFAULT_FILENAME = 'translit.json'

def ruleset(lang, filename=None):
    """Load a transliteration ruleset from a file.

    Keyword arguments:
        lang -- The language code for the transliteration ruleset.
        filename -- The name of a JSON file containing one or more
            transliteration rulesets. If omitted, the default file
            ('{}') is tried.

    """.format(DEFAULT_FILENAME)
    if filename is None:
        filename = DEFAULT_FILENAME

    try:
        from_cache = _cached_rulesets[(filename, lang)]
        # Update the recent-use status of this cache entry.
        _cached_rulesets.move_to_end((filename, lang))

        return from_cache
    except KeyError:
        # This language ruleset is not cached. Is the file it's in cached?
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

        rules = rulefile.get(lang)
        if rules is None:
            ruleset = None
        else:
            # Compile the regexes in this ruleset.
            ruleset = list((re.compile(regex), output)
                           for regex, output in rules)

        _cached_rulesets[(filename, lang)] = ruleset
        # Maintain the LRU cache size.
        if len(_cached_rulesets) > _CACHE_LIMIT:
            _cached_rulesets.popitem()

        return ruleset

def translit(s, lang, filename=None):
    """Transliterate a string according to rules for a given language."""
    rules = ruleset(lang, filename)
    if rules is None:
        # No transliteration rules available. Return the string unchanged.
        return s

    result = []
    pos = 0
    while pos < len(s):
        for regex, output in rules:
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
