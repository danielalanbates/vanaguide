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


DOOR_AREA = re.compile(r'register(Cuboid|Cylindrical)TriggerArea\(\s*(\d+)\s*,([^)]*)\)')
DOOR_CASE = re.compile(r'\[\s*(\d+)\s*\]\s*=\s*function\s*\(\)(.*?)\n\s{8}end,', re.S)
DOOR_START = re.compile(r'startEvent\(\s*(\d+)')
DOOR_FINISH = re.compile(r'csid\s*==\s*(\d+)\s*(?:then|or|and)(.*?)(?=\n\s{4}(?:elseif|end)\b)', re.S)
DOOR_SETPOS = re.compile(r'setPos\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*[-\d.]+\s*,\s*(\d+)\s*\)')


def parse_doors(root, names):
    """-> {from_zone: [(to_zone, x, z, y), ...]} for doors that are not zone lines.

    A city's inner gate -- the Chateau d'Oraguille from Northern San d'Oria, the Metalworks,
    Heavens Tower -- is not in zonelines.sql.  It is a *trigger area* in the zone's Zone.lua:
    stepping into a cuboid starts a gatekeeper event, and when that event finishes the
    server moves the player into the other zone with setPos(..., zoneId).  Read the three
    parts and join them: area id -> events started -> zone the finish leads to.  The walk-to
    point is the middle of the area.  Only areas whose event finish carries a zone id count;
    quest trigger areas start events too, and lead nowhere.
    """
    doors = {}
    by_name = {v.replace(' ', '_'): k for k, v in names.items()}
    zdir = os.path.join(root, 'scripts', 'zones')
    if not os.path.isdir(zdir):
        return doors
    for d in sorted(os.listdir(zdir)):
        zone = by_name.get(d)
        path = os.path.join(zdir, d, 'Zone.lua')
        if zone is None or not os.path.exists(path):
            continue
        text = open(path, encoding='utf-8', errors='replace').read()
        areas = {}
        for m in DOOR_AREA.finditer(text):
            nums = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', m.group(3))]
            if m.group(1) == 'Cuboid' and len(nums) >= 6:
                x1, y1, z1, x2, y2, z2 = nums[:6]
                areas[int(m.group(2))] = ((x1 + x2) / 2, (z1 + z2) / 2, (y1 + y2) / 2)
            elif m.group(1) == 'Cylindrical' and len(nums) >= 3:
                areas[int(m.group(2))] = (nums[0], nums[1], 0.0)
        finish = {}
        for m in DOOR_FINISH.finditer(text):
            sp = DOOR_SETPOS.search(m.group(2))
            if sp:
                finish[int(m.group(1))] = int(sp.group(4))
        for m in DOOR_CASE.finditer(text):
            aid = int(m.group(1))
            if aid not in areas:
                continue
            for ev in DOOR_START.findall(m.group(2)):
                to = finish.get(int(ev))
                if to is not None and to != zone:
                    x, z, y = areas[aid]
                    row = (to, x, z, y)
                    if row not in doors.setdefault(zone, []):
                        doors[zone].append(row)
    return doors


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
    doors = parse_doors(args.root, names)
    ndoors = 0
    for zone, rows in doors.items():
        for r in rows:
            exits.setdefault(zone, []).append(r)
            ndoors += 1

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
    print('%d exits across %d zones (%d of them doors), %d docks -> %s'
          % (total, len(exits), ndoors, len(docks), args.out))


if __name__ == '__main__':
    sys.exit(main())
