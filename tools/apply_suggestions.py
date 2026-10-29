#!/usr/bin/env python3
"""Vanaguide :: tools/apply_suggestions.py
Add quest/mission givers suggested from VanaGuide Server-Safe (suggested-changes/*.lua) to the
data files, but only to entries that have no zone (and no giver) yet. Nothing that exists is
changed. Safe to run any number of times, and again after regenerating the data files.

    tools/apply_suggestions.py [suggestions dir] [data dir]

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HEADING = re.compile(r"^\s*--\s*(quests|missions)\.(\w+)\b")
LINE = re.compile(r"^\s*\[(\d+)\]\s*=\s*\{(.*)\}\s*,?\s*$")
ENTRY = re.compile(r"(\s+\[(\d+)\] = \{ )(.*?)( \},?)$")
QUOTED = re.compile(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"")
# An NPC name as the data files write it: letters, digits, spaces as _, apostrophes, hyphens.
NPC_OK = re.compile(r"[A-Za-z][A-Za-z0-9_'. -]{1,40}\Z")


def unquote(value):
    """Decode only the export format's quoted strings; never execute Lua."""
    body = value[1:-1]
    if re.search(r"\\[^\\'\"]", body):
        return None
    return re.sub(r"\\([\\'\"])", r"\1", body)


def string_field(line, key):
    # Mask literals without moving offsets so field-like text inside a title/note is ignored.
    masked = QUOTED.sub(lambda m: ' ' * len(m.group()), line)
    match = re.search(r'\b' + key + r'\s*=\s*', masked)
    if not match:
        return None
    # The mask consumes the literal's whitespace too: locate '=' on the original line.
    start = masked.index('=', match.start()) + 1
    start += len(line[start:]) - len(line[start:].lstrip())
    quoted = QUOTED.match(line, start)
    return unquote(quoted.group()) if quoted else None


def suggestions(folder):
    """{(kind, area, id): (zone, npc, title)}; conflicting suggestions need review."""
    out = {}
    conflicts = set()
    for path in sorted(glob.glob(os.path.join(folder, '*.lua'))):
        kind = area = None
        with open(path, encoding='utf-8') as source:
            lines = source.readlines()
        for line in lines:
            h = HEADING.search(line)
            if h:
                kind, area = h.group(1), h.group(2)
                continue
            m = LINE.search(line)
            if not (m and kind):
                continue
            body = m.group(2)
            masked = QUOTED.sub(lambda q: ' ' * len(q.group()), body)
            location = re.search(r'\bzone\s*=\s*(\d+)(?=\s*(?:,|$))', masked)
            zone = int(location.group(1)) if location else 0
            npc, name = string_field(body, 'npc'), string_field(body, 'name')
            if not (0 < zone < 1024) or not npc or not NPC_OK.fullmatch(npc) or not name:
                print('%s: skipped invalid entry %s' % (os.path.basename(path), m.group(1)))
                continue
            key, value = (kind, area, int(m.group(1))), (zone, npc, name)
            if key in out and out[key] != value:
                conflicts.add(key)
            out.setdefault(key, value)
    for key in sorted(conflicts):
        print('skipped conflicting suggestions for %s.%s %s' % key)
        del out[key]
    return out


def apply(path, kind, wanted):
    with open(path, encoding='utf-8') as source:
        lines = source.read().splitlines()
    area, added = None, []
    for i, line in enumerate(lines):
        m = re.match(r"    (\w+) = \{$", line)
        if m:
            area = m.group(1)
            continue
        m = ENTRY.match(line)
        if not (m and area):
            continue
        s = wanted.get((kind, area, int(m.group(2))))
        masked = QUOTED.sub('', m.group(3))
        # Preserve any existing location, regardless of whitespace or field ordering.
        if not s or re.search(r'\b(?:zone|npc)\s*=', masked):
            continue
        if string_field(m.group(3), 'name') != s[2]:
            print('skipped stale/mismatched title for %s.%s %s' % (kind, area, m.group(2)))
            continue
        npc = s[1].replace('\\', '\\\\').replace("'", "\\'")
        lines[i] = "%s%s, zone = %d, npc = '%s'%s" % (m.group(1), m.group(3), s[0], npc, m.group(4))
        added.append('%s.%s %s' % (kind, area, m.group(2)))
    if added:
        with open(path, 'w', encoding='utf-8') as target:
            target.write('\n'.join(lines) + '\n')
    return added


def main(folder=os.path.join(ROOT, 'suggested-changes'), data=os.path.join(ROOT, 'Vanaguide', 'data')):
    wanted = suggestions(folder)
    added = apply(os.path.join(data, 'quests.lua'), 'quests', wanted) \
        + apply(os.path.join(data, 'missions.lua'), 'missions', wanted)
    for a in added:
        print('added', a)
    print('%d valid nonconflicting suggestions, %d added; existing or unmatched entries unchanged'
          % (len(wanted), len(added)))


if __name__ == '__main__':
    main(*sys.argv[1:3])
