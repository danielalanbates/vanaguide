#!/usr/bin/env python3
"""Vanaguide :: tools/lsbtravel.py

Every way the server moves a player between zones that is not a zone line.

`sql/zonelines.sql` is the doorways and `sql/transport.sql` is the ferries and airships, and
with only those two the router could not reach 169 of the 376 zone changes the shipped guides
ask for. The rest of the map is joined by things a player talks to or steps into, and every
one of them is an NPC script that ends an event in `setPos(x, y, z, rot, zone)`:

  * Cavernous Maws -- the Wings of the Goddess maws between a zone and its [S] twin
    (scripts/globals/maws.lua) and the Abyssea maws (scripts/globals/abyssea.lua).  The only
    way into any Crystal War or Abyssea zone.
  * Waypoints -- the Adoulin teleport network (scripts/globals/waypoint.lua), including the
    one in Lower Jeuno that is the only way to Adoulin.
  * Home Points (scripts/globals/homepoint.lua) -- the only way back to Tavnazia once the
    Chains of Promathia cutscene that first took you there is over.
  * A short, named list of doors and transporters: the Cermet Gates to the Promyvions, the
    Dimensional Portals to Al'Taieu, the Celennia Memorial Library door, the Liseran Doors and
    the Vertical Transit Devices of Ra'Kaznar, and so on.

Which NPC does what is read from the zone's own npcs/ directory -- a zone has a maw when it
has an NPC script that calls the maw handler -- and where to stand is that NPC's row in
`sql/npc_list.sql`. Nothing here is typed in from memory; the one thing that is chosen by hand
is which one-off NPC warps count as travel (EVENT_WARPS below), because a quest NPC that
teleports you once in a cutscene is not a road.

Both generators use this: gen_zonelines.py for the edges, gen_zonepoints.py for the spot.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import os
import re

from lsbdata import normalize, parse_npc_list, parse_zone_ids

# Seconds the router charges.  A maw, a waypoint or a door is a short cutscene; a Home Point
# warp is as quick, but it only works if the player has touched a Home Point in the zone they
# are going to, which no table can know -- so it is priced as a last resort, the way round
# when there is no other, and never a shortcut past a road that exists.
COST_EVENT = 120
COST_HOMEPOINT = 1800
# A crossing that needs a point in a storyline most players on a given route will not have
# reached is priced the same way: offered when nothing else reaches the place, never as a
# shortcut past a road.  At 120, the crags' Shattered Telepoints (CoP 1-2 and 1-3 only) cut
# through the Hall of Transference, and the Dimensional Portals (after CoP 7-5) through
# Al'Taieu, on Whitegate-to-Bastok routes that have nothing to do with Chains of Promathia.
COST_GATED = 1800

NUM = r'-?\d+(?:\.\d+)?'
ZONE_TOKEN = r'(xi\.zone\.[A-Z0-9_]+|\d+)'
DEST = re.compile(r'\{\s*(%s)\s*,\s*(%s)\s*,\s*(%s)\s*,\s*%s\s*,\s*%s\s*\}'
                  % (NUM, NUM, NUM, NUM, ZONE_TOKEN))
KEYED = re.compile(r'^\s*\[\s*xi\.zone\.([A-Z0-9_]+)\s*\]\s*=\s*\{(.*)$')
SETPOS = re.compile(r'setPos\(\s*%s\s*,\s*%s\s*,\s*%s\s*,\s*%s\s*,\s*%s\s*\)'
                    % (NUM, NUM, NUM, NUM, ZONE_TOKEN))
AREA = re.compile(r'register(Cuboid|Cylindrical|Spherical)TriggerArea\(\s*(\d+)\s*,([^)]*)\)')
ZONE_NAME = re.compile(r"\((\d+),\d+,'[^']*',\d+,'([^']*)'")

# One-off NPC warps that are travel, not a quest's cutscene: (zone script directory, script,
# condition the player must meet or None[, cost]).  The destination is read from the script's
# own setPos; the position from npc_list.  `Zone.lua#N` is trigger area N of the zone script.
EVENT_WARPS = [
    ('Hall_of_Transference', 'npcs/_0e0.lua', 'Chains of Promathia 1-2 or later'),
    ('Hall_of_Transference', 'npcs/_0e1.lua', 'Chains of Promathia 1-2 or later'),
    ('Hall_of_Transference', 'npcs/_0e2.lua', 'Chains of Promathia 1-2 or later'),
    ('Spire_of_Holla', 'npcs/Radiant_Aureole.lua', None),
    ('Spire_of_Dem', 'npcs/Radiant_Aureole.lua', None),
    ('Spire_of_Mea', 'npcs/Radiant_Aureole.lua', None),
    ('Spire_of_Vahzl', 'npcs/Radiant_Aureole.lua', None),
    ('La_Theine_Plateau', 'npcs/Dimensional_Portal.lua', 'after Chains of Promathia 7-5',
     COST_GATED),
    ('Konschtat_Highlands', 'npcs/Dimensional_Portal.lua', 'after Chains of Promathia 7-5',
     COST_GATED),
    ('Tahrongi_Canyon', 'npcs/Dimensional_Portal.lua', 'after Chains of Promathia 7-5',
     COST_GATED),
    ('AlTaieu', 'npcs/Dimensional_Portal.lua', None),
    ('Grand_Palace_of_HuXzoi', 'npcs/_iya.lua', None),
    ('The_Garden_of_RuHmet', 'npcs/_0zs.lua', 'after Chains of Promathia 8-3'),
    ('Lower_Delkfutts_Tower', 'npcs/Cermet_Door.lua', None),
    ('Upper_Delkfutts_Tower', 'npcs/_4e1.lua', None),
    ('Qufim_Island', 'npcs/Transcendental_Radiance.lua',
     'Abyssea: Beneath a Blood Red Sky, and a Traverser Stone'),
    ('Eastern_Adoulin', 'npcs/Eppel-Treppel.lua', None),
    ('Celennia_Memorial_Library', 'npcs/Door_Back_to_Town.lua', None),
    ('Kamihr_Drifts', 'npcs/Liseran_Door_Entrance.lua', None),
    ('Outer_RaKaznar', 'npcs/Liseran_Door_Exit.lua', None),
    ('Outer_RaKaznar', 'npcs/Vertical_Transit_Device_7.lua', None),
    ('RaKaznar_Inner_Court', 'npcs/Vertical_Transit_Device_1.lua', None),
    ('RaKaznar_Inner_Court', 'npcs/Vertical_Transit_Device_2.lua', None),
    ('RaKaznar_Turris', 'Zone.lua#1', None),
]


def pretty(name):
    """zone_settings name -> what a player reads: `Port_San_dOria` -> `Port San d'Oria`.

    The SQL drops the apostrophe and capitalises what followed it, so a lower-to-upper
    boundary puts it back -- the same rule tools/gen_zones.py uses for data/zone_names.lua.
    """
    return re.sub(r'([a-z])([A-Z])', r"\1'\2", name.replace('_', ' '))


def zone_settings(root):
    """sql/zone_settings.sql -> ({id: display name}, {script directory: id})."""
    names, dirs = {}, {}
    path = os.path.join(root, 'sql/zone_settings.sql')
    if not os.path.exists(path):
        return names, dirs
    for line in open(path, encoding='utf-8', errors='replace'):
        if line.startswith('INSERT'):
            for m in ZONE_NAME.finditer(line):
                names[int(m.group(1))] = pretty(m.group(2))
                dirs[m.group(2)] = int(m.group(1))
    return names, dirs


def zone_of(token, ids):
    if token.startswith('xi.zone.'):
        return ids.get(token[len('xi.zone.'):])
    return int(token)


def read(root, rel):
    path = os.path.join(root, rel)
    if not os.path.exists(path):
        return None
    return open(path, encoding='utf-8', errors='replace').read()


def table_rows(text, start):
    """(line number, line) for each line of the Lua table that opens with `start`."""
    if text is None:
        return []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if line.startswith(start):
            out = []
            for j in range(i + 1, len(lines)):
                if lines[j].rstrip() == '}':
                    break
                out.append((j + 1, lines[j]))
            return out
    return []


def keyed_dests(root, rel, start, ids):
    """`[xi.zone.FROM] = { ... { x, y, z, rot, TO } }` rows -> {from: (to, 'file:line')}."""
    out = {}
    for n, line in table_rows(read(root, rel), start):
        k = KEYED.match(line)
        d = DEST.search(line)
        if k and d and k.group(1) in ids:
            to = zone_of(d.group(4), ids)
            if to is not None:
                out[ids[k.group(1)]] = (to, '%s:%d' % (rel, n))
    return out


def npc_spots(npcs, zone, internal):
    """Where an NPC stands, as (x, z, y) with the height last; [] if npc_list has no row."""
    spots = []
    for x, y, z, _ in npcs.by_internal.get((zone, normalize(internal)), []):
        if (x, z, y) not in spots:
            spots.append((x, z, y))
    return spots


def npc_label(npcs, zone, internal):
    rows = npcs.by_internal.get((zone, normalize(internal)), [])
    if rows and rows[0][3] and not rows[0][3].startswith('_'):
        return rows[0][3]
    return internal.replace('_', ' ')


def area_spot(text, area):
    """Trigger area `area` of a Zone.lua -> ((x, z, y) of its middle, its comment's first
    sentence as a label), or (None, None)."""
    for line in text.split('\n'):
        m = AREA.search(line)
        if m is None or int(m.group(2)) != area:
            continue
        label = line.split('--', 1)[1].split('.')[0].strip() if '--' in line else None
        nums = [float(v) for v in re.findall(NUM, m.group(3))]
        if m.group(1) == 'Cuboid' and len(nums) >= 6:
            x1, y1, z1, x2, y2, z2 = nums[:6]
            return ((x1 + x2) / 2, (z1 + z2) / 2, (y1 + y2) / 2), label
        if m.group(1) == 'Spherical' and len(nums) >= 3:
            return (nums[0], nums[2], nums[1]), label
        if len(nums) >= 2:
            return (nums[0], nums[1], 0.0), label
    return None, None


def npc_scripts(root, dirs):
    """(zone, script directory, file name, text) for every NPC script with a zone id."""
    zdir = os.path.join(root, 'scripts', 'zones')
    for d in sorted(os.listdir(zdir)):
        zone = dirs.get(d)
        ndir = os.path.join(zdir, d, 'npcs')
        if zone is None or not os.path.isdir(ndir):
            continue
        for f in sorted(os.listdir(ndir)):
            if f.endswith('.lua'):
                yield zone, d, f, open(os.path.join(ndir, f), encoding='utf-8',
                                       errors='replace').read()


def handler_spots(scripts, npcs, handler):
    """{zone: [spots]} for every NPC whose script calls `handler`, e.g. xi.homepoint.onTrigger."""
    out = {}
    for zone, _, f, text in scripts:
        if handler in text:
            spots = out.setdefault(zone, [])
            for s in npc_spots(npcs, zone, f[:-4]):
                if s not in spots:
                    spots.append(s)
    return out


def edge(frm, to, via, cost, evidence, spots=(), net=None):
    """`cost` is what the router charges; `time` is what the window says it takes.  They
    differ only for the last-resort crossings, which are a short cutscene like the rest."""
    return {'from': frm, 'to': to, 'via': via, 'cost': cost, 'time': min(cost, COST_EVENT),
            'evidence': evidence, 'spots': list(spots), 'net': net}


def maws(root, ids, names, npcs, scripts):
    """Cavernous Maws: a zone has one when an NPC script there calls the maw handler."""
    tables = {
        'xi.maws.onTrigger': (keyed_dests(root, 'scripts/globals/maws.lua',
                                          'local pastMaws =', ids),
                              'Wings of the Goddess; the maw must be opened first'),
        'xi.abyssea.entranceMawOnTrigger': (keyed_dests(root, 'scripts/globals/abyssea.lua',
                                                        'local abysseaEntranceMawData =', ids),
                                            'Abyssea; level 30 or higher'),
        'xi.abyssea.exitMawOnTrigger': (keyed_dests(root, 'scripts/globals/abyssea.lua',
                                                    'local abysseaExitMawData =', ids), None),
    }
    out = []
    for zone, d, f, text in scripts:
        for handler, (dests, note) in tables.items():
            if handler in text and zone in dests:
                to, evidence = dests[zone]
                stem = f[:-4]
                via = '%s in %s to %s' % (npc_label(npcs, zone, stem), names.get(zone, zone),
                                          names.get(to, to))
                if note:
                    via += ' (%s)' % note
                out.append(edge(zone, to, via, COST_EVENT,
                                'scripts/zones/%s/npcs/%s + %s' % (d, f, evidence),
                                npc_spots(npcs, zone, stem)))
    return out


def shattered_telepoints(root, ids, names, npcs):
    """The crags' Shattered Telepoints -> Hall of Transference, during CoP 1-2 and 1-3 only."""
    out = []
    rel = 'scripts/missions/cop/helpers.lua'
    for zone, (to, evidence) in sorted(keyed_dests(
            root, rel, 'xi.cop.helpers.shatteredTelepointInfo =', ids).items()):
        via = 'Shattered Telepoint in %s to %s (only during Chains of Promathia 1-2 and 1-3)' \
            % (names.get(zone, zone), names.get(to, to))
        out.append(edge(zone, to, via, COST_GATED, evidence,
                        npc_spots(npcs, zone, 'Shattered_Telepoint')))
    return out


