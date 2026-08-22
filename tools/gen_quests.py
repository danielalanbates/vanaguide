#!/usr/bin/env python3
"""Vanaguide :: tools/gen_quests.py

Build the quest database from LandSandBoat's server scripts.

Why the server and not a wiki: every private server this addon can run on IS a
LandSandBoat (or AirSkyBoat) server, so its scripts are not a description of the quests —
they are the quests. Each quest file states its log area and quest id, the coordinates of
the NPCs involved, what it awards, and which quest it requires, in a form that does not
drift from what the player will actually experience. Wiki text is prose about the same
facts, under licences that do not permit redistribution; these are the facts.

The generated file holds ids, coordinates and names — game data, not LandSandBoat's code
or prose. Nothing is copied out of their scripts.

    tools/gen_quests.py <path to a LandSandBoat checkout> [-o Vanaguide/data/quests.lua]

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import os
import re
import sys
from collections import defaultdict

AREA_LOG = {
    'sandoria': 'sandoria', 'bastok': 'bastok', 'windurst': 'windurst',
    'jeuno': 'jeuno', 'otherAreas': 'other', 'outlands': 'outlands',
    'ahtUrhgan': 'ahturhgan', 'crystalWar': 'wotg', 'abyssea': 'abyssea',
    'adoulin': 'adoulin', 'coalition': 'coalition',
}


def parse_ids(root):
    """scripts/globals/quests.lua -> {lsb area: {CONST: id}}"""
    path = os.path.join(root, 'scripts/globals/quests.lua')
    text = open(path, encoding='utf-8').read()
    out, area = defaultdict(dict), None
    for line in text.splitlines():
        m = re.search(r"\[xi\.quest\.area\[xi\.questLog\.(\w+)\]\]", line)
        if m:
            area = m.group(1)
            continue
        m = re.match(r"\s*([A-Z][A-Z0-9_]+)\s*=\s*(\d+)", line)
        if m and area:
            out[area][m.group(1)] = int(m.group(2))
    return out


def parse_key_items(root):
    path = os.path.join(root, 'scripts/enum/key_item.lua')
    out = {}
    for line in open(path, encoding='utf-8'):
        m = re.match(r"\s*([A-Z][A-Z0-9_]+)\s*=\s*(\d+)", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def parse_quest(path, ids, key_items):
    text = open(path, encoding='utf-8', errors='replace').read()

    m = re.search(r"Quest:new\(\s*xi\.questLog\.(\w+)\s*,\s*xi\.quest\.id\.(\w+)\.([A-Z0-9_]+)", text)
    if not m:
        return None
    log_area, id_area, const = m.groups()
    qid = ids.get(log_area, {}).get(const)
    if qid is None:
        # The id table is keyed by the area *name*; a few files name a different one.
        for area_ids in ids.values():
            if const in area_ids:
                qid = area_ids[const]
                break
    if qid is None:
        return None

    lines = text.splitlines()
    title = lines[1].lstrip('- ').strip() if len(lines) > 1 else const.title()

    # Header comments: "-- Balasiel : !pos -136 -11 64 230".  The first one is where the
    # quest is taken, which is the only coordinate a guide can state without guessing.
    npc = None
    for line in lines[:40]:
        m = re.match(r"--\s*(.+?)\s*:\s*!pos\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)", line)
        if m:
            npc = {
                'name': m.group(1).strip(),
                'x': float(m.group(2)), 'y': float(m.group(3)), 'z': float(m.group(4)),
                'zone': int(m.group(5)),
            }
            break

    reward_ki = None
    m = re.search(r"keyItem\s*=\s*xi\.ki\.([A-Z0-9_]+)", text)
    if m:
        reward_ki = key_items.get(m.group(1))

    level = None
    m = re.search(r"getMainLvl\(\)\s*>=\s*(\d+)", text)
    if m:
        level = int(m.group(1))

    prereq = None
    m = re.search(r"hasCompletedQuest\(\s*xi\.questLog\.(\w+)\s*,\s*xi\.quest\.id\.(\w+)\.([A-Z0-9_]+)", text)
    if m:
        p_log, _, p_const = m.groups()
        p_id = ids.get(p_log, {}).get(p_const)
        if p_id is not None:
            prereq = (AREA_LOG.get(p_log.lower().replace('_', ''), p_log.lower()), p_id)

    return {
        'area': AREA_LOG.get(id_area, id_area.lower()),
        'id': qid,
        'name': title,
        'npc': npc,
        'key_item': reward_ki,
        'level': level,
        'prereq': prereq,
    }


def lua_str(s):
    return "'" + str(s).replace('\\', '\\\\').replace("'", "\\'") + "'"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', help='path to a LandSandBoat server checkout')
    ap.add_argument('-o', '--out', default='Vanaguide/data/quests.lua')
    args = ap.parse_args()

    ids = parse_ids(args.root)
    key_items = parse_key_items(args.root)

    quests, skipped = defaultdict(dict), 0
    qdir = os.path.join(args.root, 'scripts/quests')
    for dirpath, _, files in os.walk(qdir):
        for f in sorted(files):
            if not f.endswith('.lua'):
                continue
            q = parse_quest(os.path.join(dirpath, f), ids, key_items)
            if q is None:
                skipped += 1
                continue
            quests[q['area']][q['id']] = q

    total = sum(len(v) for v in quests.values())
    with_pos = sum(1 for a in quests.values() for q in a.values() if q['npc'])

    with open(args.out, 'w', encoding='utf-8') as fh:
        fh.write("""-- Vanaguide :: data/quests.lua
