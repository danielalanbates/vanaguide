#!/usr/bin/env python3
"""Vanaguide :: tools/line_check.py

Prove the two things this branch added, in the game, without looking at the screen.

Both new features rest on claims nothing had tested.  The route now points at a *coordinate*
for a step in another zone -- that needs the generated zone-point table to be right about
where the doorway is.  The line on the ground needs the Direct3D device to hand over its
view and projection matrices, through the Mac port's `d3d8 -> d3d8to9 -> DXVK` chain, which
docs/PATHWAYS.md listed as an open question for months.

A script driving this client cannot read the screen, so `/vg line probe` prints points whose
answers are known in advance (docs/LINE.md), and this walks the list.

    tools/line_check.py --game "<game dir>"

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import os
import re
import sys
import time

TEE = 'answers.txt'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', required=True)
    ap.add_argument('--zone', default='Port Jeuno', help='somewhere far, for the travel test')
    ap.add_argument('--wait', type=float, default=3.0)
    args = ap.parse_args()

    addon = os.path.join(args.game, 'addons', 'Vanaguide')
    cmd, tee = os.path.join(addon, 'cmd.txt'), os.path.join(addon, TEE)
    if not os.path.isdir(addon):
        sys.exit('no Vanaguide addon folder at ' + addon)

    def send(line, wait=None):
        before = os.path.getsize(tee) if os.path.exists(tee) else 0
        with open(cmd, 'w') as fh:
            fh.write(line + '\n')
        end = time.time() + 10
        while time.time() < end:
            try:
                if os.path.getsize(cmd) == 0:
                    break
            except OSError:
                break
            time.sleep(0.3)
        time.sleep(wait if wait is not None else args.wait)
        if not os.path.exists(tee):
            return []
        with open(tee, encoding='utf-8', errors='replace') as fh:
            fh.seek(before)
            return [l.rstrip('\n') for l in fh if l.strip()]

    results = []

    def check(name, ok, detail):
        results.append((name, ok, detail))
        print(('  PASS ' if ok else '  FAIL ') + name + ' -- ' + detail, flush=True)

    open(tee, 'w').close()
    send('/vg tee ' + TEE, wait=2)
    hello = send('/vg status', wait=3)
    if not hello:
        sys.exit('the addon printed nothing -- is it loaded, and is this the right game dir?')
    print('== status', flush=True)
    print('   ' + '\n   '.join(hello), flush=True)

    exits = 0
    for line in hello:
        m = re.search(r'exits known out of this zone: (\d+)', line)
        if m:
            exits = int(m.group(1))
    check('the zone-point table reached the client', exits > 0,
          '%d exits known out of this zone' % exits)

    # ---- the camera -------------------------------------------------------------
    print('\n== the projection', flush=True)
    probe = send('/vg line probe', wait=3)
    print('   ' + '\n   '.join(probe), flush=True)
    got = {}
    vp = (0, 0)
    for line in probe:
        m = re.search(r'viewport (\d+)x(\d+)', line)
        if m:
            vp = (int(m.group(1)), int(m.group(2)))
        # Every printed line carries the addon's own "[Vanaguide] " prefix in the tee file.
        m = re.search(r'(feet|ahead|above)\s+world .*-> screen (-?[\d.]+),(-?[\d.]+)\s+w=(-?[\d.]+)',
                      line)
        if m:
            got[m.group(1)] = (float(m.group(2)), float(m.group(3)), float(m.group(4)))

    check('GetTransform answered', any('GetTransform ok' in l for l in probe),
          'through d3d8to9 and DXVK' if any('GetTransform ok' in l for l in probe)
          else ' / '.join(probe) or 'no output')

    if len(got) == 3 and vp[0] > 0:
        w, h = vp
        fx, fy, fw = got['feet']
        ax, ay, aw = got['ahead']
        bx, by, bw = got['above']
        check('the player projects in front of the camera', 0 < fw < 120,
              'w=%.2f (the camera distance)' % fw)
        check('and near the middle of the screen', abs(fx - w / 2) < w * 0.30,
              'x=%.0f of %d' % (fx, w))
        check('and in the lower half', fy > h * 0.35, 'y=%.0f of %d' % (fy, h))
        check('twenty yalms ahead is further away', aw > fw + 5,
              'w %.1f -> %.1f' % (fw, aw))
        check('and higher up the screen', ay < fy, 'y %.0f -> %.0f' % (fy, ay))
        check('five yalms up is higher up the screen', by < fy - 8,
              'y %.0f -> %.0f' % (fy, by))
        check('and directly above the player', abs(bx - fx) < w * 0.05,
              'x %.0f vs %.0f' % (fx, bx))
    else:
        check('the probe printed three points', False,
              'got %d: %s' % (len(got), ', '.join(sorted(got))))

    # ---- routing to a place, not to a name --------------------------------------
    print('\n== routing to a coordinate', flush=True)
    go = send('/vg goto ' + args.zone, wait=3)
    print('   ' + '\n   '.join(go), flush=True)
    check('goto plans a route', any('going to' in l for l in go), ' / '.join(go[:1]) or 'nothing')
    check('and the first leg has a distance in yalms',
          any(re.search(r'\d+ yalms', l) for l in go),
          'the arrow has something to point at' if any(re.search(r'\d+ yalms', l) for l in go)
          else 'no coordinate for the first leg')

    route = send('/vg route', wait=3)
    print('   ' + '\n   '.join(route), flush=True)

    st = send('/vg status', wait=3)
    mode = ''
    for line in st:
        m = re.search(r'mode=(\w+) dist=([\d.-]+) bearing=([\d.-]+)', line)
        if m:
            mode = m.group(1)
            check('the arrow has a bearing while travelling',
                  m.group(2) != '-' and m.group(3) != '-',
                  'mode=%s dist=%s bearing=%s deg' % (m.group(1), m.group(2), m.group(3)))
    if not mode:
        # /vg status only reports a step when a guide is loaded; goto is not one.
        print('   (no guide loaded, so status has no step line -- goto was checked above)',
              flush=True)

    send('/vg goto off', wait=2)

    print('\n== summary', flush=True)
    bad = [n for n, ok, _ in results if not ok]
    for name, ok, detail in results:
        print(('  PASS ' if ok else '  FAIL ') + name)
    print('\n%d checks, %d failed' % (len(results), len(bad)), flush=True)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
