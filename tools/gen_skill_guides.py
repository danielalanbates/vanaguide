#!/usr/bin/env python3
"""Vanaguide :: tools/gen_skill_guides.py

Build data/skill_guides.lua: a levelling guide for every skill, from a LandSandBoat checkout.

  crafts   one step per 10 levels: recipes whose cap falls in that band (sql/synth_recipes.sql),
           cheapest first, with where to buy each ingredient (merchants and guild shops)
  fishing  one step per 10 levels: fish whose skill falls in that band (sql/fishing_fish.sql),
           where they bite (fishing_catch/fishing_group) and the bait they take
  combat and magic skills
           which jobs have the skill and its cap at each level (sql/skill_ranks.sql,
           sql/skill_caps.sql), and how it rises

VanaGuide Server-Safe's Skills tab reads it; the in-game addon does not load it.

    tools/gen_skill_guides.py <path to a LandSandBoat checkout> [--out Vanaguide/data/skill_guides.lua]

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_loot as L  # noqa: E402
import gen_gear_guide as GG  # noqa: E402

COMBAT_NAMES = {
    'hand2hand': 'Hand-to-Hand', 'great sword': 'Great Sword', 'great axe': 'Great Axe',
    'great katana': 'Great Katana', 'divine': 'Divine Magic', 'healing': 'Healing Magic',
    'enhancing': 'Enhancing Magic', 'enfeebling': 'Enfeebling Magic', 'elemental': 'Elemental Magic',
    'dark': 'Dark Magic', 'summoning': 'Summoning Magic', 'blue': 'Blue Magic',
    'singing': 'Singing', 'string': 'String Instrument', 'wind': 'Wind Instrument',
    'geomancy': 'Geomancy', 'handbell': 'Handbell',
}
MAGIC = {'divine', 'healing', 'enhancing', 'enfeebling', 'elemental', 'dark', 'summoning', 'ninjutsu',
         'singing', 'string', 'wind', 'blue', 'geomancy', 'handbell'}
DEFENSIVE = {'guarding', 'evasion', 'shield', 'parrying'}


def guild_shops(root, folders):
    """{item id: [(npc, zone, price)]} from scripts/data/guild_shops.lua. The shop's zone is
    the folder its NPC script lives in."""
    path = os.path.join(root, 'scripts/data/guild_shops.lua')
    if not os.path.exists(path):
        return {}
    enum = L.parse_item_enum(root)
    zid = {v: k for k, v in folders.items()}
    npc_zone = {}
    zdir = os.path.join(root, 'scripts/zones')
    for folder in os.listdir(zdir):
        nd = os.path.join(zdir, folder, 'npcs')
        if os.path.isdir(nd):
            for f in os.listdir(nd):
                npc_zone.setdefault(f[:-4], zid.get(folder))
    out = defaultdict(list)
    text = open(path, encoding='utf-8').read()
    for m in re.finditer(r"\['([^']+)'\]\s*=\s*\{(.*?)\n    \},", text, re.S):
        npc, body = m.group(1), m.group(2)
        zone = npc_zone.get(npc) or npc_zone.get(npc.replace(' ', '_'))
        for k, price in re.findall(r"id\s*=\s*xi\.item\.(\w+).*?buyMax\s*=\s*(\d+)", body):
            if k in enum and zone is not None:
                out[enum[k]].append((npc.replace('_', ' '), zone, int(price)))
    return out


def craft_guides(sql, items, buy, zone_name):
    recipes = defaultdict(list)            # craft index -> [(level, name, crystal, parts, cost, ok, other)]
    for r in L.rows(os.path.join(sql, 'synth_recipes.sql'), 'synth_recipes'):
        if len(r) < 30 or L.num(r[1]):
            continue
        levels = [L.num(r[3 + i]) for i in range(8)]
        res = L.num(r[21])
        if res not in items:
            continue
        counts = defaultdict(int)
        for i in range(13, 21):
            if L.num(r[i]):
                counts[L.num(r[i])] += 1
        cost, ok, parts = 0, True, []
        for iid, n in counts.items():
            name = items.get(iid, {}).get('name', '?')
            src = sorted(buy.get(iid, []), key=lambda s: s[2])
            if src:
                cost += src[0][2] * n
                parts.append('%s%s (%s, %s, %d gil)' % ('%d × ' % n if n > 1 else '', name, src[0][0],
                                                         zone_name(src[0][1]), src[0][2]))
            else:
                ok = False
                cost += 10 ** 6
                parts.append('%s%s' % ('%d × ' % n if n > 1 else '', name))
        crystal = items.get(L.num(r[11]), {}).get('name', 'crystal')
        for c, lv in enumerate(levels):
            if lv:
                other = max([x for i, x in enumerate(levels) if i != c] or [0])
                recipes[c].append((lv, items[res]['name'], crystal, parts, cost, ok, other))
    out = []
    for c, craft in enumerate(GG.CRAFTS):
        steps = []
        for lo in range(0, 110, 10):
            band = [x for x in recipes[c] if lo < x[0] <= lo + 10]
            if not band:
                continue
            band.sort(key=lambda x: (x[6] > lo, not x[5], x[4], x[0]))
            picked, seen = [], set()
            for x in band:                      # one recipe per result: the cheapest
                if x[1] not in seen:
                    seen.add(x[1])
                    picked.append(x)
            lines = []
            for lv, name, crystal, parts, cost, ok, other in picked[:4]:
                lines.append('• %s (cap %d)%s: %s + %s'
                             % (name, lv, '' if other == 0 else ', also needs another craft at %d' % other,
                                crystal, ', '.join(parts)))
            steps.append(('%s %d–%d' % (craft, lo, lo + 10),
                          'Synthesize one of these until it stops giving skill, then move on. Cheapest first. Merchant '
                          'prices are fixed; guild shop prices are the most they charge.\n' + '\n'.join(lines)))
        out.append((craft, 'Crafting', 'Recipes to level %s from 0, by level band.' % craft, steps))
    return out


def fishing_guide(sql, items, buy, zone_name):
    fish = {}
    for r in L.rows(os.path.join(sql, 'fishing_fish.sql'), 'fishing_fish'):
        if len(r) >= 3:
            fish[L.num(r[0])] = (r[1], L.num(r[2]))
    groups = defaultdict(set)
    for r in L.rows(os.path.join(sql, 'fishing_group.sql'), 'fishing_group'):
        groups[L.num(r[0])].add(L.num(r[1]))
    where = defaultdict(set)
    for r in L.rows(os.path.join(sql, 'fishing_catch.sql'), 'fishing_catch'):
        for f in groups.get(L.num(r[2]), ()):
            where[f].add(L.num(r[0]))
    baits = {L.num(r[0]): r[1] for r in L.rows(os.path.join(sql, 'fishing_bait.sql'), 'fishing_bait')}
    takes = defaultdict(list)
    for r in L.rows(os.path.join(sql, 'fishing_bait_affinity.sql'), 'fishing_bait_affinity'):
        takes[L.num(r[1])].append((L.num(r[2]), L.num(r[0])))
    steps = []
    for lo in range(0, 110, 10):
        band = [(sk, n, f) for f, (n, sk) in fish.items() if lo < sk <= lo + 10 and where.get(f) and takes.get(f)]
        if not band:
            continue
        def bait_text(f):
            best = sorted(takes.get(f, []), reverse=True)
            for _, b in best:
                src = sorted(buy.get(b, []), key=lambda s: s[2])
                if src:
                    return '%s (%s, %s, %d gil)' % (baits.get(b, '?'), src[0][0], zone_name(src[0][1]), src[0][2])
            return baits.get(best[0][1], '?')
        band.sort(key=lambda t: (-len(where[t[2]]), t[0]))
        lines = ['• %s (skill %d) in %s, on %s'
                 % (n, sk, ', '.join(zone_name(z) for z in sorted(where[f])[:3]), bait_text(f))
                 for sk, n, f in band[:4]]
        steps.append(('Fishing %d–%d' % (lo, lo + 10),
                      'Fish for one of these. Skill rises fastest on fish a little above your level.\n' + '\n'.join(lines)))
    return [('Fishing', 'Crafting', 'Where and what to fish, by skill band.', steps)]


def combat_guides(sql):
    caps = {}
    for r in L.rows(os.path.join(sql, 'skill_caps.sql'), 'skill_caps'):
        caps[L.num(r[0])] = [L.num(x) for x in r[1:]]
    out = []
    for r in L.rows(os.path.join(sql, 'skill_ranks.sql'), 'skill_ranks'):
        key = r[1]
        ranks = [L.num(x) for x in r[2:24]]
        jobs = [(GG.JOBS[i], rk) for i, rk in enumerate(ranks) if rk]
        if not jobs:
            continue
        name = COMBAT_NAMES.get(key, key.title())
        top = max(caps)
        jobs.sort(key=lambda j: j[1])
        cap = lambda lv, rk: caps.get(lv, [0] * 14)[rk] if rk < 14 else 0  # noqa: E731
        who = '\n'.join('• %s: %d at level 75%s' % (j, cap(75, rk), '' if top <= 75 else ', %d at %d' % (cap(top, rk), top))
                        for j, rk in jobs)
        best = jobs[0]
        table = ', '.join('%d → %d' % (lv, cap(lv, best[1])) for lv in (10, 20, 30, 40, 50, 60, 70, 75) if lv in caps)
        if key in MAGIC:
            how = ('Cast spells of this skill on monsters (or, for buffs and cures, on yourself and party members '
                   'while in combat with a monster that gives experience). Skill rises fastest while far below '
                   'your cap, so cast often after each level.')
        elif key in DEFENSIVE:
            how = ('Rises when monsters attack you and the skill comes into play (blocking, parrying, evading, '
                   'guarding). Let monsters that give experience hit you; "Even Match" or tougher work best.')
        else:
            how = ('Fight with this weapon type against monsters that give experience ("Easy Prey" or tougher). '
                   'Each swing can raise it; it rises fastest while far below your cap. If you are far below cap, '
                   'fight weaker monsters for longer instead of strong ones.')
        steps = [('Who Can Use It', 'Skill cap by job, from this server\'s tables:\n' + who),
                 ('How It Rises', how),
                 ('Caps by Level (%s)' % best[0], 'Level → cap: ' + table + '. Keep the skill near the cap for '
                  'your level before moving on to tougher areas.')]
        out.append((name, 'Magic' if key in MAGIC else ('Defense' if key in DEFENSIVE else 'Combat'),
                    'Levelling %s: who has it, caps and how it rises.' % name, steps))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--quests', default='Vanaguide/data/quests.lua')
    ap.add_argument('--zones', default='Vanaguide/data/zone_names.lua')
    ap.add_argument('--out', default='Vanaguide/data/skill_guides.lua')
    args = ap.parse_args()
    sql = os.path.join(args.root, 'sql')
    c = L.collect(args.root, args.quests)
    items = c['items']
    folders = GG.zone_settings(sql)
    names = {}
    if os.path.exists(args.zones):
        for m in re.finditer(r"\[(\d+)\]\s*=\s*'((?:[^'\\]|\\.)*)'", open(args.zones, encoding='utf-8').read()):
            names[int(m.group(1))] = m.group(2).replace("\\'", "'")
    zone_name = lambda z: names.get(z) or folders.get(z, '?').replace('_', ' ')  # noqa: E731
    buy = defaultdict(list)
    for iid, vs in c['vendors'].items():
        for v in vs:
            buy[iid].append((v['npc'], v['zone'], v['price']))
    for iid, vs in guild_shops(args.root, folders).items():
        buy[iid] += vs
    guides = craft_guides(sql, items, buy, zone_name) + fishing_guide(sql, items, buy, zone_name) + combat_guides(sql)
    q = lambda v: L.lua_str(v).replace('\n', '\\n')  # noqa: E731
    with open(args.out, 'w', encoding='utf-8') as fh:
        fh.write("-- Vanaguide :: data/skill_guides.lua\n"
                 "-- GENERATED by tools/gen_skill_guides.py from a LandSandBoat checkout.  Do not hand-edit.\n"
                 "-- A levelling guide per skill. Read by VanaGuide Server-Safe's Skills tab.\n"
                 "--\n-- Copyright (c) 2026 Bates LLC.  All rights reserved.\n\nlocal S = {}\n\nS.guides = {\n")
        for name, group, desc, steps in guides:
            st = ',\n'.join('            { title = %s, note = %s }' % (q(t), q(n)) for t, n in steps)
            fh.write("    { name = %s, group = %s, desc = %s, steps = {\n%s\n    } },\n" % (q(name), q(group), q(desc), st))
        fh.write("}\n\nreturn S\n")
    print('%d skill guides: %s' % (len(guides), ', '.join('%s %d' % (n, len(s)) for n, _, _, s in guides[:10])))


if __name__ == '__main__':
    main()
