#!/usr/bin/env python3
"""Vanaguide :: tools/settle_probe.py

Measure how long a zone actually takes to stream its entities, instead of guessing.

Every sweep so far has picked a settle time by feel -- twenty seconds, then thirty-two --
and every absent result carries the same unanswerable objection: maybe the check just
asked too early. `--retry-absent` at a longer settle is a blind fix for that, and it costs
an hour of the machine per attempt.

This asks the question directly. Stand on one spot and re-run the same `/vg verify` every
few seconds for several minutes, recording the entity count each time. The curve says what
the sweep needs to know:

  * the count climbs and the NPC appears  -> the settle was too short, and now we know by
    how much
  * the count plateaus early and the NPC never appears -> waiting longer is not the answer,
    and the absent verdict is about the server or the name, not the clock
  * the count stays at 1 forever -> the character is not really there (dead, wrong zone,
    a wedged client) and no verdict from that stop means anything

It writes one row per sample to data/settle_probe.csv and prints the curve. It does not
touch the ledger: these are repeated observations of the same spot, not verdicts.

    tools/settle_probe.py --game "<game dir>" --targets quest:sandoria:30,quest:wotg:16

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import csv as csvlib
import os
import sys
import time

import ledger

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, 'data', 'settle_probe.csv')


def parse_entities(why):
    """"<npc> is not loaded here (23 entities, nearest Test)" -> 23."""
    if '(' not in why:
        return None
    tail = why.split('(', 1)[1]
    head = tail.split(' ', 1)[0]
    return int(head) if head.isdigit() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', required=True)
    ap.add_argument('--targets', required=True,
                    help='comma-separated kind:area:id (kind is quest or mission)')
    ap.add_argument('--seconds', type=float, default=240.0, help='how long to watch one spot')
    ap.add_argument('--every', type=float, default=6.0, help='seconds between samples')
    # A `!pos` issued while the character is still zoning is dropped without a word, and
    # the first run of this probe spent five minutes measuring the streaming curve at the
    # zone entrance, three hundred yalms from the spot it meant to watch. The clock does not
    # start until the addon confirms the character is standing where it was sent.
    ap.add_argument('--zone-settle', type=float, default=18.0,
                    help='pause after !zone before the first !pos')
    ap.add_argument('--db', default=ledger.DB)
    ap.add_argument('--out', default=OUT)
    args = ap.parse_args()

    addon = os.path.join(args.game, 'addons', 'Vanaguide')
    cmd = os.path.join(addon, 'cmd.txt')
    csvfile = os.path.join(addon, 'verify.csv')
    if not os.path.isdir(addon):
        sys.exit('no Vanaguide addon folder at ' + addon)

    def send(line):
        with open(cmd, 'w') as fh:
            fh.write(line + '\n')

    def consumed(timeout=8.0):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if os.path.getsize(cmd) == 0:
                    return True
            except OSError:
                return True
            time.sleep(0.3)
        return False

    db = ledger.connect(args.db)
    targets = []
    for spec in args.targets.split(','):
        bits = spec.strip().split(':')
        if len(bits) != 3:
            sys.exit('a target is kind:area:id, not ' + spec)
        kind, area, qid = bits[0], bits[1], int(bits[2])
        row = db.execute('SELECT * FROM quest_state WHERE kind=? AND area=? AND id=?',
                         (kind, area, qid)).fetchone()
        if row is None:
            sys.exit(f'no such {kind} {area} {qid}')
        targets.append(dict(row))

    new = not os.path.exists(args.out)
    out = open(args.out, 'a', newline='')
    w = csvlib.writer(out)
    if new:
        w.writerow(['kind', 'area', 'id', 'npc', 'zone', 'elapsed', 'entities', 'found', 'why'])

    for q in targets:
        print(f'\n== {q["kind"]} {q["area"]} {q["id"]} "{q["name"]}" -> {q["npc"]} '
              f'in zone {q["zone"]}', flush=True)
        def sample():
            """Ask the addon once. Returns (ok, why, entities)."""
            before = os.path.getsize(csvfile) if os.path.exists(csvfile) else 0
            send('/vg verify %s%s %d' % ('m ' if q['kind'] == 'mission' else '',
                                         q['area'], q['id']))
            consumed()
            end = time.time() + 8
            while time.time() < end:
                if os.path.exists(csvfile) and os.path.getsize(csvfile) > before:
                    break
                time.sleep(0.3)
            else:
                return None
            last = open(csvfile, encoding='utf-8', errors='replace')\
                .read().strip().splitlines()[-1]
            bits = next(csvlib.reader([last]))
            bits += [''] * (15 - len(bits))
            ok, why = bits[2] == 'ok', bits[12]
            ents = bits[14]
            return ok, why, (int(ents) if ents.isdigit()
                             else (0 if ok else parse_entities(why)))

        send('!zone %d' % q['zone'])
        consumed()
        time.sleep(args.zone_settle)
        arrived = q['x'] is None
        for attempt in range(6):
            if arrived:
                break
            send('!pos %.3f %.3f %.3f %d' % (q['x'], q['y'] or 0, q['z'], q['zone']))
            consumed()
            time.sleep(4)
            got = sample()
            if got is None:
                break
            if 'from the spot' not in got[1] and 'standing in' not in got[1]:
                arrived = True
                break
            print(f'   {got[1]} — sending it again', flush=True)
        if not arrived:
            print('   never got the character onto the spot; skipping', flush=True)
            continue

        start = time.time()
        rows, found_at = [], None
        while time.time() - start < args.seconds:
            got = sample()
            if got is None:
                print('   no answer from the addon', flush=True)
                break
            ok, why, ents = got
            t = time.time() - start
            rows.append((t, ents, ok))
            w.writerow([q['kind'], q['area'], q['id'], q['npc'], q['zone'],
                        round(t, 1), ents if ents is not None else '', int(ok), why])
            out.flush()
            print(f'   {t:6.1f}s  {"" if ents is None else ents:>4} entities  '
                  f'{"FOUND" if ok else why[:70]}', flush=True)
            if ok:
                found_at = t
                break
            time.sleep(args.every)

        # The leading zeros are the empty window right after the teleport, not a reading of
        # the zone. Judging the curve with them in it made a plateau at six entities read as
        # "still climbing (0 -> 6)", which is the opposite of what the run showed.
        counts = [e for _, e, _ in rows if e is not None]
        loaded = counts[next((i for i, c in enumerate(counts) if c > 0), len(counts)):]
        if found_at is not None:
            print(f'   -> appeared after {found_at:.0f}s', flush=True)
        elif not loaded:
            print('   -> nothing ever loaded; the character is not really there and this '
                  'stop proves nothing about the guide', flush=True)
        elif len(loaded) >= 3 and max(loaded) == min(loaded):
            print(f'   -> {loaded[0]} entities arrived and no more, for '
                  f'{args.seconds:.0f}s. Waiting longer is not the answer here: the zone '
                  'finished and the NPC is not in it', flush=True)
        elif loaded[-1] > loaded[0]:
            print(f'   -> still climbing at {args.seconds:.0f}s '
                  f'({loaded[0]} -> {loaded[-1]} entities); the settle is genuinely short',
                  flush=True)
        else:
            print(f'   -> settled around {loaded[-1]} entities without the NPC appearing',
                  flush=True)

    out.close()
    print(f'\nwritten to {args.out}', flush=True)


if __name__ == '__main__':
    sys.exit(main())
