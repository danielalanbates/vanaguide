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
import math
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


def parse_zone_ids(root):
    """scripts/enum/zone.codegen.lua -> {ABYSSEA_ALTEPA: 218}."""
    out = {}
    path = os.path.join(root, 'scripts/enum/zone.codegen.lua')
    if not os.path.exists(path):
        return out
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r"\s*([A-Z][A-Z0-9_]*)\s*=\s*(\d+)", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def parse_npc_list(root):
    """sql/npc_list.sql -> {(zone, normalized name): (x, y, z)}.

    The header comment of a quest script names who to talk to, but only sometimes with a
    `!pos` beside it -- 160 quests, nearly all of them Abyssea dominion ops, name the NPC and
    no position at all. That is not a missing fact, only a missing copy of one: the server
    ships `npc_list.sql`, and the zone is encoded in the id.

        zone = (npcid >> 12) & 0xFFF

    Reading the shipped SQL rather than a live database keeps this a generator: it runs
    against a checkout, with no server up.
    """
    path = os.path.join(root, 'sql/npc_list.sql')
    out = {}
    if not os.path.exists(path):
        return out
    row = re.compile(r"\((\d+),'((?:[^']|\\')*)','((?:[^']|\\')*)',\s*\d+,"
                     r"(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)")
    for line in open(path, encoding='utf-8', errors='replace'):
        if not line.startswith('INSERT'):
            continue
        for m in row.finditer(line):
            npcid = int(m.group(1))
            name = (m.group(3) or m.group(2))
            x, y, z = float(m.group(4)), float(m.group(5)), float(m.group(6))
            if x == 0.0 and y == 0.0 and z == 0.0:
                continue        # placed at runtime; a position of (0,0,0) is not one
            key = ((npcid >> 12) & 0xFFF, re.sub(r'[^a-z0-9]', '', name.lower()))
            out.setdefault(key, (x, y, z))
    return out


