#!/usr/bin/env python3
"""Vanaguide :: tools/client_names.py

Does the client call each step's NPC by the name the server's npc_list gives it?

For an ordinary NPC the client shows the name its own NPC-name DAT (file 6720 + zone) gives
the target index, not a name from the server.  LandSandBoat numbers its NPCs after current retail,
and a client whose DATs are older has a different list in some zones -- in the HorizonXI
install of 2023 the index of every NPC after an insertion is one to a dozen higher on the
server.  There the audit's name check cannot pass: the NPC standing on the marker carries
somebody else's name, and the name the guide asks for belongs to an NPC elsewhere.

    tools/client_names.py --ffxi "<.../FINAL FANTASY XI>" --steps results/steps.jsonl [--overlay DIR]

Prints one line per step whose NPC the client names differently, and a per-zone summary.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import json
import math
import os
import struct
import sys

from npc_positions import sql, normalize


def dat_path(ffxi, file_id):
    """ROM-relative path of a file id, from the VTABLE/FTABLE pair of the ROM that has it."""
    for rom in range(1, 10):
        folder = 'ROM' if rom == 1 else f'ROM{rom}'
        vt = os.path.join(ffxi, 'VTABLE.DAT' if rom == 1 else os.path.join(folder, f'VTABLE{rom}.DAT'))
        ft = os.path.join(ffxi, 'FTABLE.DAT' if rom == 1 else os.path.join(folder, f'FTABLE{rom}.DAT'))
        if not os.path.exists(vt):
            continue
        with open(vt, 'rb') as fh:
            fh.seek(file_id)
            b = fh.read(1)
        if not b or b[0] == 0:
            continue
        with open(ft, 'rb') as fh:
            fh.seek(file_id * 2)
            e = struct.unpack('<H', fh.read(2))[0]
        return os.path.join(folder, str(e >> 7), f'{e & 0x7F}.DAT')
    return None


def client_names(ffxi, zone, overlay=None):
    """{target index: name} from the zone's NPC-name DAT (32-byte records: name[28], id)."""
    rel = dat_path(ffxi, 6720 + zone) if zone < 256 else None
    if rel is None:
        return None
    path = os.path.join(overlay, rel) if overlay and os.path.exists(os.path.join(overlay, rel)) else os.path.join(ffxi, rel)
    data = open(path, 'rb').read()
    out = {}
    for i in range(0, len(data) - 31, 32):
        name = data[i:i + 28].split(b'\0')[0].decode('latin-1')
        npcid = struct.unpack_from('<I', data, i + 28)[0]
        if (npcid >> 12) & 0xFFF == zone:
            out[npcid & 0xFFF] = name
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ffxi', required=True, help='the FINAL FANTASY XI folder (VTABLE.DAT, ROM...)')
    ap.add_argument('--steps', required=True)
    ap.add_argument('--overlay', help='an XIPivot overlay folder, checked before the install')
    a = ap.parse_args()

    steps = [json.loads(l) for l in open(a.steps)]
    zones = sorted({s['zone'] for s in steps if s.get('npc') and s.get('zone') is not None})
    server, client, bad = {}, {}, {}
    for zone in zones:
        rows = sql(f'SELECT npcid & 0xFFF, polutils_name, pos_x, pos_z FROM npc_list '
                   f'WHERE ((npcid >> 12) & 0xFFF) = {zone} AND status = 0')
        server[zone] = [(int(t), n, float(x), float(z)) for t, n, x, z in rows]
        client[zone] = client_names(a.ffxi, zone, a.overlay)
        if client[zone] is not None:
            bad[zone] = sum(1 for t, n, _, _ in server[zone]
                            if n and normalize(client[zone].get(t, '')) != normalize(n))

    for s in steps:
        zone, npc = s.get('zone'), s.get('npc')
        if not npc or zone is None or client.get(zone) is None:
            continue
        mine = [r for r in server[zone] if normalize(r[1]) == normalize(npc)]
        if not mine:
            continue
        if s.get('x') is not None:
            mine.sort(key=lambda r: math.hypot(r[2] - s['x'], r[3] - s['z']))
        t = mine[0][0]
        seen = client[zone].get(t, '')
        if normalize(seen) != normalize(npc):
            print(f"{s['guide']}/{s['step']}  zone {zone}  {npc!r} is index {t} on the server; "
                  f"the client calls index {t} {seen!r}")
    print()
    for zone in zones:
        if bad.get(zone):
            print(f'zone {zone}: {bad[zone]} of {len(server[zone])} spawned NPCs named differently by the client')


if __name__ == '__main__':
    sys.exit(main())