-- GENERATED by tools/gen_quests.py from a LandSandBoat checkout.  Do not hand-edit.
--
-- Every quest the server code implements, keyed the way the client's quest log keys them,
-- so `Q|area,id|` in a guide and this table are the same numbers.  Fields:
--
--   name    the quest's name
--   zone    where it is taken, and x/z/y there (nil when the script states no position)
--   npc     who to talk to
--   ki      the key item it awards, when it awards one
--   level   the level the script checks for, when it checks one
--   prereq  { area, id } of the quest it requires, when it requires one
--
-- Coordinates and ids are game data.  See docs/QUEST_DATABASE.md.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local Q = {}

""")
        fh.write('Q.quests = {\n')
        for area in sorted(quests):
            fh.write('    %s = {\n' % area)
            for qid in sorted(quests[area]):
                q = quests[area][qid]
                bits = ['name = %s' % lua_str(q['name'])]
                if q['npc']:
                    n = q['npc']
                    bits.append('zone = %d' % n['zone'])
                    bits.append('x = %.1f' % n['x'])
                    bits.append('z = %.1f' % n['z'])
                    bits.append('y = %.1f' % n['y'])
                    bits.append('npc = %s' % lua_str(n['name']))
                if q['key_item']:
                    bits.append('ki = %d' % q['key_item'])
                if q['level']:
                    bits.append('level = %d' % q['level'])
                if q['prereq']:
                    bits.append("prereq = { %s, %d }" % (lua_str(q['prereq'][0]), q['prereq'][1]))
                fh.write('        [%d] = { %s },\n' % (qid, ', '.join(bits)))
            fh.write('    },\n')
        fh.write('}\n\n')
        fh.write("""--- One quest, or nil.
function Q.get(area, id)
    local a = Q.quests[area]
    return a ~= nil and a[id] or nil
end

--- Every quest in an area, sorted by id.
function Q.area(area)
    local out = {}
    for id, q in pairs(Q.quests[area] or {}) do
        out[#out + 1] = { id = id, quest = q }
    end
    table.sort(out, function(a, b) return a.id < b.id end)
    return out
end

return Q
""")

    print('%d quests in %d areas (%d with coordinates); %d files skipped'
          % (total, len(quests), with_pos, skipped))


if __name__ == '__main__':
    sys.exit(main())
