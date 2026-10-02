#!/usr/bin/env python3
"""Vanaguide :: tools/gen_navgrid.py

Turn LandSandBoat's navigation meshes into something a Lua addon can walk.

The line on the ground is a straight line.  It is right about the direction and silent about
the cliff, which is exactly as much as the arrow ever knew.  The data to fix that is already
on any machine that runs a LandSandBoat server: `navmeshes/*.nav`, 304 zones, and they are
plain Recast/Detour navigation meshes -- magic `TESM`, a `dtNavMeshParams`, then tiles of
`dtMeshHeader` + vertices + polygons.  Every walkable surface in the game, already computed.

What they are not is loadable by an addon.  A Detour mesh is a tiled polygon soup with a
BV-tree and off-mesh links, and 422 MB of it; a guide needs "can I stand here, and how high
is the ground" over a few hundred yalms.  So this rasterises the walkable polygons into a
coarse grid -- one bit and one height per cell -- which is small, trivially indexable, and
enough for an A* that goes round the wall.

    tools/gen_navgrid.py <lsb checkout or navmeshes dir> [-o Vanaguide/data/nav] [--zone N]

THE OUTPUT IS NOT SHIPPED, and must not be.  The meshes are derived from Square Enix's map
geometry and LandSandBoat is GPL-3.0; a grid built from them is a derived work twice over.
The tool ships, the data does not, and `routing/navgrid.lua` falls back to a straight line
for any zone with no file -- which is every zone, until somebody runs this against a copy
they already have.  Same shape as tools/gen_zonelines.py and tools/gen_quests.py.

## The file it writes

`<zone id>.vgnav`, little-endian, and deliberately dull so the Lua side can read it with
`string.byte` and nothing else:

    0   "VGNV"                 magic
    4   version                1 byte, currently 1
    5   zone id                2 bytes
    7   cell size, tenths      1 byte  (20 = two yalms; see --cell)
    8   origin x, tenths       4 bytes signed  (the west/south corner, in yalms x 10)
    12  origin z, tenths       4 bytes signed
    16  width in cells         2 bytes
    18  height in cells        2 bytes
    20  mask run count         4 bytes
    24  mask runs              5 bytes each: 4-byte length, 1-byte value (0 or 1)
    ..  height run count       4 bytes
    ..  height runs            6 bytes each: 4-byte length, 2-byte signed height x 4

Both arrays are run-length encoded because both are enormously repetitive -- most of a zone
is one unbroken run of "not walkable", and open ground is one height for tens of cells.

## Two known simplifications, said out loud

**One floor.**  A cell holds one height, so a zone stacked on itself -- a tower, a bridge over
a road -- keeps the *lower* surface and forgets the other.  Ground level is what a guide
usually wants, and the cost of the error is a line drawn under a bridge you are walking over.
A second layer is a real fix and is not this.

**Coarse.**  The cell is chosen per zone so the grid stays under `--max-cells`, which for a
2,400-yalm zone means four or six yalms.  A doorway narrower than a cell can close.  The A*
falls back to a straight line when it cannot find a route, so a closed doorway costs you the
detour drawing, not the guide.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import os
import re
import struct
import sys

DETOUR_MAGIC = 0x444E4156          # 'DNAV'
SET_MAGIC = b'TESM'                # 'MSET', little-endian
MESH_HEADER = 100                  # bytes, dtMeshHeader
POLY_SIZE = 32                     # bytes, dtPoly
DT_VERTS_PER_POLYGON = 6


def parse_zone_names(root):
    """sql/zone_settings.sql -> {'Southern_San_dOria': 230}, the navmesh file naming."""
    out = {}
    path = os.path.join(root, 'sql', 'zone_settings.sql')
    if not os.path.exists(path):
        return out
    pat = re.compile(r"\((\d+),\d+,'[^']*',\d+,'([^']*)'")
    for line in open(path, encoding='utf-8', errors='replace'):
        if line.startswith('INSERT'):
            for m in pat.finditer(line):
                out[m.group(2)] = int(m.group(1))
    return out


def read_polygons(path):
    """-> (list of polygons, each a list of (x, z, y) in FFXI axes).

    LandSandBoat converts between the two spaces with two sign flips
    (`src/map/navmesh/detour_navmesh.cpp`): FFXI (x, y, z) -> Detour (x, -y, -z).  Going back
    is the same operation.  Everything below is in *guide* order afterwards -- x, z, then the
    height -- to match every other data file in this project.
    """
    d = open(path, 'rb').read()
    if d[:4] != SET_MAGIC:
        raise ValueError('%s is not a Detour navmesh set' % path)
    _, version, ntiles = struct.unpack_from('<4sii', d, 0)
    off = 40                                    # 12 header + 28 dtNavMeshParams
    polys = []
    for _ in range(ntiles):
        if off + 8 > len(d):
            break
        _ref, size = struct.unpack_from('<Ii', d, off)
        off += 8
        if size <= 0 or off + size > len(d):
            break
        magic, hver = struct.unpack_from('<ii', d, off)
        if magic != DETOUR_MAGIC:
            off += size
            continue
        poly_count, vert_count = struct.unpack_from('<ii', d, off + 24)
        verts_at = off + MESH_HEADER
        polys_at = verts_at + vert_count * 12
        verts = struct.unpack_from('<%df' % (vert_count * 3), d, verts_at)
        for i in range(poly_count):
            base = polys_at + i * POLY_SIZE
            at = d[base + 31]
            if (at >> 6) != 0:                  # type 1 is an off-mesh connection, not ground
                continue
            n = d[base + 30]
            if n < 3:
                continue
            idx = struct.unpack_from('<%dH' % DT_VERTS_PER_POLYGON, d, base + 4)
            ring = []
            for k in range(n):
                v = idx[k] * 3
                if v + 2 >= len(verts):
                    ring = []
                    break
                # Detour (x, up, z) -> FFXI (x, z, height); the height axis points down.
                ring.append((verts[v], -verts[v + 2], -verts[v + 1]))
            if len(ring) >= 3:
                polys.append(ring)
        off += size
    return polys


def choose_cell(width, height, max_cells, wanted):
    """The finest cell that keeps the grid under the budget.

    A city is a few hundred yalms across and wants two-yalm cells so a gate stays open; an
    outdoor zone can be two thousand and would be a million cells at that size.  Rather than
    pick one number and be wrong for half the game, pick per zone and write it in the file.
    """
    for cell in (wanted, 3.0, 4.0, 6.0, 8.0, 12.0):
        if cell < wanted:
            continue
        if (width / cell) * (height / cell) <= max_cells:
            return cell
    return 16.0


def rasterise(polys, cell, max_cells, wanted):
    """-> (ox, oz, w, h, mask, heights) with mask a bytearray of 0/1 and heights a list."""
    xs = [p[0] for ring in polys for p in ring]
    zs = [p[1] for ring in polys for p in ring]
    minx, maxx = min(xs), max(xs)
    minz, maxz = min(zs), max(zs)
    cell = choose_cell(maxx - minx + 1, maxz - minz + 1, max_cells, wanted)
    ox = minx - cell
    oz = minz - cell
    w = int((maxx - ox) / cell) + 2
    h = int((maxz - oz) / cell) + 2

    mask = bytearray(w * h)
    # The height axis points down, so "keep the lower surface" is "keep the larger y".
    heights = [None] * (w * h)

    for ring in polys:
        ys = [p[2] for p in ring]
        ylo, yhi = min(ys), max(ys)
        rminx = min(p[0] for p in ring)
        rmaxx = max(p[0] for p in ring)
        rminz = min(p[1] for p in ring)
        rmaxz = max(p[1] for p in ring)
        c0 = max(0, int((rminx - ox) / cell))
        c1 = min(w - 1, int((rmaxx - ox) / cell))
        r0 = max(0, int((rminz - oz) / cell))
        r1 = min(h - 1, int((rmaxz - oz) / cell))
        if c1 < c0 or r1 < r0:
            continue
        # A polygon can be smaller than a cell -- Recast makes plenty of those -- so a strict
        # centre-in-polygon test drops it entirely and punches a hole in the floor.  Anything
        # that lands in only one cell claims that cell outright.
        tiny = (c1 == c0 and r1 == r0)
        plane = plane_of(ring)

        def put(c, r, y):
            if c < 0 or r < 0 or c >= w or r >= h:
                return
            if y < ylo:
                y = ylo
            elif y > yhi:
                y = yhi
            i = r * w + c
            mask[i] = 1
            cur = heights[i]
            if cur is None or y > cur:
                heights[i] = y

        # The polygon's *edges*, cell by cell, before its interior.  A centre-in-polygon test
        # on its own drops every cell whose middle falls a hand's breadth outside the mesh,
        # and in a city that is most of the kerb: Southern San d'Oria came out as 88
        # disconnected islands, with the west gate and the east gate in different ones, so no
        # route existed between two doors of the same city.  Painting the boundary closes
        # them.  It errs a cell wide, which is a path that hugs the wall rather than a path
        # that does not exist.
        for k in range(len(ring)):
            ax, az, ay = ring[k]
            bx, bz, by = ring[(k + 1) % len(ring)]
            steps = int(max(abs(bx - ax), abs(bz - az)) / cell) + 1
            for t in range(steps + 1):
                f = t / float(steps)
                px = ax + (bx - ax) * f
                pz = az + (bz - az) * f
                put(int((px - ox) / cell), int((pz - oz) / cell), ay + (by - ay) * f)

        for r in range(r0, r1 + 1):
            pz = oz + (r + 0.5) * cell
            for c in range(c0, c1 + 1):
                px = ox + (c + 0.5) * cell
                if not tiny and not inside(ring, px, pz):
                    continue
                # `put` clamps to the polygon's own corners.  A surface cannot be higher or
                # lower than its own vertices, and without that a nearly-degenerate triangle
                # -- Recast makes plenty -- extrapolates its plane out to the cell centre and
                # invents a height.  Southern San d'Oria came out spanning 285 yalms
                # vertically, in a city whose navmesh is 43 yalms tall.
                put(c, r, plane(px, pz) if plane is not None else (sum(ys) / len(ys)))
    return ox, oz, w, h, cell, mask, heights


def plane_of(ring):
    """A function giving the polygon's height at (x, z), or None if it is degenerate."""
    (x0, z0, y0) = ring[0]
    for i in range(1, len(ring) - 1):
        x1, z1, y1 = ring[i]
        x2, z2, y2 = ring[i + 1]
        det = (x1 - x0) * (z2 - z0) - (x2 - x0) * (z1 - z0)
        if abs(det) < 1e-6:
            continue
        a = ((y1 - y0) * (z2 - z0) - (y2 - y0) * (z1 - z0)) / det
        b = ((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / det
        return lambda x, z, a=a, b=b, x0=x0, z0=z0, y0=y0: y0 + a * (x - x0) + b * (z - z0)
    return None


def inside(ring, px, pz):
    """Even-odd point in polygon, in the x/z plane."""
    n = len(ring)
    hit = False
    j = n - 1
    for i in range(n):
        xi, zi = ring[i][0], ring[i][1]
        xj, zj = ring[j][0], ring[j][1]
        if (zi > pz) != (zj > pz):
            if px < (xj - xi) * (pz - zi) / (zj - zi) + xi:
                hit = not hit
        j = i
    return hit


def rle_bytes(values, pack, size):
    """Run-length encode a sequence.  Both arrays here are hugely repetitive."""
    out = bytearray()
    runs = 0
    if not values:
        return 0, out
    cur = values[0]
    n = 0
    for v in values:
        if v == cur:
            n += 1
            continue
        out += struct.pack('<I', n) + pack(cur)
        runs += 1
        cur, n = v, 1
    out += struct.pack('<I', n) + pack(cur)
    return runs + 1, out


def write_grid(path, zone, ox, oz, w, h, cell, mask, heights):
    # An unwalkable cell still needs a height in the array so the runs line up with the mask;
    # zero is as good as anything and is never read.
    quant = [0 if heights[i] is None else max(-32000, min(32000, int(round(heights[i] * 4))))
             for i in range(w * h)]
    mask_runs, mask_bytes = rle_bytes(mask, lambda v: struct.pack('<B', v), 1)
    h_runs, h_bytes = rle_bytes(quant, lambda v: struct.pack('<h', v), 2)
    body = struct.pack('<4sBHBiiHH', b'VGNV', 1, zone, int(round(cell * 10)),
                       int(round(ox * 10)), int(round(oz * 10)), w, h)
    body += struct.pack('<I', mask_runs) + bytes(mask_bytes)
    body += struct.pack('<I', h_runs) + bytes(h_bytes)
    open(path, 'wb').write(body)
    return len(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', help='a LandSandBoat checkout, or a navmeshes directory')
    ap.add_argument('-o', '--out', default='Vanaguide/data/nav')
    ap.add_argument('--zone', type=int, action='append',
                    help='only this zone id; repeatable')
    ap.add_argument('--cell', type=float, default=2.0,
                    help='finest cell size in yalms (default 2)')
    ap.add_argument('--max-cells', type=int, default=150000,
                    help='cap on cells per zone; the cell size grows to fit (default 150000)')
    args = ap.parse_args()

    root = args.root
    meshes = root if os.path.basename(root.rstrip('/')) == 'navmeshes' \
        else os.path.join(root, 'navmeshes')
    if not os.path.isdir(meshes):
        meshes = os.path.join(root, 'server', 'navmeshes')
    if not os.path.isdir(meshes):
        sys.exit('no navmeshes/ under ' + root)
    lsb = os.path.dirname(os.path.dirname(meshes)) if meshes.endswith('server/navmeshes') \
        else os.path.dirname(meshes)
    names = parse_zone_names(os.path.join(lsb, 'server')) or parse_zone_names(lsb)

    os.makedirs(args.out, exist_ok=True)
    wanted = set(args.zone or [])
    done = skipped = total_bytes = 0
    for fn in sorted(os.listdir(meshes)):
        if not fn.endswith('.nav'):
            continue
        stem = fn[:-4]
        zone = int(stem) if stem.isdigit() else names.get(stem)
        # Zone 0 is `unknown` in zone_settings -- a placeholder, not a place. A grid for it
        # would never be asked for and would only sit in the folder looking like data.
        if zone is None or zone == 0:
            skipped += 1
            continue
        if wanted and zone not in wanted:
            continue
        try:
            polys = read_polygons(os.path.join(meshes, fn))
        except Exception as exc:                        # a mesh this tool cannot read is a
            print('  %-34s unreadable: %s' % (fn, exc))  # fact about the mesh, not a crash
            skipped += 1
            continue
        if not polys:
            skipped += 1
            continue
        ox, oz, w, h, cell, mask, heights = rasterise(polys, args.cell, args.max_cells,
                                                      args.cell)
        n = write_grid(os.path.join(args.out, '%d.vgnav' % zone), zone,
                       ox, oz, w, h, cell, mask, heights)
        total_bytes += n
        done += 1
        walk = sum(mask)
        print('  %-34s zone %-4d %4dx%-4d cell %.0f  %6d walkable  %6.1f KB'
              % (stem, zone, w, h, cell, walk, n / 1024.0))
    print('%d zones -> %s  (%.1f MB), %d skipped'
          % (done, args.out, total_bytes / 1048576.0, skipped))


if __name__ == '__main__':
    sys.exit(main())
