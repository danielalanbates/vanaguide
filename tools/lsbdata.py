#!/usr/bin/env python3
"""Vanaguide :: tools/lsbdata.py

The parts of a LandSandBoat checkout that both generators need.

Quests and missions are written by the same people in the same house style, which is to say
in six house styles. Reading the header of one and the header of the other used to be two
copies of the same regex, and the copy in gen_missions.py knew about one dialect out of six --
so missions lost the NPC that quests had just gained.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import math
import os
import re


def normalize(name):
    return re.sub(r'[^a-z0-9]', '', (name or '').lower())


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


def find_npc(text, lines, title, zone_ids, npc_list, allow_zone_only=False):
    """Who to talk to, and where they stand, from a quest or mission script.

    Six header dialects, then the script's own section tables, then a last pass that lets the
    server's npc_list overrule a position the comment states wrongly. Returns None only when
    the script really does name nobody anywhere.
    """
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

    if npc is not None:
        return npc

    # Nobody to talk to anywhere -- `allow_zone_only` decides whether that is worth a zone.
    # Missions want it: many begin by walking into a place rather than by talking to somebody.
    # Quests do not: a quest with no NPC and no coordinate is a quest with nothing to say, and
    # naming a zone the script happens to mention would be a guess dressed as a fact.
    # Nobody to talk to anywhere -- and for a whole class of missions that is the truth, not a
    # gap. A Crystalline Prophecy begins by *walking into* Lower Jeuno: the section is keyed
    # `[xi.zone.LOWER_JEUNO] = { onZoneIn = ... }` and names no NPC because none is involved.
    # "Go to Lower Jeuno" is still the instruction a guide should give, so the zone is kept
    # even though there is no coordinate to stand on. Twelve ACP missions and most of A
    # Shantotto Ascension are this shape.
    if not allow_zone_only:
        return None

    m = re.search(r"\[\s*xi\.zone\.([A-Z][A-Z0-9_]*)\s*\]\s*=", text)
    zone = (zone_ids or {}).get(m.group(1)) if m else None
    if zone:
        return {'name': '', 'zone': zone, 'x': None, 'y': None, 'z': None, 'zone_only': True}

    return None
