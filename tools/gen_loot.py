#!/usr/bin/env python3
"""Vanaguide :: tools/gen_loot.py

Build the loot, gear and notorious-monster databases from a LandSandBoat checkout's SQL.

Same argument as tools/gen_quests.py (docs/QUEST_DATABASE.md): the server's tables are what
actually decides what drops from what, so they are the source rather than a wiki's prose
about retail.  Three files come out:

    data/nm.lua      notorious monsters: where they spawn, what level, what they drop
    data/drops.lua   item id -> the mobs that drop it, with the server's own drop rates
    data/gear.lua    equipment that has a findable source: level, jobs, slot, rare/ex

Everything is filtered to what a guide can act on.  An item nothing drops, or a mob with no
spawn point, cannot be pointed at, so it is left out rather than padding the client's memory.

    tools/gen_loot.py <path to a LandSandBoat checkout>

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import os
import re
import sys
from collections import defaultdict

FLAG_EX, FLAG_RARE, FLAG_EQUIP = 0x4000, 0x8000, 0x0800
MOBTYPE_NOTORIOUS = 0x02

# FFXI equipment slot bits.
SLOTS = [
    (0x0001, 'main'), (0x0002, 'sub'), (0x0004, 'ranged'), (0x0008, 'ammo'),
    (0x0010, 'head'), (0x0020, 'body'), (0x0040, 'hands'), (0x0080, 'legs'),
    (0x0100, 'feet'), (0x0200, 'neck'), (0x0400, 'waist'), (0x0800, 'ear'),
    (0x2000, 'ring'), (0x8000, 'back'),
]


def rows(path, table):
    """Yield each VALUES tuple of `INSERT INTO \\`table\\`` as a list of raw strings.

    LandSandBoat writes drop rates as SQL variables -- `SET @COMMON = 150;` at the top of the
    file, then `VALUES (15,0,0,1000,637,@COMMON)`. Reading those as numbers gives 0, which
    silently turns every drop rate in the game into "never". They are substituted here.
    """
    text = open(path, encoding='utf-8', errors='replace').read()
    variables = {m.group(1): m.group(2)
                 for m in re.finditer(r"SET\s+@(\w+)\s*=\s*([\-\d.]+)\s*;", text)}
    # Every dump line carries a trailing `-- Lizard Tail (Common, 15%)`. Those parentheses
    # look exactly like a row to the tuple scanner, and the statement terminator is *before*
    # them, so leaving them in makes a VALUES body run on to the next statement.
    text = strip_comments(text)
    pattern = re.compile(r"INSERT INTO `%s`[^V]*VALUES\s*(.+?);" % re.escape(table), re.S)
    for m in pattern.finditer(text):
        body = m.group(1)
        for tup in tuples(body):
            yield [resolve(v, variables) for v in split_values(tup)]


def strip_comments(text):
    """Remove `-- ...` line comments that are not inside a quoted string."""
    out, quote, esc = [], False, False
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if esc:
            esc = False
        elif ch == '\\' and quote:
            esc = True
        elif ch == "'":
            quote = not quote
        elif not quote and ch == '-' and i + 1 < n and text[i + 1] == '-':
            j = text.find('\n', i)
            if j == -1:
                break
            out.append('\n')
            i = j + 1
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def tuples(body):
    """Yield the inside of each top-level (...) in a VALUES body.

    A regex cannot do this: mob names contain parentheses -- `Goblin_Smithy_(Fire)` --
    and a naive scan ends the tuple there, handing the caller a row with too few fields.
    That silently threw away 1045 of 1763 mob groups on the first run.
    """
    depth, start, quote, esc = 0, None, False, False
    for i, ch in enumerate(body):
        if esc:
            esc = False
        elif ch == '\\':
            esc = True
        elif quote:
            if ch == "'":
                quote = False
        elif ch == "'":
            quote = True
        elif ch == '(':
            depth += 1
            if depth == 1:
                start = i + 1
        elif ch == ')':
            depth -= 1
            if depth == 0 and start is not None:
                yield body[start:i]
                start = None


def resolve(value, variables):
    """Turn a raw SQL field into a plain string.

    Two shapes need it. Drop rates are single variables (`@COMMON`), and item flags are
    OR-expressions of them: `@FLAG_MYSTERY_BOX | @FLAG_CANEQUIP | @FLAG_RARE`. Reading either
    as a number gives 0, which is how the first run of this generator concluded that nothing
    in FINAL FANTASY XI is rare or exclusive.
    """
    if '@' not in value:
        return value
    total, seen = 0, False
    for part in value.split('|'):
        part = part.strip()
        if part.startswith('@'):
            part = variables.get(part[1:])
            if part is None:
                return value
        try:
            total |= int(float(part))
            seen = True
        except (TypeError, ValueError):
            return value
    return str(total) if seen else value


def split_values(s):
    out, cur, quote, esc = [], '', False, False
    for ch in s:
        if esc:
            cur += ch
            esc = False
        elif ch == '\\':
            esc = True
        elif quote:
            if ch == "'":
                quote = False
            else:
                cur += ch
        elif ch == "'":
            quote = True
        elif ch == ',':
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    out.append(cur.strip())
    return out


def num(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def pretty(name):
    return ' '.join(w.capitalize() if w.islower() else w for w in str(name).split('_'))


def slot_name(mask):
    for bit, name in SLOTS:
        if mask & bit:
            return name
    return None


def lua_str(s):
    return "'" + str(s).replace('\\', '\\\\').replace("'", "\\'") + "'"


def parse_item_enum(root):
    """scripts/enum/item.lua -> {NAME: id}. Vendor stock is written as `xi.item.LUGWORM`."""
    out = {}
    path = os.path.join(root, 'scripts/enum/item.lua')
    if not os.path.exists(path):
        return out
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r"\s*([A-Z][A-Z0-9_]*)\s*=\s*(\d+)", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def parse_npcs(sql_dir):
    """npc_list -> {name: (zone, x, y, z)}. The zone is encoded in the npc id."""
    out = {}
    for r in rows(os.path.join(sql_dir, 'npc_list.sql'), 'npc_list'):
        if len(r) < 7:
            continue
        nid = num(r[0])
        name = r[2] or r[1]
        if not name or name in out:
            continue
        out[name] = ((nid - 0x1000000) >> 12, float(r[4] or 0), float(r[5] or 0), float(r[6] or 0))
    return out


def parse_zone_ids(sql_dir):
    """zone_settings -> {directory name: zone id}. The zone script folders are named exactly
    as that table names the zone, which is how a shop script's path gives its zone."""
    out = {}
    for r in rows(os.path.join(sql_dir, 'zone_settings.sql'), 'zone_settings'):
        if len(r) < 4:
            continue
        out[r[3]] = num(r[0])
    return out


