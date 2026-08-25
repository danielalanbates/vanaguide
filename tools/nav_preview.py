#!/usr/bin/env python3
"""Vanaguide :: tools/nav_preview.py

Look at a navigation grid, and count how many pieces it is in.

`tools/gen_navgrid.py` writes a grid of walkable cells and ground heights per zone
(docs/NAVMESH.md). Nothing about that file is readable by eye, and the two bugs it had were
both invisible in its statistics and obvious in a picture:

* Southern San d'Oria came out as **88 disconnected islands** with its west gate and its east
  gate in different ones, so no route existed between two doors of the same city. The counts
  looked perfectly healthy: 8,345 walkable cells, the right bounding box, the gates both
  marked walkable.
* The same city came out spanning 285 yalms vertically, in a navmesh 43 yalms tall, because a
  plane fitted through a degenerate triangle was extrapolated to the cell centre.

So this does two things. It writes a PNG -- walkable cells shaded by height -- which is
enough to recognise a city you have walked through. And it counts connected components under
**the same movement rule the addon's A\\* uses**, including the no-corner-cutting rule, which
is the number that actually says whether a route can exist.

    tools/nav_preview.py Vanaguide/data/nav/230.vgnav -o /tmp/sandoria.png
    tools/nav_preview.py Vanaguide/data/nav/230.vgnav --at -113.4,-57.4 --at 113.5,-57.4

`--at x,z` marks a coordinate and says which component it landed in. Two points in different
components mean the grid is lying to the router, whatever the picture looks like.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import struct
import sys
import zlib
from collections import deque

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


def read_grid(path):
    d = open(path, 'rb').read()
    magic, ver, zone, cell10, ox10, oz10, w, h = struct.unpack_from('<4sBHBiiHH', d, 0)
    if magic != b'VGNV':
        sys.exit('%s is not a Vanaguide navigation grid' % path)
    off = 20
    (mask_runs,) = struct.unpack_from('<I', d, off)
    off += 4
    mask = bytearray()
    for _ in range(mask_runs):
        n, v = struct.unpack_from('<IB', d, off)
        off += 5
        mask += bytes([v]) * n
    (h_runs,) = struct.unpack_from('<I', d, off)
    off += 4
    heights = []
    for _ in range(h_runs):
        n, v = struct.unpack_from('<Ih', d, off)
        off += 6
        heights += [v] * n
    return dict(zone=zone, cell=cell10 / 10.0, ox=ox10 / 10.0, oz=oz10 / 10.0,
                w=w, h=h, mask=mask, heights=heights)


def components(g):
    """Label every walkable cell, under the addon's own movement rule.

    The no-corner-cutting rule matters here and is easy to leave out: a diagonal step is only
    a step when both squares beside it are open.  Counting components without it says a grid
    is connected when the search that has to cross it disagrees.
    """
    w, h, mask = g['w'], g['h'], g['mask']
    label = [0] * (w * h)
    sizes = []
    for start in range(w * h):
        if not mask[start] or label[start]:
            continue
        cid = len(sizes) + 1
        q = deque([start])
        label[start] = cid
        n = 0
        while q:
            i = q.popleft()
            n += 1
            cz, cx = divmod(i, w)
            for dx, dz in DIRS:
                nx, nz = cx + dx, cz + dz
                if not (0 <= nx < w and 0 <= nz < h):
                    continue
                j = nz * w + nx
                if not mask[j] or label[j]:
                    continue
                if dx and dz and not (mask[cz * w + cx + dx] and mask[(cz + dz) * w + cx]):
                    continue
                label[j] = cid
                q.append(j)
        sizes.append(n)
    return label, sizes


def write_png(path, g, label, marks, scale):
    w, h, mask, heights = g['w'], g['h'], g['mask'], g['heights']
    hs = [heights[i] / 4.0 for i in range(w * h) if mask[i]]
    lo, hi = (min(hs), max(hs)) if hs else (0.0, 1.0)
    span = max(0.001, hi - lo)
    rows = []
    for r in range(h):
        row = bytearray()
        for c in range(w):
            i = r * w + c
            if mask[i]:
                t = (heights[i] / 4.0 - lo) / span
                v = int(40 + 200 * (1 - t))
                px = (v, v, 255 - v // 2)
            else:
                px = (16, 18, 24)
            row += bytes(px) * scale
        for _ in range(scale):
            rows.append(b'\x00' + bytes(row))
    # The marks go on last so they are never painted over.
    W = w * scale
    for (cx, cz) in marks:
        for dz in range(-3, 4):
            for dx in range(-3, 4):
                x, z = cx * scale + dx, cz * scale + dz
                if 0 <= x < W and 0 <= z < h * scale:
                    off = 1 + x * 3
                    rows[z] = rows[z][:off] + b'\xff\xff\xff' + rows[z][off + 3:]
    raw = b''.join(rows)

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xffffffff)

    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', W, h * scale, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 6))
           + chunk(b'IEND', b''))
    open(path, 'wb').write(png)
    return W, h * scale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('grid', help='a .vgnav file from tools/gen_navgrid.py')
    ap.add_argument('-o', '--out', help='write a PNG here')
    ap.add_argument('--scale', type=int, default=2, help='pixels per cell (default 2)')
    ap.add_argument('--at', action='append', default=[],
                    help='x,z in world coordinates; marked, and its component reported')
    args = ap.parse_args()

    g = read_grid(args.grid)
    walk = sum(g['mask'])
    hs = [g['heights'][i] / 4.0 for i in range(g['w'] * g['h']) if g['mask'][i]]
    print('zone %d: %dx%d cells of %.1f yalms, origin %.1f,%.1f'
          % (g['zone'], g['w'], g['h'], g['cell'], g['ox'], g['oz']))
    print('  %d walkable of %d (%.0f%%), height %.1f .. %.1f'
          % (walk, g['w'] * g['h'], 100.0 * walk / max(1, g['w'] * g['h']),
             min(hs) if hs else 0, max(hs) if hs else 0))

    label, sizes = components(g)
    order = sorted(range(len(sizes)), key=lambda i: -sizes[i])
    print('  %d connected component(s); largest %s'
          % (len(sizes), [sizes[i] for i in order[:5]]))
    if len(sizes) > 1:
        biggest = sizes[order[0]]
        print('  %.1f%% of walkable ground is in the largest one'
              % (100.0 * biggest / max(1, walk)))

    marks = []
    for spec in args.at:
        try:
            x, z = (float(v) for v in spec.split(','))
        except ValueError:
            sys.exit('--at wants x,z')
        cx = int((x - g['ox']) / g['cell'])
        cz = int((z - g['oz']) / g['cell'])
        inside = 0 <= cx < g['w'] and 0 <= cz < g['h']
        i = cz * g['w'] + cx if inside else -1
        print('  %s -> cell %d,%d  walkable=%s  component=%s'
              % (spec, cx, cz,
                 bool(inside and g['mask'][i]),
                 label[i] if inside and g['mask'][i] else '-'))
        if inside:
            marks.append((cx, cz))

    if len(marks) > 1:
        comps = {label[cz * g['w'] + cx] for cx, cz in marks
                 if g['mask'][cz * g['w'] + cx]}
        if len(comps) > 1:
            print('  MARKED POINTS ARE IN DIFFERENT COMPONENTS -- no route can exist')

    if args.out:
        W, H = write_png(args.out, g, label, marks, max(1, args.scale))
        print('  wrote %s (%dx%d)' % (args.out, W, H))


if __name__ == '__main__':
    sys.exit(main())
