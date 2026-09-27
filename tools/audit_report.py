#!/usr/bin/env python3
"""Vanaguide :: tools/audit_report.py -- grade every audited step from audit.csv.

    tools/audit_report.py <audit.csv> --steps results/steps.jsonl [-o docs/AUDIT_RESULTS.md]

Per step (the last 'pre' row taken in the step's zone, and the 'done' row after it):
  arrow     pass when the arrow says 'here' and the character is inside the step's radius
            (zone-only steps: in the zone)
  target    pass when the named NPC is loaded there; n/a when the step names nobody
  condition pass when it read open before and done after the server completed it;
            'already' when it was already done before (cannot be told apart);
            FAIL when it stayed open after the server completed it
  path      navmesh / straight (straight is not a failure: small zones and dungeons may lack a grid)

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse, collections, csv, json, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('audit')
    ap.add_argument('--steps', required=True)
    ap.add_argument('-o', '--out')
    a = ap.parse_args()
    steps = {(s['guide'], s['step']): s for s in map(json.loads, open(a.steps))}
    pre, done = {}, {}
    for r in csv.reader(open(a.audit, encoding='utf-8', errors='replace')):
        if len(r) < 17:
            continue
        key = (int(r[0]), int(r[1]))
        row = dict(phase=r[2], kind=r[3], want=r[4], zone=r[5], mode=r[6], dist=r[7], radius=r[8],
                   inside=r[9], npc=r[10], present=r[11], cond=r[14], path=r[15], why=r[16])
        if row['phase'] == 'pre' and (row['want'] == '' or row['want'] == row['zone']):
            pre[key] = row
            done.pop(key, None)
        elif row['phase'] == 'done' and key in pre:
            done[key] = row
    grades = {}
    for key, p in pre.items():
        s = steps.get(key, {})
        d = done.get(key)
        arrow = 'n/a' if p['want'] == '' else ('pass' if p['inside'] == 'inside' else 'FAIL')
        target = 'n/a' if not p['npc'] else ('pass' if p['present'] == 'present' else 'FAIL')
        if s.get('cond') in (None, 'manual'):
            cond = 'n/a'
        elif p['cond'] == 'done':
            cond = 'already'
        elif d is None:
            cond = 'untested'
        else:
            cond = 'pass' if d['cond'] == 'done' else 'FAIL'
        path = 'navmesh' if 'path navmesh' in p['path'] else ('straight' if 'straight' in p['path'] else 'none')
        grades[key] = dict(arrow=arrow, target=target, cond=cond, path=path, why=p['why'],
                           npc=p['npc'], text=s.get('text', ''), guide_name=s.get('guide_name', ''),
                           cond_kind=s.get('cond'), dist=p['dist'], zone=p['want'])
    tot = collections.Counter()
    for g in grades.values():
        for k in ('arrow', 'target', 'cond'):
            tot[(k, g[k])] += 1
        tot[('path', g['path'])] += 1
    lines = [f'# Guide audit: in-game results', '',
             f'{len(grades)} of {len(steps)} steps audited in game.', '',
             '| check | pass | FAIL | other |', '|---|---|---|---|']
    for k in ('arrow', 'target', 'cond'):
        other = {v: n for (kk, v), n in tot.items() if kk == k and v not in ('pass', 'FAIL')}
        lines.append(f"| {k} | {tot[(k, 'pass')]} | {tot[(k, 'FAIL')]} | "
                     + ', '.join(f'{v} {n}' for v, n in sorted(other.items())) + ' |')
    lines.append(f"| path | navmesh {tot[('path', 'navmesh')]} | | straight {tot[('path', 'straight')]}, none {tot[('path', 'none')]} |")
    lines += ['', '## Failures', '', '| step | guide | what | detail |', '|---|---|---|---|']
    for key in sorted(grades):
        g = grades[key]
        bad = [k for k in ('arrow', 'target', 'cond') if g[k] == 'FAIL']
        if bad:
            detail = f"{g['text'][:50]} | npc={g['npc']} dist={g['dist']} cond={g['cond_kind']} | {g['why'][:80]}"
            lines.append(f"| {key[0]}/{key[1]} | {g['guide_name'][:28]} | {', '.join(bad)} | {detail} |")
    out = '\n'.join(lines) + '\n'
    if a.out:
        open(a.out, 'w').write(out)
    print(out[:4000])


if __name__ == '__main__':
    sys.exit(main())