def parse_vendors(root, item_ids, npcs, zone_ids):
    """Shops live in zone scripts, not in a table: an NPC builds a `stock` list and hands it
    to `xi.shop.general`. Read those, so a gear guide can say "buy it from X in Y" instead of
    only ever pointing at a monster."""
    vendors = defaultdict(list)
    zone_dir = os.path.join(root, 'scripts/zones')
    for zone_name in sorted(os.listdir(zone_dir)):
        npc_dir = os.path.join(zone_dir, zone_name, 'npcs')
        if not os.path.isdir(npc_dir):
            continue
        for f in sorted(os.listdir(npc_dir)):
            if not f.endswith('.lua'):
                continue
            text = open(os.path.join(npc_dir, f), encoding='utf-8', errors='replace').read()
            if 'xi.shop.' not in text:
                continue
            npc_name = f[:-4].replace('_', ' ')
            # Most shop NPCs are not in npc_list at all -- that table holds only part of the
            # world's entities. The zone is always knowable from the script's own folder, so a
            # vendor without coordinates still gets "buy it in Norg" and a route there.
            placed = npcs.get(npc_name) or npcs.get(f[:-4])
            zone = placed[0] if placed else zone_ids.get(zone_name)
            for m in re.finditer(r"\{\s*xi\.item\.([A-Z0-9_]+)\s*,\s*(\d+)", text):
                iid = item_ids.get(m.group(1))
                if iid is None:
                    continue
                entry = {'npc': npc_name, 'price': int(m.group(2)), 'zone': zone,
                         'x': placed[1] if placed else None,
                         'z': placed[3] if placed else None}
                if entry['zone'] is None:
                    continue
                vendors[iid].append(entry)
    return vendors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--outdir', default='Vanaguide/data')
    ap.add_argument('--quests', default='Vanaguide/data/quests.lua',
                    help='the file tools/gen_quests.py wrote; its reward items count as a '
                         'source, so quest gear appears in the gear finder')
    args = ap.parse_args()
    sql = os.path.join(args.root, 'sql')

    # ---- items -----------------------------------------------------------------
    items = {}
    for r in rows(os.path.join(sql, 'item_basic.sql'), 'item_basic'):
        if len(r) < 8:
            continue
        iid, name, flags = num(r[0]), r[2], num(r[7])
        if iid == 0 or name in ('', '.'):
            continue
        items[iid] = {'name': pretty(name), 'flags': flags}

    equipment = {}
    for r in rows(os.path.join(sql, 'item_equipment.sql'), 'item_equipment'):
        if len(r) < 10:
            continue
        iid = num(r[0])
        equipment[iid] = {'level': num(r[2]), 'jobs': num(r[4]), 'slot': num(r[8])}

    # ---- mobs ------------------------------------------------------------------
    pools = {}
    for r in rows(os.path.join(sql, 'mob_pools.sql'), 'mob_pools'):
        if len(r) < 16:
            continue
                # mobType is the fifteenth column, index 14. Reading r[15] (immunity) instead found
        # 16 notorious monsters in the whole game, which is what caught this.
        pools[num(r[0])] = {'name': pretty(r[1]), 'mobType': num(r[14])}

    # mob_groups' key is (groupid, zoneid), not groupid: the same group number is reused in
    # every zone. Keying on groupid alone collapsed 1757 rows into 718 and joined half the
    # world's drops onto the wrong monsters.
    groups = {}
    for r in rows(os.path.join(sql, 'mob_groups.sql'), 'mob_groups'):
        if len(r) < 7:
            continue
        groups[(num(r[0]), num(r[2]))] = {'pool': num(r[1]), 'zone': num(r[2]),
                                          'name': pretty(r[3]), 'respawn': num(r[4]),
                                          'drop': num(r[6])}

    spawns = {}
    for r in rows(os.path.join(sql, 'mob_spawn_points.sql'), 'mob_spawn_points'):
        if len(r) < 10:
            continue
        # Same ambiguity: the spawn's zone comes out of its mob id, the way npc ids encode it.
        gid = (num(r[4]), (num(r[0]) - 0x1000000) >> 12)
        if gid in spawns:
            continue                      # first spawn point is enough to point an arrow
        spawns[gid] = {
            'name': pretty(r[3] or r[2]),
            'min': num(r[5]), 'max': num(r[6]),
            'x': float(r[7] or 0), 'y': float(r[8] or 0), 'z': float(r[9] or 0),
        }

    droplists = defaultdict(list)
    for r in rows(os.path.join(sql, 'mob_droplist.sql'), 'mob_droplist'):
        if len(r) < 6:
            continue
        droplists[num(r[0])].append({'item': num(r[4]), 'rate': num(r[5]),
                                     'group_rate': num(r[3]), 'type': num(r[1])})

    # ---- join ------------------------------------------------------------------
    nms, drops = [], defaultdict(list)
    for key, g in groups.items():
        pool = pools.get(g['pool'], {})
        spawn = spawns.get(key)
        is_nm = bool(pool.get('mobType', 0) & MOBTYPE_NOTORIOUS)
        name = spawn['name'] if spawn else (g['name'] or pool.get('name', ''))
        if not name:
            continue

        loot = []
        for d in droplists.get(g['drop'], []):
            item = items.get(d['item'])
            if item is None:
                continue
            rate = d['rate'] / 10.0            # the server stores tenths of a percent
            if d['group_rate'] and d['group_rate'] < 1000:
                rate = rate * d['group_rate'] / 1000.0
            loot.append((d['item'], round(rate, 1)))
            # Only record a source for something worth hunting: rare, ex, or equipment.
            f = item['flags']
            if (f & (FLAG_RARE | FLAG_EX)) or d['item'] in equipment:
                drops[d['item']].append({'mob': name, 'zone': g['zone'], 'rate': round(rate, 1),
                                         'nm': is_nm,
                                         'x': spawn['x'] if spawn else None,
                                         'z': spawn['z'] if spawn else None})

        if is_nm and spawn is not None and g['zone'] > 0:
            # (1,1,1) and (0,0,0) are LandSandBoat's placeholders for a mob whose real spawn
            # is decided by a script. Writing them out would point the arrow confidently at
            # the middle of nowhere, so the entry keeps its name and loses its coordinates.
            placeholder = ((abs(spawn['x']) <= 1 and abs(spawn['y']) <= 1 and abs(spawn['z']) <= 1))
            nms.append({
                'name': name, 'zone': g['zone'], 'min': spawn['min'], 'max': spawn['max'],
                'x': None if placeholder else spawn['x'],
                'z': None if placeholder else spawn['z'],
                'y': None if placeholder else spawn['y'],
                'respawn': g['respawn'],
                'loot': sorted(loot, key=lambda t: -t[1])[:8],
            })

    nms.sort(key=lambda n: (n['zone'], n['name']))

    # ---- quest rewards ---------------------------------------------------------
    # Read back what gen_quests.py already worked out rather than parsing the quest scripts a
    # second time: one source of truth, and the two generators stay independent.
    quest_rewards = set()
    if os.path.exists(args.quests):
        text = open(args.quests, encoding='utf-8').read()
        for m in re.finditer(r"rewards\s*=\s*\{([^}]*)\}", text):
            for n in re.finditer(r"\d+", m.group(1)):
                quest_rewards.add(int(n.group(0)))

    # ---- vendors ---------------------------------------------------------------
    vendors = parse_vendors(args.root, parse_item_enum(args.root), parse_npcs(sql),
                            parse_zone_ids(sql))

    header = ("-- Vanaguide :: data/%s\n"
              "-- GENERATED by tools/gen_loot.py from a LandSandBoat checkout.  Do not hand-edit.\n"
              "-- Drop rates are the server's own numbers, in percent.\n"
              "--\n"
              "-- Copyright (c) 2026 Bates LLC.  All rights reserved.\n\n")

    # ---- nm.lua ----------------------------------------------------------------
    with open(os.path.join(args.outdir, 'nm.lua'), 'w', encoding='utf-8') as fh:
        fh.write(header % 'nm.lua')
        fh.write('local N = {}\n\nN.list = {\n')
        placed = 0
        for n in nms:
            loot = ', '.join('{%d,%s}' % (i, ('%.1f' % r)) for i, r in n['loot'])
            where = ''
            if n['x'] is not None:
                placed += 1
                where = ' x = %.1f, z = %.1f, y = %.1f,' % (n['x'], n['z'], n['y'])
            fh.write("    { name = %s, zone = %d, lo = %d, hi = %d,%s respawn = %d, loot = { %s } },\n"
                     % (lua_str(n['name']), n['zone'], n['min'], n['max'], where,
                        n['respawn'], loot))
        fh.write('}\n\n')
        fh.write("""--- Every notorious monster known to spawn in a zone.
function N.in_zone(zone)
    local out = {}
    for _, n in ipairs(N.list) do
        if n.zone == zone then out[#out + 1] = n end
    end
    return out
end

--- Name search, case-insensitive substring.
function N.find(text)
    local needle, out = tostring(text):lower(), {}
    for _, n in ipairs(N.list) do
        if n.name:lower():find(needle, 1, true) then out[#out + 1] = n end
    end
    return out
end

return N
""")

    # ---- drops.lua -------------------------------------------------------------
    kept = 0
    with open(os.path.join(args.outdir, 'drops.lua'), 'w', encoding='utf-8') as fh:
        fh.write(header % 'drops.lua')
        fh.write('local D = {}\n\n-- [item id] = { { mob, zone, rate, nm, x, z }, ... }\nD.sources = {\n')
        for iid in sorted(drops):
            best = sorted(drops[iid], key=lambda s: -s['rate'])[:4]
            parts = []
            for s in best:
                bits = "%s, %d, %s, %s" % (lua_str(s['mob']), s['zone'], ('%.1f' % s['rate']),
                                           'true' if s['nm'] else 'false')
                if s['x'] is not None:
                    bits += ", %.1f, %.1f" % (s['x'], s['z'])
                parts.append('{ %s }' % bits)
            fh.write('    [%d] = { %s },\n' % (iid, ', '.join(parts)))
            kept += 1
        fh.write('}\n\n')
        fh.write("""--- Where does this item come from?  Best drop rate first.
function D.sources_for(item_id)
    local raw = D.sources[item_id]
    if raw == nil then return {} end
    local out = {}
    for _, s in ipairs(raw) do
        out[#out + 1] = { mob = s[1], zone = s[2], rate = s[3], nm = s[4], x = s[5], z = s[6] }
    end
    return out
end

return D
""")

    # ---- vendors.lua -----------------------------------------------------------
    with open(os.path.join(args.outdir, 'vendors.lua'), 'w', encoding='utf-8') as fh:
        fh.write(header % 'vendors.lua')
        fh.write('local V = {}\n\n-- [item id] = { { npc, zone, price, x, z }, ... }\nV.sold_by = {\n')
        for iid in sorted(vendors):
            best = sorted(vendors[iid], key=lambda v: v['price'])[:3]
            parts = ['{ %s, %d, %d, %.1f, %.1f }' % (lua_str(v['npc']), v['zone'], v['price'],
                                                     v['x'] or 0, v['z'] or 0) for v in best]
            fh.write('    [%d] = { %s },\n' % (iid, ', '.join(parts)))
        fh.write('}\n\n')
        fh.write("""--- Who sells this, cheapest first?
function V.sources_for(item_id)
    local raw = V.sold_by[item_id]
    if raw == nil then return {} end
    local out = {}
    for _, v in ipairs(raw) do
        out[#out + 1] = { npc = v[1], zone = v[2], price = v[3], x = v[4], z = v[5] }
    end
    return out
end

return V
""")

    # ---- gear.lua --------------------------------------------------------------
    gear_rows = 0
    with open(os.path.join(args.outdir, 'gear.lua'), 'w', encoding='utf-8') as fh:
        fh.write(header % 'gear.lua')
        fh.write("""local G = {}

-- Equipment with a source this addon can point at -- dropped by something, or sold by
-- somebody standing in a zone.
-- [item id] = { name, level, jobs bitmask, slot name, rare, ex }
G.items = {
""")
        for iid, eq in sorted(equipment.items()):
            if iid not in drops and iid not in vendors and iid not in quest_rewards:
                continue                      # no source we can name: nothing to point at
            item = items.get(iid)
            if item is None:
                continue
            slot = slot_name(eq['slot'])
            if slot is None:
                continue
            f = item['flags']
            fh.write("    [%d] = { %s, %d, %d, %s, %s, %s },\n"
                     % (iid, lua_str(item['name']), eq['level'], eq['jobs'], lua_str(slot),
                        'true' if f & FLAG_RARE else 'false', 'true' if f & FLAG_EX else 'false'))
            gear_rows += 1
        fh.write('}\n\n')
        fh.write("""--- Jobs are a bitmask, bit 1 = WAR .. bit 22 = GEO, matching the client's job ids.
function G.fits_job(entry, job_id)
    if job_id == nil or job_id == 0 then return true end
    local mask = entry[3]
    if mask == 0 then return true end
    return math.floor(mask / 2 ^ job_id) % 2 == 1
end

--- Everything for a slot that this job can wear at this level, closest to the level first.
function G.for_slot(slot, level, job_id)
    local out = {}
    for id, e in pairs(G.items) do
        if e[4] == slot and e[2] <= (level or 99) and G.fits_job(e, job_id) then
            out[#out + 1] = { id = id, name = e[1], level = e[2], slot = e[4],
                              rare = e[5], ex = e[6] }
        end
    end
    table.sort(out, function(a, b)
        if a.level ~= b.level then return a.level > b.level end
        return a.name < b.name
    end)
    return out
end

--- Name search across everything with a source.
function G.find(text)
    local needle, out = tostring(text):lower(), {}
    for id, e in pairs(G.items) do
        if e[1]:lower():find(needle, 1, true) then
            out[#out + 1] = { id = id, name = e[1], level = e[2], slot = e[4],
                              rare = e[5], ex = e[6] }
        end
    end
    table.sort(out, function(a, b) return a.name < b.name end)
    return out
end

return G
""")

    print('%d notorious monsters (%d with real coordinates), %d items dropped by something, %d items sold by somebody, '
          '%d equipment pieces you can be pointed at (%d of them quest rewards)'
          % (len(nms), placed, kept, len(vendors), gear_rows, len(quest_rewards)))


if __name__ == '__main__':
    sys.exit(main())