def waypoints(root, ids, names, stations):
    """The Adoulin waypoint network, with the two routing rules waypoint.lua enforces.

    Groups 1-2 are the two Adoulin cities, 3-9 the frontier, 10 Lower Jeuno, 11 the Enigmatic
    Devices.  Lower Jeuno reaches only the cities; a frontier waypoint is only a destination
    from a city.  Warp runes (the one-way destinations with no group) need a key item each and
    are left out.  `stations` is the zones that have a Waypoint NPC.
    """
    rel = 'scripts/globals/waypoint.lua'
    text = read(root, rel)
    if text is None:
        return []
    group_zones = {}
    info = re.compile(r'^\s*\[\s*\d+\s*\]\s*=\s*\{\s*(?:\d+|nil)\s*,\s*(\d+)\s*,')
    for _, line in table_rows(text, 'local waypointInfo ='):
        m, d = info.match(line), DEST.search(line)
        if m and d:
            group_zones.setdefault(int(m.group(1)), set()).add(zone_of(d.group(4), ids))
    marks = [n + 1 for n, line in enumerate(text.split('\n'))
             if line.startswith('local waypointInfo =')
             or 'Field destinations only reachable' in line
             or 'Lower Jeuno can only reach' in line]
    evidence = '%s:%s (destinations, then the two rules)' % (
        rel, ','.join(str(n) for n in marks))
    zone_group = {}
    for g, zones in group_zones.items():
        if g in (1, 2, 10) or 3 <= g <= 9:
            for z in zones:
                zone_group[z] = g

    def allowed(sg, dg):
        if sg == 10 and dg not in (1, 2):
            return False
        if 3 <= dg <= 9 and sg not in (1, 2):
            return False
        return True

    out, seen = [], set()
    for src in sorted(stations):
        sg = zone_group.get(src)
        if sg is None:
            continue
        for dg in sorted(group_zones):
            if not allowed(sg, dg):
                continue
            for dst in sorted(group_zones[dg]):
                if dst == src or (src, dst) in seen:
                    continue
                seen.add((src, dst))
                if src == ids.get('LOWER_JEUNO'):
                    note = 'the Adoulin waypoint must be attuned'
                elif dg == 10:
                    note = 'kinetic units'          # Jeuno's is always active
                elif dg == 11:
                    note = 'kinetic units; the Enigmatic Device must be unlocked'
                else:
                    note = 'kinetic units; the waypoint there must be attuned'
                via = 'Waypoint in %s to %s (%s)' % (names.get(src, src),
                                                      names.get(dst, dst), note)
                out.append(edge(src, dst, via, COST_EVENT, evidence, net='waypoint'))
    return out


