#!/usr/bin/env python3
"""Vanaguide :: tools/capability_check.py

Answer the questions docs/VERIFICATION.md lists as still open.

The first in-game run proved the addon loads, draws, reads the story packet and completes a
mission step. It left six things unverified, and five of them were unverified for the same
reason: every `/vg` command answers into the game's chat log, a script driving the client
through `cmd.txt` cannot read chat, and nobody wanted to sit and squint at screenshots.

`/vg tee <file>` fixed that -- printed lines are copied to a file -- so this walks the list:

  quest flags      `!completequest` on the live server, then `/vg story`: does the Q bit
                   turn on? Missions were proven end to end months ago and quests never were,
                   because the test character had never finished one.
  routing          `/vg route` with the current step in another zone: does it produce legs?
  zone learning    two `!zone` calls, then `/vg graph`: does a crossing get recorded? A GM
                   warp may or may not look like walking through a zone line, and which one
                   it is has never been established.
  mark             `/vg mark` writes marks.txt.

What it cannot answer is the sixth: whether the arrow points at the thing. That needs
somebody to walk.

    tools/capability_check.py --game "<game dir>"

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TEE = 'answers.txt'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', required=True)
    ap.add_argument('--quest-area', default='sandoria', help='a quest area for the flag test')
    ap.add_argument('--quest-id', type=int, default=29)
    ap.add_argument('--log-id', type=int, default=0, help="the server's log id for that area")
    ap.add_argument('--zones', default='231,232', help='two adjacent zones for the walk test')
    ap.add_argument('--wait', type=float, default=6.0)
    args = ap.parse_args()

    addon = os.path.join(args.game, 'addons', 'Vanaguide')
    cmd, tee = os.path.join(addon, 'cmd.txt'), os.path.join(addon, TEE)
    if not os.path.isdir(addon):
        sys.exit('no Vanaguide addon folder at ' + addon)

    def send(line, wait=None):
        """One line, and the addon's answer to it."""
        before = os.path.getsize(tee) if os.path.exists(tee) else 0
        with open(cmd, 'w') as fh:
            fh.write(line + '\n')
        end = time.time() + 8
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

    print('== turning the tee on', flush=True)
    open(tee, 'w').close()
    send('/vg tee ' + TEE, wait=2)
    hello = send('/vg status', wait=3)
    if not hello:
        sys.exit('the addon printed nothing -- is it loaded, and is this the right game dir?')
    print('   ' + '\n   '.join(hello), flush=True)

    print('\n== quest completion flags', flush=True)
    before = send('/vg story')
    send('!completequest %d %d' % (args.log_id, args.quest_id), wait=4)
    after = send('/vg story')

    def completed(lines):
        for l in lines:
            if 'completed quests=' in l:
                try:
                    return int(l.split('completed quests=')[1].split()[0])
                except (IndexError, ValueError):
                    return None
        return None

    a, b = completed(before), completed(after)
    check('a completed quest reaches the addon',
          a is not None and b is not None and b > a,
          'completed quests went %s -> %s after !completequest %d %d'
          % (a, b, args.log_id, args.quest_id))

    print('\n== routing across zones', flush=True)
    zones = [int(z) for z in args.zones.split(',')][:2]
    send('!zone %d' % zones[0], wait=20)
    route = send('/vg route')
    check('the router answers for the current step',
          bool(route) and 'no place' not in ' '.join(route),
          (route[0] if route else 'nothing printed')[:110])

    print('\n== zone-line learning', flush=True)
    was = send('/vg graph')
    send('!zone %d' % zones[1], wait=20)
    send('!zone %d' % zones[0], wait=20)
    now = send('/vg graph')

    def crossings(lines):
        for l in lines:
            if 'learned crossings' in l:
                try:
                    return int(l.split(',')[1].strip().split()[0])
                except (IndexError, ValueError):
                    return None
        return None

    a, b = crossings(was), crossings(now)
    check('a GM warp is recorded as a crossing',
          a is not None and b is not None and b > a,
          'learned crossings went %s -> %s across two !zone calls. A GM warp is not walking '
          'through a zone line, so a FAIL here is a finding about the test, not the feature'
          % (a, b))

    print('\n== mark', flush=True)
    marks = os.path.join(addon, 'marks.txt')
    size = os.path.getsize(marks) if os.path.exists(marks) else 0
    send('/vg mark capability check')
    grew = os.path.exists(marks) and os.path.getsize(marks) > size
    check('/vg mark writes marks.txt', grew,
          'marks.txt %s' % ('grew' if grew else 'did not change'))

    send('/vg tee off', wait=2)
    print('\n%d of %d answered yes' % (sum(1 for _, ok, _ in results if ok), len(results)),
          flush=True)
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == '__main__':
    sys.exit(main())
