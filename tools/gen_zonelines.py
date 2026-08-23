#!/usr/bin/env python3
"""Vanaguide :: tools/gen_zonelines.py

Build the walk graph from the server's own zone lines.

`data/travel.lua` says, in a comment, that no server project publishes a table of zone lines
and that guessing one is worse than not having it. The first half was wrong: LandSandBoat
ships `sql/zonelines.sql`, 484 directed pairs across 198 zones — every doorway, cave mouth and
city gate the server will move a player through, with the position it drops them at.

The consequence of not using it was not subtle. The hand-written seed graph covers the base
world, so the router could not reach Aht Urhgan Whitegate (41 quests), any Abyssea zone, or
any of the Crystal War cities — 180 quests in 38 zones, routable only after the player had
already walked there once and the graph had learned the edge.

The learning stays: this is a seed, players find shortcuts a table does not have, and a
server with custom zones will differ. But nobody should have to discover Whitegate on foot
before the guide will route them to it.

    tools/gen_zonelines.py <path to a LandSandBoat checkout> [-o Vanaguide/data/zonelines.lua]

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import os
import re
import sys

ROW = re.compile(r"\((\d+),(\d+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),(\d+),")
TRANSPORT = re.compile(r"\((\d+),'([^']+)',(\d+),")
ZONE_NAME = re.compile(r"\((\d+),\d+,'[^']*',\d+,'([^']*)'")


def lua_str(s):
    return "'" + s.replace('\\', '\\\\').replace("'", "\\'") + "'"


def parse_zone_names(root):
    """sql/zone_settings.sql -> {id: 'Aht Urhgan Whitegate'}."""
    out = {}
    path = os.path.join(root, 'sql/zone_settings.sql')
    if not os.path.exists(path):
        return out
    for line in open(path, encoding='utf-8', errors='replace'):
        if line.startswith('INSERT'):
            for m in ZONE_NAME.finditer(line):
                out[int(m.group(1))] = m.group(2).replace('_', ' ')
    return out


def parse_transport(root, names):
    """sql/transport.sql -> the ferries and airships, as edges between zones.

    A zone line is a doorway; a transport is a thing you board and wait for, and the router
    needs both or half the world is a separate island. The base world and Aht Urhgan share no
    doorway at all -- the only way across is the Mhaura ferry -- so without this, 171 quests
    sit in zones no route can reach from a starting city.

    The table gives the zone each route departs from, and its name gives both ends:
    `Mhaura-Whitegate_Boat` and `Whitegate-Mhaura_Boat`. Pairing a route with its mirror image
    yields the destination exactly, with no guessing at what "Sandoria" means -- which matters,
    because it means Port San d'Oria, not the city.
    """
    path = os.path.join(root, 'sql/transport.sql')
    if not os.path.exists(path):
        return []
    routes = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        if not line.startswith('INSERT'):
            continue
        for m in TRANSPORT.finditer(line):
            name, zone = m.group(2), (int(m.group(3)) >> 12) & 0xFFF
            routes[name] = zone

    edges, seen = [], set()
    for name, zone in sorted(routes.items()):
        bits = name.split('_')
        if len(bits) < 2 or '-' not in bits[0]:
            continue                        # barges and manaclips: one zone, no crossing
        a, b = bits[0].split('-', 1)
        kind = bits[-1]
        mirror = routes.get('%s-%s_%s' % (b, a, '_'.join(bits[1:])))
        if mirror is None or mirror == zone:
            continue
        key = (min(zone, mirror), max(zone, mirror))
        if key in seen:
            continue
        seen.add(key)
        edges.append((zone, mirror, kind.replace('_', ' ')))
    return edges


def parse(path):
    """zonelineid, from_zone, from x/y/z, to_zone, ... -> the set of connected pairs.

    Direction is dropped on purpose. A zone line is one-way in the data because each side is
    its own row, and the router wants "these two zones touch"; where a passage really is
    one-way the missing return trip is a walk the player cannot make anyway, and the graph
    learns the truth the first time they cross it.
    """
    pairs, zones = set(), set()
    for line in open(path, encoding='utf-8', errors='replace'):
        if not line.startswith('INSERT'):
            continue
        for m in ROW.finditer(line):
            a, b = int(m.group(2)), int(m.group(6))
            if a == b or a == 0 or b == 0:
                continue
            zones.add(a)
            zones.add(b)
            pairs.add((min(a, b), max(a, b)))
    return sorted(pairs), zones


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', help='a LandSandBoat checkout')
    ap.add_argument('-o', '--out', default='Vanaguide/data/zonelines.lua')
    args = ap.parse_args()

    path = os.path.join(args.root, 'sql/zonelines.sql')
    if not os.path.exists(path):
        sys.exit('no sql/zonelines.sql under ' + args.root)
    pairs, zones = parse(path)
    names = parse_zone_names(args.root)
    transit = parse_transport(args.root, names)

    out = ['-- Vanaguide :: data/zonelines.lua',
           '-- GENERATED by tools/gen_zonelines.py from a LandSandBoat checkout.  Do not',
           '-- hand-edit.',
           '--',
           '-- Every pair of zones the server will walk a player between, from sql/zonelines.sql.',
           '-- Zone ids and the fact that two zones touch are game facts, not authored content.',
           '--',
           '-- data/travel.lua holds the other half -- airships, ferries, teleports -- which is',
           '-- hand-written because it carries what to TELL the player, and a table of zone',
           '-- lines cannot say "take the airship to Jeuno".',
           '--',
           '-- Copyright (c) 2026 Bates LLC.  All rights reserved.',
           '',
           'local Z = {}',
           '',
           'Z.walk = {']
    line = '   '
    for a, b in pairs:
        piece = ' { %d, %d },' % (a, b)
        if len(line) + len(piece) > 96:
            out.append(line)
            line = '   '
        line += piece
    if line.strip():
        out.append(line)
    out += ['}', '']
    out += ['-- Ferries and airships: boarded and waited for, not walked through. Without',
            '-- these the base world and Aht Urhgan share no connection at all -- the Mhaura',
            '-- ferry is the only crossing -- and a third of the quest zones are unreachable.',
            '-- The cost is the seconds a router should treat the trip as; the real wait',
            '-- varies with the ship\'s schedule and is not knowable from a table.',
            'Z.transit = {']
    for a, b, kind in transit:
        # Each direction gets its own sentence: the guide window prints this verbatim, and
        # "Boat from Mhaura to Aht Urhgan Whitegate" is wrong half the time if it is shared.
        for src, dst in ((a, b), (b, a)):
            via = '%s from %s to %s' % (kind, names.get(src, str(src)),
                                        names.get(dst, str(dst)))
            out.append("    { from = %d, to = %d, cost = 300, kind = 'transit', via = %s },"
                       % (src, dst, lua_str(via)))
    out += ['}', '', 'return Z', '']

    open(args.out, 'w', encoding='utf-8').write('\n'.join(out))
    print(f'{len(pairs)} zone lines across {len(zones)} zones, '
          f'{len(transit)} ferry/airship crossings -> {args.out}')


if __name__ == '__main__':
    sys.exit(main())
