#!/usr/bin/env python3
"""Vanaguide :: tools/gen_gear_guide.py

Build data/gear_guide.lua: every piece of equipment a player can get on a LandSandBoat server,
grouped by how it is obtained (artifact, relic, craft, quest, notorious monster, monster drop,
merchant), each with plain "how to get it" steps. VanaGuide Server-Safe's Gear tab reads it;
the in-game addon does not load it.

Everything comes from the server's own data, the same way tools/gen_loot.py and
tools/gen_quests.py work:
  artifact armor   scripts/globals/equipment.lua `artifactArmorRanges`
  relic weapons    scripts/zones/Castle_Zvahl_Baileys/npcs/Switchstix.lua (stages 1-4) and the
                   zones' npcs/relic*.lua (the final trade), xi.equipment.relicIDs (later tiers)
  relic armor      equipment dropped by monsters in the Dynamis zones
  crafts           sql/synth_recipes.sql (enabled rows only)
  quests           data/quests.lua `rewards` (written by gen_quests.py)
  drops, merchants gen_loot.collect()

    tools/gen_gear_guide.py <path to a LandSandBoat checkout> [--out Vanaguide/data/gear_guide.lua]

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_loot as L  # noqa: E402

JOBS = ['WAR', 'MNK', 'WHM', 'BLM', 'RDM', 'THF', 'PLD', 'DRK', 'BST', 'BRD', 'RNG', 'SAM',
        'NIN', 'DRG', 'SMN', 'BLU', 'COR', 'PUP', 'DNC', 'SCH', 'GEO', 'RUN']
CRAFTS = ['Woodworking', 'Smithing', 'Goldsmithing', 'Clothcraft', 'Leathercraft', 'Bonecraft',
          'Alchemy', 'Cooking']
CATEGORIES = [
    ('artifact', 'Artifact Armor', "Each job's own armor, earned through that job's artifact quests."),
    ('relic', 'Relic Weapons', 'The legendary weapons: a base weapon upgraded in stages with Dynamis currency.'),
    ('dynamis', 'Relic Armor (Dynamis)', 'Armor that drops from monsters in Dynamis.'),
    ('craft', 'Craftable', 'Made by synthesis. Shows the craft, its level and the ingredients.'),
    ('quest', 'Quest Rewards', 'Given for finishing a quest.'),
    ('nm', 'Notorious Monster Drops', 'Dropped by named, rarer monsters.'),
    ('drop', 'Monster Drops', 'Dropped by ordinary monsters.'),
    ('vendor', 'Merchants', 'Sold by an NPC.'),
]


def jobs_text(mask):
    if mask == 0 or mask & ((1 << 22) - 1) == (1 << 22) - 1:
        return 'All jobs'
    return ' '.join(j for i, j in enumerate(JOBS) if mask & (1 << i))


def zone_settings(sql):
    """{zone id: folder name}"""
    out = {}
    for r in L.rows(os.path.join(sql, 'zone_settings.sql'), 'zone_settings'):
        if len(r) >= 5:
            out[L.num(r[0])] = r[4]       # (id, type, ip, port, name, ...)
    return out


def zone_enum(root):
    out = {}
    for line in open(os.path.join(root, 'scripts/enum/zone.codegen.lua'), encoding='utf-8'):
        m = re.match(r"\s*([A-Z][A-Z0-9_]*)\s*=\s*(\d+)", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def quest_scripts(root, enum, zones):
    """Rewards the quest scripts hand out that data/quests.lua does not list:
    `quest.reward = { item = ... }`, Borghertz's `handAFId`, and the artifact pieces a quest
    puts in a treasure coffer (`xi.treasure.onTrade(..., 1, xi.item.X)`).
    {item id: [(kind, quest title, area, zone or None, extra)]}"""
    out = defaultdict(list)
    base = os.path.join(root, 'scripts/quests')
    for dirpath, _, files in os.walk(base):
        for f in sorted(files):
            if not f.endswith('.lua'):
                continue
            text = open(os.path.join(dirpath, f), encoding='utf-8', errors='replace').read()
            q = re.search(r"xi\.quest\.id\.(\w+)\.(\w+)", text)
            if not q:
                continue
            area, title = q.group(1), L.pretty(q.group(2).lower()).title()
            r = re.search(r"quest\.reward\s*=\s*\{(.*?)\n\}", text, re.S)
            if r:
                for k in re.findall(r"xi\.item\.(\w+)", r.group(1)):
                    if k in enum:
                        out[enum[k]].append(('quest', title, area, None, ''))
            h = re.search(r"handAFId\s*=\s*xi\.item\.(\w+)", text)
            g = re.search(r"oldGauntletZoneId\s*=\s*xi\.zone\.(\w+)", text)
            if h and h.group(1) in enum:
                extra = ' The Old Gauntlets it needs come from a treasure coffer there.' if g else ''
                out[enum[h.group(1)]].append(('quest', title, area, zones.get(g.group(1)) if g else None, extra))
            for m in re.finditer(r"xi\.treasure\.onTrade\(\s*player\s*,\s*npc\s*,\s*trade\s*,\s*1\s*,\s*xi\.item\.(\w+)", text):
                if m.group(1) not in enum:
                    continue
                zs = re.findall(r"\[xi\.zone\.(\w+)\]", text[:m.start()])
                zone = zones.get(zs[-1]) if zs else None
                out[enum[m.group(1)]].append(('coffer', title, area, zone, ''))
    return out


def artifact_ids(root, enum):
    text = open(os.path.join(root, 'scripts/globals/equipment.lua'), encoding='utf-8').read()
    block = text[text.index('artifactArmorRanges'):]
    block = block[:block.index('\n}')]
    out = set()
    for a, b in re.findall(r"\{\s*xi\.item\.(\w+)\s*,\s*xi\.item\.(\w+)\s*\}", block):
        if a in enum and b in enum:
            out.update(range(enum[a], enum[b] + 1))
    return out


def relic_chains(root, enum, names, zone_folders):
    """{item id: [how lines]} for every relic stage and its final weapon."""
    how = defaultdict(list)
    path = os.path.join(root, 'scripts/zones/Castle_Zvahl_Baileys/npcs/Switchstix.lua')
    zid = {v: k for k, v in zone_folders.items()}
    name = lambda key: names.get(enum.get(key), key.replace('_', ' ').title())  # noqa: E731
    if os.path.exists(path):
        text = open(path, encoding='utf-8').read()
        groups = re.split(r"\n\s*-- (\w[\w' ]*)\n", text[text.index('local relics'):])
        # groups = [preamble, weapon, body, weapon, body, ...]
        for weapon, body in zip(groups[1::2], groups[2::2]):
            stages = re.findall(r"\[xi\.item\.(\w+)\]\s*=\s*\{\s*\{([^}]*)\}\s*,\s*xi\.item\.(\w+)\s*,\s*(\d+)",
                                body)
            chain = [s[0] for s in stages]
            for i, (base, need, cur, amount) in enumerate(stages):
                parts = ', '.join(name(k) for k in re.findall(r"xi\.item\.(\w+)", need))
                step = ('Trade %s, %s and %s × %s to Switchstix'
                        % (name(base), parts, amount, name(cur)))
                target = chain[i + 1] if i + 1 < len(chain) else None
                if target and target in enum:
                    how[enum[target]].append(('relic', step, zid.get('Castle_Zvahl_Baileys'), 'Switchstix'))
            if chain:
                how[enum.get(chain[0], -1)].append(('relic', 'The first stage of %s. Start the relic upgrade with Switchstix' % weapon, zid.get('Castle_Zvahl_Baileys'), 'Switchstix'))
    zones_dir = os.path.join(root, 'scripts/zones')
    for folder in sorted(os.listdir(zones_dir)):
        npcs = os.path.join(zones_dir, folder, 'npcs')
        if not os.path.isdir(npcs):
            continue
        for f in sorted(os.listdir(npcs)):
            if not (f.startswith('relic') and f.endswith('.lua')):
                continue
            text = open(os.path.join(npcs, f), encoding='utf-8').read()
            trade = re.search(r"tradeHas\(trade,\s*\{([^}]*)\}", text)
            give = re.search(r"giveItem\(player,\s*\{?\s*xi\.item\.(\w+)", text)
            if not (trade and give and give.group(1) in enum):
                continue
            parts = ', '.join(name(k) for k in re.findall(r"xi\.item\.(\w+)", trade.group(1)))
            how[enum[give.group(1)]].append(
                ('relic', 'Trade %s to the ??? marker (the final stage)' % parts, zid.get(folder), '???'))
    # Later tiers (80-119) upgrade the one before; this server may not have those stages.
    text = open(os.path.join(root, 'scripts/globals/equipment.lua'), encoding='utf-8').read()
    for block in re.findall(r"\]\s*=\s*\{([^}]*)\}", text[text.index('relicIDs'):text.index('artifactArmorRanges')]):
        tiers = [enum[k] for k in re.findall(r"xi\.item\.(\w+)", block) if k in enum]
        for prev, cur in zip(tiers, tiers[1:]):
            if cur not in how:
                how[cur].append(('relic', 'Upgrade %s (a later tier; this server may not offer it yet)'
                                 % names.get(prev, prev), None, None))
    return how


def recipes(sql, items):
    """{result item id: [(craft line, crystal, ingredients)]} from enabled synthesis rows."""
    out = defaultdict(list)
    for r in L.rows(os.path.join(sql, 'synth_recipes.sql'), 'synth_recipes'):
        if len(r) < 30 or L.num(r[1]):           # desynthesis rows give materials back
            continue
        levels = [(CRAFTS[i], L.num(r[3 + i])) for i in range(8) if L.num(r[3 + i])]
        if not levels:
            continue
        levels.sort(key=lambda t: -t[1])
        craft = ', '.join('%s %d' % t for t in levels)
        crystal = items.get(L.num(r[11]), {}).get('name', 'crystal')
        counts = defaultdict(int)
        for i in range(13, 21):
            if L.num(r[i]):
                counts[L.num(r[i])] += 1
        parts = ', '.join(('%d × %s' % (n, items[i]['name'])) if n > 1 else items[i]['name']
                          for i, n in counts.items() if i in items)
        for res in {L.num(r[21]), L.num(r[22]), L.num(r[23]), L.num(r[24])}:
            hq = res != L.num(r[21])
            out[res].append((craft, crystal, parts, hq))
    return out


def quest_index(path):
    """{(area, normalized name): (name, zone, npc)} for every quest in data/quests.lua."""
    out, area = {}, None
    for line in open(path, encoding='utf-8'):
        m = re.match(r"    (\w+) = \{$", line)
        if m:
            area = m.group(1)
            continue
        m = re.search(r"\[\d+\] = \{ name = '((?:[^'\\]|\\.)*)'", line)
        if m and area:
            name = m.group(1).replace("\\'", "'")
            z = re.search(r"zone = (\d+)", line)
            n = re.search(r"npc = '((?:[^'\\]|\\.)*)'", line)
            out[(area, norm(name))] = (name, int(z.group(1)) if z else None, n.group(1) if n else None)
    return out


def norm(s):
    return re.sub(r"[^a-z0-9]", '', s.lower())


def quest_rewards(path):
    """{item id: [(area, quest name, zone, npc)]} from data/quests.lua."""
    out = defaultdict(list)
    area = None
    for line in open(path, encoding='utf-8'):
        m = re.match(r"    (\w+) = \{$", line)
        if m:
            area = m.group(1)
            continue
        m = re.search(r"\[\d+\] = \{ name = '((?:[^'\\]|\\.)*)'.*?rewards = \{([^}]*)\}", line)
        if not (m and area):
            continue
        z = re.search(r"zone = (\d+)", line)
        n = re.search(r"npc = '((?:[^'\\]|\\.)*)'", line)
        for iid in re.findall(r"\d+", m.group(2)):
            out[int(iid)].append((area, m.group(1).replace("\\'", "'"),
                                  int(z.group(1)) if z else None, n.group(1) if n else None))
    return out


AREAS = {'sandoria': "San d'Oria", 'bastok': 'Bastok', 'windurst': 'Windurst', 'jeuno': 'Jeuno',
         'other': 'Other Areas', 'outlands': 'Outlands', 'ahturhgan': 'Aht Urhgan',
         'wotg': 'Crystal War', 'abyssea': 'Abyssea', 'adoulin': 'Adoulin', 'coalition': 'Coalition'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--quests', default='Vanaguide/data/quests.lua')
    ap.add_argument('--out', default='Vanaguide/data/gear_guide.lua')
    args = ap.parse_args()
    sql = os.path.join(args.root, 'sql')
    c = L.collect(args.root, args.quests)
    items, equipment = c['items'], c['equipment']
    names = {i: v['name'] for i, v in items.items()}
    enum = L.parse_item_enum(args.root)
    folders = zone_settings(sql)
    dynamis = {z for z, f in folders.items() if f.startswith('Dynamis')}
    af = artifact_ids(args.root, enum)
    relic = relic_chains(args.root, enum, names, folders)
    crafts = recipes(sql, items)
    quests = quest_rewards(args.quests)
    scripted = quest_scripts(args.root, enum, zone_enum(args.root))
    qindex = quest_index(args.quests)

    rows = []
    for iid, eq in equipment.items():
        if iid not in items:
            continue
        how, cats = [], []
        if iid in af:
            cats.append('artifact')
        if iid in relic:
            cats.append('relic')
            how += relic[iid]
        for area, qname, zone, npc in quests.get(iid, []):
            how.append(('quest', 'Quest: %s (%s)' % (qname, AREAS.get(area, area.title())), zone, npc))
        listed = {norm(qname) for _, qname, _, _ in quests.get(iid, [])}
        for kind, title, area, zone, extra in scripted.get(iid, []):
            where = AREAS.get(area, area.title())
            known = qindex.get((area, norm(title)))
            npc = None
            if known:
                title = known[0]
                if kind == 'quest' and zone is None:
                    zone, npc = known[1], known[2]
            if kind == 'coffer':
                how.append(('quest', 'Treasure coffer, opened during the quest %s (%s)' % (title, where), zone, None))
            elif norm(title) not in listed:
                how.append(('quest', ('Quest: %s (%s).%s' % (title, where, extra)).rstrip('.'), zone, npc))
        if (iid in quests or iid in scripted) and 'quest' not in cats:
            cats.append('quest')
        for craft, crystal, parts, hq in crafts.get(iid, [])[:3]:
            how.append(('craft', '%s%s: %s + %s' % ('High-quality result of ' if hq else '', craft, crystal, parts),
                        None, None))
        if iid in crafts:
            cats.append('craft')
        drops = sorted(c['drops'].get(iid, []), key=lambda d: (not d['nm'], -d['rate']))
        if any(d['zone'] in dynamis for d in drops):
            cats.append('dynamis')
        if any(d['nm'] for d in drops):
            cats.append('nm')
        if any(not d['nm'] and d['zone'] not in dynamis for d in drops):
            cats.append('drop')
        seen = set()
        for d in drops:
            if (d['mob'], d['zone']) in seen or len(seen) >= 4:
                continue
            seen.add((d['mob'], d['zone']))
            how.append(('nm' if d['nm'] else 'drop',
                        '%s %s (%.1f%%)' % ('Notorious monster' if d['nm'] else 'Dropped by', d['mob'], d['rate']),
                        d['zone'], None))
        vend = sorted(c['vendors'].get(iid, []), key=lambda v: v['price'])
        if vend:
            cats.append('vendor')
        for v in vend[:3]:
            how.append(('vendor', 'Sold by %s for %d gil' % (v['npc'], v['price']), v['zone'], v['npc']))
        if not cats:
            continue
        if 'artifact' in cats and not how:
            how.append(('quest', "Not handed out by this server's scripts yet. On retail it comes from a "
                        "treasure coffer during your job's artifact quests.", None, None))
        rows.append((iid, eq, cats, how))

    rows.sort(key=lambda r: (r[1]['level'], items[r[0]]['name']))
    q = L.lua_str
    with open(args.out, 'w', encoding='utf-8') as fh:
        fh.write("-- Vanaguide :: data/gear_guide.lua\n"
                 "-- GENERATED by tools/gen_gear_guide.py from a LandSandBoat checkout.  Do not hand-edit.\n"
                 "-- Every obtainable piece of equipment, by how it is obtained. Read by VanaGuide\n"
                 "-- Server-Safe's Gear tab; the in-game addon does not load it.\n"
                 "-- how = { kind, text, zone id or nil, npc or nil }\n"
                 "--\n-- Copyright (c) 2026 Bates LLC.  All rights reserved.\n\n"
                 "local G = {}\n\nG.categories = {\n")
        count = defaultdict(int)
        for _, _, cats, _ in rows:
            for k in cats:
                count[k] += 1
        for key, name, desc in CATEGORIES:
            fh.write("    { id = %s, name = %s, desc = %s, count = %d },\n" % (q(key), q(name), q(desc), count[key]))
        fh.write("}\n\nG.items = {\n")
        for iid, eq, cats, how in rows:
            f = items[iid]['flags']
            hows = ', '.join('{ %s, %s, %s, %s }' % (q(k), q(t), 'nil' if z is None else z, 'nil' if n is None else q(n))
                             for k, t, z, n in how)
            fh.write("    { id = %d, name = %s, level = %d, slot = %s, jobs = %s, rare = %s, ex = %s, cats = %s, how = { %s } },\n"
                     % (iid, q(items[iid]['name']), eq['level'], q(L.slot_name(eq['slot']) or 'other'),
                        q(jobs_text(eq['jobs'])), 'true' if f & L.FLAG_RARE else 'false',
                        'true' if f & L.FLAG_EX else 'false', q(' '.join(cats)), hows))
        fh.write("}\n\nreturn G\n")
    print('%d pieces of equipment: %s' % (len(rows), ', '.join('%s %d' % (k, count[k]) for k, _, _ in CATEGORIES)))


if __name__ == '__main__':
    main()
