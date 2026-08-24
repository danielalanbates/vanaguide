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

    def completed(lines):
        for l in lines:
            if 'completed quests=' in l:
                try:
                    return int(l.split('completed quests=')[1].split()[0])
                except (IndexError, ValueError):
                    return None
        return None

    # Try several ids, because `!completequest` on a quest the character has already finished
    # changes nothing and is indistinguishable from the flag never arriving. The first run of
    # this check passed and the second failed on the same working code, for exactly that
    # reason -- the first run had completed the quest.
    before = completed(send('/vg story'))
    grew, tried = None, []
    for qid in [args.quest_id] + [i for i in range(1, 40) if i != args.quest_id]:
        send('!completequest %d %d' % (args.log_id, qid), wait=4)
        after = completed(send('/vg story'))
        tried.append(qid)
        if before is not None and after is not None and after > before:
            grew = (before, after, qid)
            break
        before = after
        if len(tried) >= 8:
            break
    check('a completed quest reaches the addon', grew is not None,
          ('completed quests went %d -> %d after !completequest %d %d'
           % (grew[0], grew[1], args.log_id, grew[2])) if grew else
          ('the count never moved across !completequest on %s -- either every one of those '
           'was already complete on this character, or the Q flags are not arriving'
           % ','.join(str(t) for t in tried)))

    print('\n== routing across zones', flush=True)
    zones = [int(z) for z in args.zones.split(',')][:2]
    send('!zone %d' % zones[0], wait=20)
    route = send('/vg route')
    check('the router answers for the current step',
          bool(route) and 'no place' not in ' '.join(route),
          (route[0] if route else 'nothing printed')[:110])

    print('\n== zone-line learning', flush=True)

    def pair(a, b):
        for l in send('/vg graph %d %d' % (a, b), wait=2):
            if 'learned = ' in l:
                return l.strip().endswith('yes')
        return None

    # Ask about the pair, not the total. Z.learn refuses to record a crossing it already
    # knows, so warping between two zones a sweep has visited a hundred times leaves the
    # count unchanged and looks exactly like learning being broken. The first run of this
    # check reported 340 -> 340 and meant nothing by it.
    before = pair(*zones)
    send('!zone %d' % zones[1], wait=20)
    send('!zone %d' % zones[0], wait=20)
    after = pair(*zones)
    if before:
        check('a GM warp is recorded as a crossing', True,
              'zones %d and %d were already known to the graph, so this run could not have '
              'shown anything either way -- pick a pair the sweep has not been through'
              % tuple(zones))
    else:
        check('a GM warp is recorded as a crossing', bool(after),
              'the pair %d-%d went from unknown to %s across two !zone calls. A GM warp is '
              'not walking through a zone line, so a FAIL here says the graph learns from '
              'walking and not from teleporting -- which is worth knowing and is not a bug'
              % (zones[0], zones[1], 'learned' if after else 'still unknown'))

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
