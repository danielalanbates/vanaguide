#!/usr/bin/env python3
"""Vanaguide :: tools/offline_check.py

Check every exported guide step against a LandSandBoat server's own data, without a client:
the named NPC exists in the step's zone and stands within the step's radius of its marker;
the quest / mission / key item / item the step waits for exists; the route from the previous
step's zone exists (results/routes.jsonl from tools/route_check.lua).

    tools/offline_check.py --lsb ~/Games/lsb/server --steps results/steps.jsonl \
        --routes results/routes.jsonl --db-user xiuser --db-pass ... -o results/offline.csv

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse, csv, json, math, os, re, subprocess, sys

QUEST_LOG = {'sandoria': 'SANDORIA', 'bastok': 'BASTOK', 'windurst': 'WINDURST', 'jeuno': 'JEUNO',
             'other': 'OTHER_AREAS', 'outlands': 'OUTLANDS', 'ahturhgan': 'AHT_URHGAN',
             'wotg': 'CRYSTAL_WAR', 'abyssea': 'ABYSSEA', 'adoulin': 'ADOULIN', 'coalition': 'COALITION'}
MISSION_LOG = {'sandoria': 'SANDORIA', 'bastok': 'BASTOK', 'windurst': 'WINDURST', 'zilart': 'ZILART',
               'cop': 'COP', 'toau': 'TOAU', 'wotg': 'WOTG', 'acp': 'ACP', 'amk': 'AMK', 'asa': 'ASA',
               'adoulin': 'SOA', 'rov': 'ROV', 'tvr': 'TVR'}


def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def id_blocks(path, keyword):
    """xi.quest.id / xi.mission.id: { [xi.questLog.X] = { NAME = n, ... }, ... } -> {X: {n}}"""
    text = open(path, encoding='utf-8', errors='replace').read()
    out = {}
    # Sections look like  [xi.quest.area[xi.questLog.SANDORIA]] = { NAME = 0, ... },
    for m in re.finditer(r'\[xi\.\w+\.area\[xi\.[\w.]+\.([A-Z_]+)\]\]\s*=\s*\{(.*?)\n    \}', text, re.S):
        out.setdefault(m.group(1), set()).update(int(n) for n in re.findall(r'=\s*(\d+)', m.group(2)))
    return out


def query(args, sql):
    cmd = ['/opt/homebrew/opt/mariadb/bin/mariadb', '-N', '-B', f'-u{args.db_user}',
           f'-p{args.db_pass}', 'xidb', '-e', sql]
    res = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
    if res.returncode != 0:
        sys.exit(f'SQL failed: {sql}\n{res.stderr.strip()}')
    return [l.split('\t') for l in res.stdout.splitlines() if l.split('\t')[0].strip().isdigit()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lsb', required=True)
    ap.add_argument('--steps', required=True)
    ap.add_argument('--routes', required=True)
    ap.add_argument('--db-user', default='xiuser')
    ap.add_argument('--db-pass', default='')
    ap.add_argument('-o', '--out', required=True)
    a = ap.parse_args()

    quests = id_blocks(os.path.join(a.lsb, 'scripts/globals/quests.lua'), 'questLog')
    missions = id_blocks(os.path.join(a.lsb, 'scripts/globals/missions.lua'), 'missionLog')
    kis = {int(n) for n in re.findall(r'=\s*(\d+)', open(os.path.join(a.lsb, 'scripts/enum/key_item.lua')).read())}
    items = {int(r[0]) for r in query(a, 'SELECT itemid FROM item_basic')}
    npcs = {}
    for r in query(a, "SELECT (npcid>>12)&0xFFF, polutils_name, name, pos_x, pos_z FROM npc_list"):
        if len(r) < 5:
            continue
        z = int(r[0])
        for nm in {norm(r[1]), norm(r[2])}:
            if nm:
                npcs.setdefault((z, nm), []).append((float(r[3]), float(r[4])))
    mobs = {}
    for r in query(a, "SELECT (s.mobid>>12)&0xFFF, s.polutils_name, s.mobname FROM mob_spawn_points s"):
        if len(r) < 3:
            continue
        z = int(r[0])
        for nm in {norm(r[1]), norm(r[2])}:
            if nm:
                mobs.setdefault(z, set()).add(nm)
    routes = {(r['guide'], r['step']): r for r in map(json.loads, open(a.routes))}

    rows = []
    for s in map(json.loads, open(a.steps)):
        issues = []
        zone, npc = s.get('zone'), s.get('npc') or ''
        if zone is None:
            issues.append('no location: the arrow cannot point anywhere')
        elif s.get('x') is None:
            issues.append('zone only: no marker inside the zone')
        rt = routes.get((s['guide'], s['step']))
        if rt is not None and not rt['ok']:
            issues.append(f'no route from zone {rt["from"]} to {rt["to"]}')
        marker = npc.startswith('qm') or npc.startswith('_') or '???' in npc
        npc_dist = ''
        if npc and zone is not None and not marker:
            spots = npcs.get((zone, norm(npc)))
            if not spots:
                elsewhere = sorted({z for (z, n) in npcs if n == norm(npc)})
                issues.append(f'NPC "{npc}" not in zone {zone} in npc_list'
                              + (f' (it is in {elsewhere[:5]})' if elsewhere else ' (not in npc_list at all)'))
            elif s.get('x') is not None:
                d = min(math.hypot(x - s['x'], z - s['z']) for x, z in spots)
                npc_dist = f'{d:.1f}'
                if d > (s.get('r') or 10):
                    issues.append(f'NPC "{npc}" is {d:.0f} yalms from the marker (radius {s.get("r") or 10})')
        if s['kind'] == 'kill' and zone is not None and zone in mobs:
            words = {norm(w) for w in re.findall(r"[A-Za-z][A-Za-z' -]+", s['text'])}
            if not any(m in norm(s['text']) for m in mobs[zone]):
                issues.append('kill step: no mob of this zone is named in the text')
        c, area, i = s['cond'], s.get('area'), s.get('id')
        if c in ('Q', 'QA'):
            log = QUEST_LOG.get(area)
            if log is None or i not in quests.get(log, set()):
                issues.append(f'quest {area},{i} not in LSB xi.quest.id')
        if c in ('M', 'MA'):
            log = MISSION_LOG.get(area)
            if log is None or i not in missions.get(log, set()):
                issues.append(f'mission {area},{i} not in LSB xi.mission.id')
        if c == 'KI' and s.get('ki') not in kis:
            issues.append(f'key item {s.get("ki")} not in LSB key_item enum')
        if c == 'IT' and s.get('item') not in items:
            issues.append(f'item {s.get("item")} not in item_basic')
        rows.append({'guide': s['guide'], 'guide_name': s['guide_name'], 'step': s['step'],
                     'kind': s['kind'], 'cond': c, 'zone': zone if zone is not None else '',
                     'npc': npc, 'npc_dist': npc_dist, 'text': s['text'],
                     'issues': ' ; '.join(issues), 'ok': 'ok' if not issues else 'ISSUE'})
    with open(a.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    bad = sum(1 for r in rows if r['ok'] != 'ok')
    print(f'{len(rows)} steps checked, {len(rows) - bad} clean, {bad} with at least one issue -> {a.out}')


if __name__ == '__main__':
    sys.exit(main())
