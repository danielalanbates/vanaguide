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
HEADING = re.compile(r"--\s*(quests|missions)\.(\w+)\b")
LINE = re.compile(r"\[(\d+)\]\s*=\s*\{.*?\bzone\s*=\s*(\d+)\s*,\s*npc\s*=\s*'((?:[^'\\]|\\.)*)'")
ENTRY = re.compile(r"(\s+\[(\d+)\] = \{ )(.*?)( \},?)$")
# An NPC name as the data files write it: letters, digits, spaces as _, apostrophes, hyphens.
NPC_OK = re.compile(r"^[A-Za-z][A-Za-z0-9_'\\. -]{1,40}$")


def suggestions(folder):
    """{(kind, area, id): (zone, npc)}; the first file (by name) to suggest an entry wins."""
    out = {}
    for path in sorted(glob.glob(os.path.join(folder, '*.lua'))):
        kind = area = None
        for line in open(path, encoding='utf-8'):
            h = HEADING.search(line)
            if h:
                kind, area = h.group(1), h.group(2)
                continue
            m = LINE.search(line)
            if not (m and kind):
                continue
            zone, npc = int(m.group(2)), m.group(3)
            if not (0 < zone < 1024) or not NPC_OK.match(npc):
                print('%s: skipped %s' % (os.path.basename(path), line.strip()))
                continue
            out.setdefault((kind, area, int(m.group(1))), (zone, npc))
    return out


def apply(path, kind, wanted):
    lines = open(path, encoding='utf-8').read().splitlines()
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
        if not s or 'zone =' in line or 'npc =' in line:
            continue
        lines[i] = "%s%s, zone = %d, npc = '%s'%s" % (m.group(1), m.group(3), s[0], s[1], m.group(4))
        added.append('%s.%s %s' % (kind, area, m.group(2)))
    if added:
        open(path, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    return added


def main(folder=os.path.join(ROOT, 'suggested-changes'), data=os.path.join(ROOT, 'Vanaguide', 'data')):
    wanted = suggestions(folder)
    added = apply(os.path.join(data, 'quests.lua'), 'quests', wanted) \
        + apply(os.path.join(data, 'missions.lua'), 'missions', wanted)
    for a in added:
        print('added', a)
    print('%d suggestions, %d added (the rest already had a location)' % (len(wanted), len(added)))


if __name__ == '__main__':
    main(*sys.argv[1:3])