def clean_npc_name(raw):
    """Header comments label the name as often as they just state it.

    "NPC: Ayame", "Door: Merchant's House (H-8)", "Ranpi-Monpi (S) -", "qm6 (H-10/Boat)" --
    the label, the map reference in brackets and a trailing dash are all decoration. What is
    left is either a name the server knows or it is not, and that is the useful question.
    """
    name = re.sub(r'^\s*(?:NPC|Door|Marker|QM)\s*:\s*', '', raw, flags=re.I)
    name = name.split(',')[0]
    name = re.sub(r'\s*\([^)]*\)\s*$', '', name)
    # "Glenne - Southern Sandoria": the name, then where to find it.
    name = re.split(r'\s+-\s+', name)[0]
    return name.strip(' -\t')


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
    # Header comments name who to talk to, in three dialects that all mean the same thing:
    #
    #   -- Balasiel : !pos -136 -11 64 230
    #   -- Curilla : !pos: -467.7 -3.5 -769.5 132
    #   -- Ahkk Jharcham, Whitegate , !pos 0.1 -1 -76 50
    #   -- Hadahda !pos -112 -7 -66 50
    #
    # Reading only the first cost 88 quests their NPC. The separator is a colon, a comma or
    # nothing at all, `!pos` may carry a colon of its own, and anything after a comma in the
    # name is the place in words -- "Ahkk Jharcham, Whitegate" is one NPC, not two.
    npc = None
    header_pos = re.compile(r"--\s*(.+?)\s*[,:]?\s*!pos:?\s+"
                            r"(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)")
    candidates = []
    for line in lines[:40]:
        m = header_pos.match(line)
        if m:
            candidates.append({
                'name': clean_npc_name(m.group(1)),
                'x': float(m.group(2)), 'y': float(m.group(3)), 'z': float(m.group(4)),
                'zone': int(m.group(5)),
            })
    # A quest often lists several positions -- the giver, the place it is turned in, a door on
    # the way. The first line is not reliably the giver: several name the town, or a door, and
    # one names "Region". The one whose name the server actually has an NPC for is.
    if candidates:
        npc = next((c for c in candidates if npc_list and
                    (c['zone'], re.sub(r'[^a-z0-9]', '', c['name'].lower())) in npc_list),
                   candidates[0])

    # A fourth dialect gives a position with no zone -- "-- Salimah : !pos -31.7 -6.8 -73.3" --
    # and a fifth gives a zone-less position with no name at all. Both are still usable: the
    # zone is in the script, in its own `xi.zone.X` references.
    script_zones = [zone_ids[z] for z in re.findall(r"xi\.zone\.([A-Z][A-Z0-9_]*)", text)
                    if zone_ids and z in zone_ids]
    if npc is None:
        for line in lines[:40]:
            m = re.match(r"--\s*(.*?)\s*[,:]?\s*!pos:?\s+"
                         r"(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*$", line)
            if m and script_zones:
                name = clean_npc_name(m.group(1))
                if name.lower() == title.lower():
                    name = ''
                # A script mentions several zones -- the one the quest is taken in is the one
                # that actually has this NPC standing in it. Guessing the first mentioned put
                # thirteen quests in the wrong zone.
                key = re.sub(r'[^a-z0-9]', '', name.lower())
                zone = next((z for z in script_zones
                             if npc_list and (z, key) in npc_list), script_zones[0])
                npc = {'name': name,
                       'x': float(m.group(2)), 'y': float(m.group(3)), 'z': float(m.group(4)),
                       'zone': zone}
                break

    # The other header style: the NPC named on its own, with the place in words rather than
    # coordinates -- "-- Dominion Sergeant (Nanaa Mihgo\'s Camp)". Every Abyssea dominion op
    # is written this way, which is why 160 quests came out of the generator with nobody to
    # talk to. The name is enough: the zone comes from the script\'s own `[xi.zone.X]` block
    # and the position from the server\'s npc_list.
    if npc is None and zone_ids and npc_list:
        zones = [zone_ids[z] for z in re.findall(r"xi\.zone\.([A-Z][A-Z0-9_]*)", text)
                 if z in zone_ids]
        header = []
        for line in lines[:12]:
            m = re.match(r"--\s*([A-Z][A-Za-z\'\- ]{2,40}?)\s*(?:\([^)]*\))?\s*$", line)
            if m and not m.group(1).strip().startswith('!'):
                header.append(m.group(1).strip())
        # The title line is a header comment too, and is not an NPC name.
        for name in [h for h in header if h.lower() != title.lower()]:
            key = re.sub(r'[^a-z0-9]', '', name.lower())
            for zone in zones:
                pos = npc_list.get((zone, key))
                if pos:
                    npc = {'name': name, 'x': pos[0], 'y': pos[1], 'z': pos[2], 'zone': zone}
                    break
            if npc:
                break

    # Last resort, and the most reliable of the lot when it fires: a quest's sections are keyed
    # by the NPC they belong to -- `[xi.zone.LOWER_JEUNO] = { ['Chalvatot'] = { onTrigger ...`.
    # A quest whose header says nothing at all still says this, and so does one whose header
    # names the town rather than the person ("Mhaura", "Chateau d'Oraguille") -- which reads as
    # an NPC the server has never heard of, and is really the parse missing the point.
    unresolved = (npc is not None and npc_list is not None and npc['name'] and
                  (npc['zone'], re.sub(r'[^a-z0-9]', '', npc['name'].lower())) not in npc_list)
    if (npc is None or unresolved) and zone_ids and npc_list:
        for m in re.finditer(r"\[\s*xi\.zone\.([A-Z][A-Z0-9_]*)\s*\]\s*=\s*\{(.{0,4000}?)\n\s*\}",
                             text, re.S):
            zone = zone_ids.get(m.group(1))
            if zone is None:
                continue
            for n in re.finditer(r"\[\s*'([^']{2,40})'\s*\]\s*=", m.group(2)):
                name = n.group(1)
                pos = npc_list.get((zone, re.sub(r'[^a-z0-9]', '', name.lower())))
                if pos:
                    found = {'name': name, 'x': pos[0], 'y': pos[1], 'z': pos[2],
                             'zone': zone}
                    break
            else:
                continue
            break
        else:
            found = None
        if found:
            npc = found

    # The header comment and npc_list can disagree, and when they do the server wins: the
    # comment is prose somebody typed, npc_list is what the server actually spawns. Nine
    # quests are affected, one of them by 1540 yalms -- "An Eye for Revenge" has Curilla's z
    # written -769.5 where the server puts her at +770.2, a sign typed wrong once and copied
    # since. Disagreements under ten yalms are left alone; they are the same spot.
    if npc and npc_list and npc['name']:
        pos = npc_list.get((npc['zone'], re.sub(r'[^a-z0-9]', '', npc['name'].lower())))
        if pos and math.hypot(pos[0] - npc['x'], pos[2] - npc['z']) > 10.0:
            npc = dict(npc, x=pos[0], y=pos[1], z=pos[2], from_server=True)

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
    zone_ids = parse_zone_ids(args.root)
    npc_list = parse_npc_list(args.root)

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
