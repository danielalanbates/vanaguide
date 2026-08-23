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

import lsbdata

AREA_LOG = {
    'sandoria': 'sandoria', 'bastok': 'bastok', 'windurst': 'windurst',
    'jeuno': 'jeuno', 'otherAreas': 'other', 'outlands': 'outlands',
    'ahtUrhgan': 'ahturhgan', 'crystalWar': 'wotg', 'abyssea': 'abyssea',
    'adoulin': 'adoulin', 'coalition': 'coalition',
}

# A quest states its own area as the directory name (`crystalWar`) and its prerequisite's as
# the questLog constant (`CRYSTAL_WAR`). Squashing case and underscores makes them the same
# key -- without it, every cross-referenced prerequisite in Aht Urhgan, the Crystal War and
# "other areas" pointed at an area that does not exist, and 44 of the 48 dangling
# prerequisites in the database were this one line.
AREA_ANY = {k.lower().replace('_', ''): v for k, v in AREA_LOG.items()}


def area_key(name):
    flat = (name or '').lower().replace('_', '')
    return AREA_ANY.get(flat, flat)


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


def parse_items(root):
    """scripts/enum/item.lua -> {NAME: id}, so a quest's `item = xi.item.HORN_RING` reward
    becomes something the gear finder can point at."""
    out = {}
    path = os.path.join(root, 'scripts/enum/item.lua')
    if not os.path.exists(path):
        return out
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r"\s*([A-Z][A-Z0-9_]*)\s*=\s*(\d+)", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def parse_quest(path, ids, key_items, item_ids, zone_ids=None, npc_list=None):
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
    npc = lsbdata.find_npc(text, lines, title, zone_ids, npc_list)

    reward_ki = None
    m = re.search(r"keyItem\s*=\s*xi\.ki\.([A-Z0-9_]+)", text)
    if m:
        reward_ki = key_items.get(m.group(1))

    # Reward items: `item = xi.item.HORN_RING`, or a list of them. These are the other half of
    # "where does this gear come from" -- a quest reward is a source you can be routed to, and
    # nothing drops or sells it.
    reward_items = []
    for m in re.finditer(r"item\s*=\s*xi\.item\.([A-Z0-9_]+)", text):
        iid = item_ids.get(m.group(1))
        if iid is not None and iid not in reward_items:
            reward_items.append(iid)
    for m in re.finditer(r"item\s*=\s*\{([^}]*)\}", text):
        for n in re.finditer(r"xi\.item\.([A-Z0-9_]+)", m.group(1)):
            iid = item_ids.get(n.group(1))
            if iid is not None and iid not in reward_items:
                reward_items.append(iid)

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
            prereq = (area_key(p_log), p_id)

    return {
        'area': area_key(id_area),
        'id': qid,
        'name': title,
        'npc': npc,
        'key_item': reward_ki,
        'items': reward_items,
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
    item_ids = parse_items(args.root)
    zone_ids = lsbdata.parse_zone_ids(args.root)
    npc_list = lsbdata.parse_npc_list(args.root)

    quests, skipped = defaultdict(dict), 0
    qdir = os.path.join(args.root, 'scripts/quests')
    for dirpath, _, files in os.walk(qdir):
        for f in sorted(files):
            if not f.endswith('.lua'):
                continue
            q = parse_quest(os.path.join(dirpath, f), ids, key_items, item_ids,
                            zone_ids, npc_list)
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
                if q['items']:
                    bits.append('rewards = { %s }' % ', '.join(str(i) for i in q['items']))
                fh.write('        [%d] = { %s },\n' % (qid, ', '.join(bits)))
            fh.write('    },\n')
        fh.write('}\n\n')
        fh.write("""--- One quest, or nil.
function Q.get(area, id)
    local a = Q.quests[area]
    return a ~= nil and a[id] or nil
end

--- Which quests award this item?  Returns { area, id, quest } for each.
function Q.awarding(item_id)
    local out = {}
    for area, quests in pairs(Q.quests) do
        for id, q in pairs(quests) do
            for _, r in ipairs(q.rewards or {}) do
                if r == item_id then out[#out + 1] = { area = area, id = id, quest = q } end
            end
        end
    end
    return out
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

    rewarded = sum(1 for a in quests.values() for q in a.values() if q['items'])
    print('%d quests in %d areas (%d with coordinates, %d awarding an item); %d files skipped'
          % (total, len(quests), with_pos, rewarded, skipped))


if __name__ == '__main__':
    sys.exit(main())
