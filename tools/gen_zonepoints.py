#!/usr/bin/env python3
"""Vanaguide :: tools/gen_zonepoints.py

Where, inside the zone you are standing in, is the way out?

`data/zonelines.lua` answers "do these two zones touch", which is enough to plan a route and
not enough to walk one.  The router could say *"Zone into La Theine Plateau"* and then leave
the arrow with nothing to point at, so the guide went quiet for the entire length of every
journey -- the exact stretch a guide is for.

`sql/zonelines.sql` has the missing half and always did.  Every row carries **both** ends:

    zonelineid, from_zone, from_pos_x, from_pos_y, from_pos_z,
                to_zone,   to_pos_x,   to_pos_y,   to_pos_z, ...

`from_pos` is the trigger's position *in the zone you are leaving*.  All 844 rows have one --
none are zero -- so for any leg of a route there is a real coordinate to walk to.  A pair of
zones can have several (Southern San d'Oria has more than one gate onto the same road); they
are all kept, and the router picks whichever is nearest the player rather than guessing.

`sql/transport.sql` does the same for the things you board: `dock_x/y/z` is where you stand
to wait, in the zone the route departs from.

Both files ship with LandSandBoat, which is GPL-3.0, so this reads a checkout the user
already has rather than vendoring anything: the same shape as tools/gen_zonelines.py.

    tools/gen_zonepoints.py <path to a LandSandBoat checkout> [-o Vanaguide/data/zonepoints.lua]

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import os
import re
import sys

# zonelineid, from_zone, from x/y/z, to_zone, to x/y/z -- the first nine columns of a row.
ROW = re.compile(
    r"\((\d+),(\d+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),"
    r"(\d+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),")

# id, name, transport, door, dock x/y/z -- the first seven columns of a transport row.
TRANSPORT = re.compile(
    r"\((\d+),'([^']+)',(\d+),(\d+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+),")


def lua_str(s):
    return "'" + s.replace('\\', '\\\\').replace("'", "\\'") + "'"


def parse_zonelines(path):
    """-> {from_zone: [(to_zone, x, z, y), ...]}, in *guide* axis order.

    LandSandBoat writes a position as (x, y, z) with **y** the height.  Every coordinate in
    this project is written (x, z, y) -- the two horizontal numbers first, height last --
    because that is the order Ashita hands them over in and the order the guide files use
    (core/util.lua says so at the top).  The swap happens here, once, rather than in four
    places at runtime.
    """
    exits = {}
    seen = set()
    text = open(path, encoding='utf-8', errors='replace').read()
    for m in ROW.finditer(text):
        a, b = int(m.group(2)), int(m.group(6))
        if a == b or a == 0 or b == 0:
            continue
        x, y, z = float(m.group(3)), float(m.group(4)), float(m.group(5))
        # A handful of rows repeat a coordinate exactly; the duplicate would only make the
        # router compare the same point twice.
        key = (a, b, round(x, 1), round(z, 1))
        if key in seen:
            continue
        seen.add(key)
        exits.setdefault(a, []).append((b, x, z, y))
    return exits


def parse_zone_names(root):
    out = {}
    path = os.path.join(root, 'sql/zone_settings.sql')
    if not os.path.exists(path):
        return out
    pat = re.compile(r"\((\d+),\d+,'[^']*',\d+,'([^']*)'")
    for line in open(path, encoding='utf-8', errors='replace'):
        if line.startswith('INSERT'):
            for m in pat.finditer(line):
                out[int(m.group(1))] = m.group(2).replace('_', ' ')
    return out


def parse_docks(root, names):
    """-> {(from_zone, to_zone): (x, z, y, via)} -- where you wait for the boat or airship.

    The departure zone is not a column: it is packed into `transport`, the ship's own entity
    id, as bits 12..23 -- the same way every FFXI entity id carries its zone.  The
    destination comes from the route's *name*, paired with its mirror image
    (`Mhaura-Whitegate_Boat` <-> `Whitegate-Mhaura_Boat`), because the words in the name are
    not zone names: "Sandoria" there means Port San d'Oria, and only the mirror row says so.
    """
    path = os.path.join(root, 'sql/transport.sql')
    if not os.path.exists(path):
        return {}
    routes = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        if not line.startswith('INSERT'):
            continue
        for m in TRANSPORT.finditer(line):
            name = m.group(2)
            zone = (int(m.group(3)) >> 12) & 0xFFF
            routes[name] = (zone, float(m.group(5)), float(m.group(6)), float(m.group(7)))

    docks = {}
    for name, (zone, x, y, z) in sorted(routes.items()):
        bits = name.split('_')
        if len(bits) < 2 or '-' not in bits[0]:
            continue                      # barges and manaclips: one zone, no crossing
        a, b = bits[0].split('-', 1)
        kind = bits[-1].replace('_', ' ')
        mirror = routes.get('%s-%s_%s' % (b, a, '_'.join(bits[1:])))
        if mirror is None or mirror[0] == zone:
            continue
        via = '%s from %s to %s' % (kind, names.get(zone, str(zone)),
                                    names.get(mirror[0], str(mirror[0])))
        docks[(zone, mirror[0])] = (x, z, y, via)
    return docks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', help='a LandSandBoat checkout')
    ap.add_argument('-o', '--out', default='Vanaguide/data/zonepoints.lua')
    args = ap.parse_args()

    src = os.path.join(args.root, 'sql/zonelines.sql')
    if not os.path.exists(src):
        sys.exit('no sql/zonelines.sql under ' + args.root)

    exits = parse_zonelines(src)
    names = parse_zone_names(args.root)
    docks = parse_docks(args.root, names)

    out = [
        '-- Vanaguide :: data/zonepoints.lua',
        '-- GENERATED by tools/gen_zonepoints.py from a LandSandBoat checkout.  Do not',
        '-- hand-edit.',
        '--',
        '-- Where the way out of a zone actually is.  data/zonelines.lua says which zones',
        '-- touch; this says the coordinate to walk to, in the zone you are standing in, so',
        '-- the arrow has something to point at for the whole journey instead of only at the',
        '-- last hop.',
        '--',
        '-- Axis order throughout is the one core/util.lua documents: x, z, y -- the two',
        '-- horizontal numbers first, height last.  LandSandBoat writes x, y, z with y the',
        '-- height; the swap is done by the generator.',
        '--',
        '-- Copyright (c) 2026 Bates LLC.  All rights reserved.',
        '',
        'local Z = {}',
        '',
        '-- Z.exit[from] = { { to, x, z, y }, ... }  -- more than one when a pair of zones has',
        '-- more than one doorway; the router walks you to the nearest.',
        'Z.exit = {',
    ]
    total = 0
    for zone in sorted(exits):
        rows = sorted(exits[zone])
        total += len(rows)
        pieces = ['{%d,%.1f,%.1f,%.1f}' % r for r in rows]
        line = '    [%d] = {' % zone
        for i, p in enumerate(pieces):
            if len(line) + len(p) > 94:
                out.append(line)
                line = '        '
            line += p + (',' if i < len(pieces) - 1 else '')
        out.append(line + '},')
    out += ['}', '']

    out += [
        '-- Z.dock[from][to] = { x, z, y, via }  -- where you board, and what to call it.',
        'Z.dock = {',
    ]
    by_from = {}
    for (a, b), v in docks.items():
        by_from.setdefault(a, {})[b] = v
    for a in sorted(by_from):
        out.append('    [%d] = {' % a)
        for b in sorted(by_from[a]):
            x, z, y, via = by_from[a][b]
            out.append('        [%d] = {%.1f,%.1f,%.1f,%s},' % (b, x, z, y, lua_str(via)))
        out.append('    },')
    out += ['}', '', 'return Z', '']

    open(args.out, 'w', encoding='utf-8').write('\n'.join(out))
    print('%d exits across %d zones, %d docks -> %s'
          % (total, len(exits), len(docks), args.out))


if __name__ == '__main__':
    sys.exit(main())