def homepoint_evidence(root):
    setting = 'settings/default/main.lua'
    text = read(root, setting) or ''
    n = [i for i, line in enumerate(text.split('\n'), 1) if 'HOMEPOINT_TELEPORT' in line]
    return 'scripts/globals/homepoint.lua (goToHP) + %s:%d' % (setting, n[0] if n else 0)


def event_warps(root, ids, names, dirs, npcs):
    out, missing = [], []
    for d, script, note, *cost in EVENT_WARPS:
        cost = cost[0] if cost else COST_EVENT
        zone = dirs.get(d)
        path, _, area = script.partition('#')
        rel = 'scripts/zones/%s/%s' % (d, path)
        text = read(root, rel)
        if zone is None or text is None:
            missing.append(rel)
            continue
        dests = []
        for n, line in enumerate(text.split('\n'), 1):
            for m in SETPOS.finditer(line):
                to = zone_of(m.group(1), ids)
                if to is not None and to != zone and to not in [t for t, _ in dests]:
                    dests.append((to, '%s:%d' % (rel, n)))
        if not dests:
            missing.append(rel)
            continue
        if area:
            spot, label = area_spot(text, int(area))
            spots = [spot] if spot else []
            label = label or 'The way out'
        else:
            stem = os.path.basename(path)[:-4]
            spots = npc_spots(npcs, zone, stem)
            label = npc_label(npcs, zone, stem)
        # One script, several destinations (Al'Taieu's three portals): which spot goes where
        # is decided by the NPC's id at runtime, so no spot is given rather than a wrong one.
        if len(dests) > 1:
            spots = []
        for to, evidence in dests:
            via = '%s in %s to %s' % (label, names.get(zone, zone), names.get(to, to))
            if note:
                via += ' (%s)' % note
            out.append(edge(zone, to, via, cost, evidence, spots))
    return out, missing


def collect(root):
    """Everything above, for a checkout.  Returns a dict the generators format."""
    ids = parse_zone_ids(root)
    names, dirs = zone_settings(root)
    npcs = parse_npc_list(root)
    scripts = list(npc_scripts(root, dirs))
    warps, missing = event_warps(root, ids, names, dirs, npcs)
    hp = handler_spots(scripts, npcs, 'xi.homepoint.onTrigger')
    wp = handler_spots(scripts, npcs, 'xi.waypoint.onTrigger')
    edges = (maws(root, ids, names, npcs, scripts) + shattered_telepoints(root, ids, names, npcs)
             + waypoints(root, ids, names, wp) + warps)
    return {
        'edges': edges,
        'names': names,
        'nets': {'waypoint': wp, 'homepoint': hp},
        'homepoint': {'zones': sorted(hp), 'cost': COST_HOMEPOINT, 'time': COST_EVENT,
                      'evidence': homepoint_evidence(root)},
        'missing': missing,
    }
