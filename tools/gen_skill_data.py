#!/usr/bin/env python3
"""Vanaguide :: tools/gen_skill_data.py

Build the data behind Server-Safe's Skills tab, where the player sets their level and gets one
recommendation (combat) or two (crafts), from a LandSandBoat checkout:

  data/craft_recipes.lua   every synthesis recipe per craft: level, other-craft requirement,
                           ingredients with the cheapest NPC price, cost, and what the result
                           sells to an NPC for (BaseSell x quantity)
  data/skill_targets.lua   ordinary monsters in the open world and dungeons: level range, zone,
                           spawn count, whether they aggro or link

    tools/gen_skill_data.py <LSB checkout> [--outdir Vanaguide/data]

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import os
import sys
from collections import defaultdict

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_loot as L                         # noqa: E402
import gen_skill_guides as SG                # noqa: E402
from gen_quests import lua_str               # noqa: E402

CRAFTS = ['Woodworking', 'Smithing', 'Goldsmithing', 'Clothcraft', 'Leathercraft', 'Bonecraft',
          'Alchemy', 'Cooking']
OUTDOORS, DUNGEON = 0x2, 0x4
MOBTYPE_NOTORIOUS = 0x2


def zone_info(sql, names_path):
    """{zone id: (name, type, level restriction)} from zone_settings.sql; display names from
    data/zone_names.lua, which keeps the apostrophes ("Northern San d'Oria")."""
    import re
    names = {}
    if os.path.exists(names_path):
        for m in re.finditer(r"\[(\d+)\]\s*=\s*'((?:[^'\\]|\\.)*)'", open(names_path, encoding='utf-8').read()):
            names[int(m.group(1))] = m.group(2).replace("\\'", "'")
    out = {}
    for r in L.rows(os.path.join(sql, 'zone_settings.sql'), 'zone_settings'):
        if len(r) >= 10:
            z = L.num(r[0])
            out[z] = (names.get(z) or r[4].replace('_', ' '), L.num(r[1]), L.num(r[9]))
    return out


def item_basic(sql):
    """{item id: (name, BaseSell)}; the flags column moved in newer LSB (name_jp)."""
    path = os.path.join(sql, 'item_basic.sql')
    head = open(path, encoding='utf-8', errors='replace').read(4000)
    sell_col = 9 if '`name_jp`' in head else 8
    out = {}
    for r in L.rows(path, 'item_basic'):
        if len(r) > sell_col:
            out[L.num(r[0])] = (L.pretty(r[2]), L.num(r[sell_col]))
    return out


def recipes(root, sql, items, buy, zones):
    out = defaultdict(list)
    for r in L.rows(os.path.join(sql, 'synth_recipes.sql'), 'synth_recipes'):
        if len(r) < 30 or L.num(r[1]):                 # desynthesis
            continue
        levels = [L.num(r[3 + i]) for i in range(8)]
        res, qty = L.num(r[21]), max(L.num(r[25]), 1)
        if res not in items or max(levels) == 0 or max(levels) > 110:
            continue
        counts = defaultdict(int)
        for i in range(13, 21):
            if L.num(r[i]):
                counts[L.num(r[i])] += 1
        cost, parts = 0, []
        for iid, n in sorted(counts.items()):
            name = items.get(iid, ('?', 0))[0]
            src = sorted(buy.get(iid, []), key=lambda s: s[2])
            label = ('%d × ' % n if n > 1 else '') + name
            if src and cost is not None:
                cost += src[0][2] * n
            if src:
                label += ' (%s, %s, %d gil)' % (src[0][0], zones.get(src[0][1], ('?',))[0], src[0][2])
            else:
                cost = None                             # someone has to farm or buy it at the AH
            parts.append(label)
        crystal = items.get(L.num(r[11]), ('Crystal', 0))[0]
        sell = items[res][1] * qty
        for c, lv in enumerate(levels):
            if lv:
                other = [(CRAFTS[i], x) for i, x in enumerate(levels) if i != c and x]
                out[c].append({'lv': lv, 'name': items[res][0] + (' ×%d' % qty if qty > 1 else ''),
                               'crystal': crystal, 'parts': parts, 'cost': cost, 'sell': sell,
                               'ki': L.num(r[2]) > 0, 'other': other})
    return out


def targets(sql, zones):
    pools = {}
    for r in L.rows(os.path.join(sql, 'mob_pools.sql'), 'mob_pools'):
        if len(r) >= 15:
            pools[L.num(r[0])] = {'aggro': L.num(r[11]) > 0, 'links': L.num(r[13]) > 0,
                                  'nm': L.num(r[14]) & MOBTYPE_NOTORIOUS > 0}
    groups = {}
    for r in L.rows(os.path.join(sql, 'mob_groups.sql'), 'mob_groups'):
        if len(r) >= 6:
            groups[(L.num(r[0]), L.num(r[2]))] = {'pool': L.num(r[1]), 'respawn': L.num(r[4]),
                                                  'spawntype': L.num(r[5])}
    mobs = {}
    for r in L.rows(os.path.join(sql, 'mob_spawn_points.sql'), 'mob_spawn_points'):
        if len(r) < 7:
            continue
        zone = (L.num(r[0]) - 0x1000000) >> 12
        g = groups.get((L.num(r[4]), zone))
        z = zones.get(zone)
        if not g or not z or g['spawntype'] != 0 or g['respawn'] <= 0:
            continue                                    # scripted, lottery or one-off spawns
        name, ztype, restriction = z
        if not ztype & (OUTDOORS | DUNGEON) or restriction:
            continue                                    # cities, battlefields, level-capped areas
        p = pools.get(g['pool'])
        lo, hi = L.num(r[5]), L.num(r[6])
        if not p or p['nm'] or lo <= 0 or hi < lo:
            continue
        key = (L.pretty(r[3] or r[2]), zone)
        m = mobs.setdefault(key, {'min': lo, 'max': hi, 'spawns': 0, 'aggro': p['aggro'], 'links': p['links']})
        m['min'], m['max'] = min(m['min'], lo), max(m['max'], hi)
        m['spawns'] += 1
    return mobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--outdir', default='Vanaguide/data')
    args = ap.parse_args()
    sql = os.path.join(args.root, 'sql')
    zones = zone_info(sql, os.path.join(args.outdir, 'zone_names.lua'))
    items = item_basic(sql)
    c = L.collect(args.root, os.path.join(args.outdir, 'quests.lua'))
    buy = defaultdict(list)                             # {item: [(npc, zone, price)]}
    for iid, vs in c['vendors'].items():
        for v in vs:
            buy[iid].append((v['npc'], v['zone'], v['price']))
    for iid, vs in SG.guild_shops(args.root, SG.GG.zone_settings(sql)).items():
        buy[iid].extend(vs)

    rec = recipes(args.root, sql, items, buy, zones)
    with open(os.path.join(args.outdir, 'craft_recipes.lua'), 'w', encoding='utf-8') as fh:
        fh.write('-- Vanaguide :: data/craft_recipes.lua\n'
                 '-- GENERATED by tools/gen_skill_data.py from a LandSandBoat checkout.  Do not hand-edit.\n'
                 '-- Recipes per craft for Server-Safe\'s Skills tab. cost = cheapest NPC prices (nil when an\n'
                 '-- ingredient is not sold by any NPC); sell = what the result sells to an NPC for.\n'
                 '--\n-- Copyright (c) 2026 Bates LLC.  All rights reserved.\n\nlocal R = {}\n\nR.crafts = {\n')
        for i, craft in enumerate(CRAFTS):
            fh.write('    { name = %s, recipes = {\n' % lua_str(craft))
            for x in sorted(rec[i], key=lambda x: (x['lv'], x['name'])):
                other = ', '.join(lua_str('%s %d' % o) for o in x['other'])
                fh.write('        { lv = %d, name = %s, crystal = %s, parts = { %s }, %ssell = %d, ki = %s, other = { %s } },\n'
                         % (x['lv'], lua_str(x['name']), lua_str(x['crystal']),
                            ', '.join(lua_str(p) for p in x['parts']),
                            '' if x['cost'] is None else 'cost = %d, ' % x['cost'], x['sell'],
                            'true' if x['ki'] else 'false', other))
            fh.write('    } },\n')
        fh.write('}\n\nreturn R\n')

    mobs = targets(sql, zones)
    with open(os.path.join(args.outdir, 'skill_targets.lua'), 'w', encoding='utf-8') as fh:
        fh.write('-- Vanaguide :: data/skill_targets.lua\n'
                 '-- GENERATED by tools/gen_skill_data.py from a LandSandBoat checkout.  Do not hand-edit.\n'
                 '-- Ordinary (not notorious) monsters with regular respawns in the open world and dungeons,\n'
                 '-- for Server-Safe\'s combat-skill recommendation.\n'
                 '--\n-- Copyright (c) 2026 Bates LLC.  All rights reserved.\n\nlocal T = {}\n\nT.mobs = {\n')
        for (name, zone), m in sorted(mobs.items(), key=lambda kv: (kv[1]['min'], kv[0])):
            fh.write('    { name = %s, zone = %d, min = %d, max = %d, spawns = %d, aggro = %s, links = %s },\n'
                     % (lua_str(name), zone, m['min'], m['max'], m['spawns'],
                        'true' if m['aggro'] else 'false', 'true' if m['links'] else 'false'))
        fh.write('}\n\nreturn T\n')
    print('%d recipes over %d crafts; %d monsters' % (sum(len(v) for v in rec.values()), len(CRAFTS), len(mobs)))


if __name__ == '__main__':
    main()
