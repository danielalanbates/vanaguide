#!/usr/bin/env python3
"""Vanaguide :: tools/merge_locations.py
Fill in only what a data file is missing: add `zone/x/z/y` (and `npc` when it names a person)
from a freshly generated file to entries that have no location. Nothing that exists is changed,
so entries from an older server checkout survive and reviewed names are not overwritten.

    tools/merge_locations.py <current data file> <freshly generated file>

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import re
import sys

NOT_PEOPLE = re.compile(r"(?i)^(door|region|area|entrance|gate|zone)\b|\bregion$|\bdoor\b"
                        r"|^(fire|ice|wind|earth|lightning|water|light|dark)$")  # headstones
ENTRY = re.compile(r"(\s+\[(\d+)\] = \{ )(.*?)( \},?)$")


def entries(path):
    out, area = {}, None
    for line in open(path, encoding='utf-8').read().splitlines():
        m = re.match(r"    (\w+) = \{$", line)
        if m:
            area = m.group(1)
            continue
        m = ENTRY.match(line)
        if m and area:
            out[(area, int(m.group(2)))] = m.group(3)
    return out


def main(current, fresh):
    new = entries(fresh)
    lines = open(current, encoding='utf-8').read().splitlines()
    area, added, named = None, 0, 0
    for i, line in enumerate(lines):
        m = re.match(r"    (\w+) = \{$", line)
        if m:
            area = m.group(1)
            continue
        m = ENTRY.match(line)
        if not (m and area) or 'zone =' in line:
            continue
        body = new.get((area, int(m.group(2))))
        if not body or 'zone =' not in body:
            continue
        extra = re.search(r"zone = \d+, x = [-\d.]+, z = [-\d.]+, y = [-\d.]+", body).group(0)
        npc = re.search(r"npc = ('(?:[^'\\]|\\.)*')", body)
        if npc and not NOT_PEOPLE.search(npc.group(1).strip("'")):
            extra += ', npc = ' + npc.group(1)
            named += 1
        lines[i] = m.group(1) + m.group(3) + ', ' + extra + m.group(4)
        added += 1
    open(current, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('%s: %d locations added, %d with a named giver' % (current, added, named))


if __name__ == '__main__':
    main(*sys.argv[1:3])
