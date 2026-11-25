#!/usr/bin/env python3
"""Vanaguide :: tools/servers/scythe.py

Build per-server data for the Scythe private server (folder key: scythe) from its public
site, https://scythe-bbq.pages.dev .

  fetch    robots.txt (the host has none: it answers with the home page), the static JSON the
           site's own database page loads (data/<name>.json, field meanings in js/database.js),
           and the HTML guide pages linked from index.html and guides.html.
           Saved under ~/Downloads/ffxi-server-data/scythe/raw/; nothing is refetched unless
           --refresh.  Honest User-Agent, 1 s between requests, no login.
  convert  raw -> Vanaguide/data/servers/scythe/
             gear_guide.lua     equipment.json + drops.json + recipes.json + shops.json
             skill_guides.lua   crafting bands from recipes.json
             quest_guides.lua   only when guide pages carry ordered step lists
             server_notes.lua   facts from the HTML pages, one guide per topic

Fetched content is untrusted data: it is parsed, never executed.  Run with python3 -I.

    python3 -I tools/servers/scythe.py [--refresh] [--fetch-only | --convert-only]

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import html
import html.parser
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

KEY = 'scythe'
BASE = 'https://scythe-bbq.pages.dev/'
UA = 'VanaGuide-data/1.0 (+https://batesai.org; help@batesai.org)'
FETCHED = '2026-10-28'
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RAW = os.path.expanduser('~/Downloads/ffxi-server-data/%s/raw' % KEY)
OUT = os.path.join(REPO, 'Vanaguide', 'data', 'servers', KEY)
ZONE_NAMES = os.path.join(REPO, 'Vanaguide', 'data', 'zone_names.lua')

DATA_FILES = ['items', 'equipment', 'mobs', 'spells', 'weaponskills', 'mobskills', 'nm_hunts',
              'shops', 'drops', 'recipes', 'zones', 'item_mods', 'item_drops',
              'regional_bosses', 'lumina_augments']
SEED_PAGES = ['index.html', 'guides.html', 'server-info.html', 'other-features.html',
              'missions.html', 'relic-weapons.html', 'nm-hunt.html']
SKIP_PAGES = {'login.html', 'database.html', 'community.html'}
MAX_PAGES = 400
ROBOT_AGENTS = ('claudebot', 'anthropic-ai', 'claude-web', '*')

_last = [0.0]


def get(path):
    """GET BASE+path politely; returns (status, bytes) or (status, None)."""
    wait = 1.0 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(urllib.parse.urljoin(BASE, path), headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        body, status = None, e.code
    finally:
        _last[0] = time.time()
    return status, body


def raw_path(path):
    return os.path.join(RAW, path.replace('/', '_'))


def fetch_one(path, refresh):
    dest = raw_path(path)
    if os.path.exists(dest) and not refresh:
        return True
    status, body = get(path)
    print('  GET %s -> %s %s' % (path, status, len(body) if body else 0))
    if status != 200 or body is None:
        return False
    with open(dest, 'wb') as f:
        f.write(body)
    return True


def robots_disallows(text, paths):
    """Return the paths a robots.txt disallows for any of our agents (empty if not robots)."""
    if '<html' in text[:500].lower():
        return []
    groups, agents, rules = [], [], []
    for line in text.splitlines():
        line = line.split('#', 1)[0].strip()
        if ':' not in line:
            continue
        k, v = [s.strip() for s in line.split(':', 1)]
        k = k.lower()
        if k == 'user-agent':
            if rules:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(v.lower())
        elif k == 'disallow' and v:
            rules.append(v)
    if agents:
        groups.append((agents, rules))
    bad = []
    for agents, rules in groups:
        if any(a in ROBOT_AGENTS for a in agents):
            for p in paths:
                if any(('/' + p).startswith(r) for r in rules):
                    bad.append(p)
    return sorted(set(bad))


def page_links(path):
    with open(raw_path(path), encoding='utf-8', errors='replace') as f:
        text = f.read()
    out = []
    base = os.path.dirname(path)
    for h in re.findall(r'href="([^"#?]+\.html)"', text):
        if '://' in h or h.startswith('/') or '..' in h and not base:
            continue
        h = os.path.normpath(os.path.join(base, h))
        if h.startswith('..') or h in SKIP_PAGES:
            continue
        out.append(h)
    return out


def fetch(refresh):
    os.makedirs(RAW, exist_ok=True)
    fetch_one('robots.txt', refresh)
    with open(raw_path('robots.txt'), encoding='utf-8', errors='replace') as f:
        robots = f.read()
    wanted = ['data/%s.json' % n for n in DATA_FILES] + ['js/database.js'] + SEED_PAGES
    blocked = robots_disallows(robots, wanted)
    if blocked:
        print('robots.txt disallows: %s' % ', '.join(blocked))
    missing = []
    for p in ['js/database.js'] + ['data/%s.json' % n for n in DATA_FILES]:
        if p not in blocked and not fetch_one(p, refresh):
            missing.append(p)
    # Breadth-first over every same-site .html page the guide pages link to.
    seen, queue = set(), list(SEED_PAGES)
    while queue:
        p = queue.pop(0)
        if p in seen or p in blocked or len(seen) >= MAX_PAGES:
            continue
        seen.add(p)
        if fetch_one(p, refresh):
            queue += [q for q in page_links(p) if q not in seen]
        else:
            missing.append(p)
    with open(os.path.join(RAW, 'pages.json'), 'w') as f:
        json.dump({'pages': sorted(seen), 'missing': missing, 'blocked': blocked}, f, indent=1)
    print('pages: %d, missing: %s, blocked: %s' % (len(seen), missing or 'none', blocked or 'none'))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[2])
    ap.add_argument('--refresh', action='store_true')
    ap.add_argument('--fetch-only', action='store_true')
    ap.add_argument('--convert-only', action='store_true')
    a = ap.parse_args()
    if not a.convert_only:
        fetch(a.refresh)
    if not a.fetch_only:
        convert()


#  ---------------------------------------------------------------- HTML -> blocks

class Blocks(html.parser.HTMLParser):
    """Flatten a page's body to ('h', level, text) / ('tr', [cells]) / ('li', text, ordered)
    / ('p', text) blocks, skipping nav, footer, script, style and forms."""
    SKIP = {'nav', 'footer', 'script', 'style', 'form', 'button', 'select', 'noscript', 'svg'}
    TEXT = {'h1', 'h2', 'h3', 'h4', 'li', 'p', 'td', 'th', 'dt', 'dd', 'figcaption'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip, self.stack, self.lists, self.cells = [], 0, [], [], None
        self.buf = None

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in ('ul', 'ol'):
            self.flush()
            self.lists.append(tag)
        elif tag == 'table':
            self.flush()
            self.out.append(('table',))
        elif tag == 'tr':
            self.flush()
            self.cells = []
        elif tag == 'br' and self.buf is not None:
            self.buf.append(' ')
        elif tag in self.TEXT:
            self.flush()
            self.stack.append(tag)
            self.buf = []

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in ('ul', 'ol'):
            self.flush()
            if self.lists:
                self.lists.pop()
        elif tag == 'tr':
            self.flush()
            if self.cells:
                self.out.append(('tr', [c[0] for c in self.cells], all(c[1] for c in self.cells)))
            self.cells = None
        elif tag in self.TEXT:
            self.flush()

    def flush(self):
        if self.buf is None:
            return
        tag = self.stack.pop() if self.stack else 'p'
        text = clean(''.join(self.buf))
        self.buf = None
        if not text:
            return
        if tag in ('td', 'th'):
            if self.cells is not None:
                self.cells.append((text, tag == 'th'))
        elif tag in ('h1', 'h2', 'h3', 'h4'):
            self.out.append(('h', int(tag[1]), text))
        elif tag == 'li':
            self.out.append(('li', text, bool(self.lists) and self.lists[-1] == 'ol'))
        else:
            self.out.append(('p', text))

    def handle_data(self, data):
        if not self.skip and self.buf is not None:
            self.buf.append(data)


def clean(s):
    s = re.sub(r'\s+', ' ', s).strip()
    return s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')


def page_blocks(name):
    with open(raw_path(name), encoding='utf-8', errors='replace') as f:
        p = Blocks()
        p.feed(f.read())
        p.flush()
    return p.out


def page_title(name):
    for b in page_blocks(name):
        if b[0] == 'h' and b[1] == 1:
            return b[2]
    return name


def sections(name):
    """[(heading, [bullet text], [ordered step text])] split at every h2/h3.  Table rows become
    'first cell — Header: cell; ...' using the table's own header row."""
    out, head = [], None
    bullets, ordered, header = [], [], None
    for b in page_blocks(name):
        if b[0] == 'h':
            if b[1] == 1:
                continue
            if bullets or ordered:
                out.append((head, bullets, ordered))
            head, bullets, ordered = b[2], [], []
        elif b[0] == 'table':
            header = None
        elif b[0] == 'tr':
            cells, is_header = b[1], b[2]
            if is_header:
                header = cells
                continue
            if len(cells) == 1:
                bullets.append(cells[0])
            elif len(cells) == 2:
                bullets.append('%s: %s' % (cells[0], cells[1]))
            elif header and len(header) == len(cells):
                bullets.append('%s — %s' % (cells[0], '; '.join(
                    '%s: %s' % (h, c) for h, c in zip(header[1:], cells[1:]) if c not in ('', '—'))))
            else:
                bullets.append(' | '.join(cells))
        elif b[0] == 'li':
            (ordered if b[2] else bullets).append(b[1])
        else:
            bullets.append(b[1])
    if bullets or ordered:
        out.append((head, bullets, ordered))
    junk = re.compile(r'^(←|Loading|Download |No regional bosses match|Persisted game events$)|^.{0,60}→$')
    return [(h, [x for x in b if not junk.match(x)], o) for h, b, o in out]


#  ---------------------------------------------------------------- helpers

LSB_SQL = '/Volumes/Games/FFXI/lsb/server/sql'
CRAFTS = ['Woodworking', 'Smithing', 'Goldsmithing', 'Clothcraft', 'Leathercraft', 'Bonecraft',
          'Alchemy', 'Cooking']
JOBS = ['WAR', 'MNK', 'WHM', 'BLM', 'RDM', 'THF', 'PLD', 'DRK', 'BST', 'BRD', 'RNG', 'SAM',
        'NIN', 'DRG', 'SMN', 'BLU', 'COR', 'PUP', 'DNC', 'SCH', 'GEO', 'RUN']
SLOTS = [(0x0001, 'main'), (0x0002, 'sub'), (0x0004, 'ranged'), (0x0008, 'ammo'),
         (0x0010, 'head'), (0x0020, 'body'), (0x0040, 'hands'), (0x0080, 'legs'),
         (0x0100, 'feet'), (0x0200, 'neck'), (0x0400, 'waist'), (0x0800, 'ear'),
         (0x1000, 'ear'), (0x2000, 'ring'), (0x4000, 'ring'), (0x8000, 'back')]
FLAG_EX, FLAG_RARE = 0x4000, 0x8000
MOBTYPE_NOTORIOUS = 0x02
CELENNIA = 284          # Celennia Memorial Library: the NM Hunt shop NPC (nm-hunt.html)


def url(page):
    return BASE + page


def load(name):
    with open(raw_path('data/%s.json' % name), encoding='utf-8') as f:
        return json.load(f)


def title(name):
    """'piece of ash lumber' -> 'Piece Of Ash Lumber' (the stock files' style)."""
    return ' '.join(w[:1].upper() + w[1:] if w.islower() else w
                    for w in str(name).replace('_', ' ').split())


def key(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower())


def jobs_text(mask):
    if mask == 0:
        return 'No jobs'
    if mask & ((1 << 22) - 1) == (1 << 22) - 1:
        return 'All jobs'
    return ' '.join(j for i, j in enumerate(JOBS) if mask & (1 << i))


def slot_name(mask):
    for bit, name in SLOTS:
        if mask & bit:
            return name
    return None


def lstr(s):
    s = str(s).replace('\\', '\\\\').replace("'", "\\'").replace('\r', '').replace('\n', '\\n')
    return "'" + s + "'"


def lval(v):
    if v is None:
        return 'nil'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return str(v)
    return lstr(v)


def header(fname, source, what):
    return ('-- Vanaguide :: data/servers/%s/%s\n'
            '-- GENERATED by tools/servers/%s.py from %s, fetched %s.  Do not hand-edit.\n'
            '-- %s\n'
            '-- The source site states no licence; facts are reproduced with attribution to it.\n'
            '--\n'
            '-- Copyright (c) 2026 Bates LLC.  All rights reserved.\n\n') % (KEY, fname, KEY, source, FETCHED, what)


def lsb_rows(table):
    """LandSandBoat rows via the stock tool's SQL reader (only used for item flags and the
    notorious-monster flag, which the Scythe JSON does not carry)."""
    path = os.path.join(LSB_SQL, table + '.sql')
    if not os.path.exists(path):
        return []
    sys.dont_write_bytecode = True
    sys.path.insert(0, os.path.dirname(HERE))
    import gen_loot  # noqa: E402  (our own tool, not fetched content)
    return list(gen_loot.rows(path, table)), gen_loot


def lsb_item_flags():
    got = lsb_rows('item_basic')
    if not got:
        return {}
    rows, L = got
    head = open(os.path.join(LSB_SQL, 'item_basic.sql'), encoding='utf-8', errors='replace').read(4000)
    fcol = 7 if '`name_jp`' in head else 6
    return {L.num(r[0]): (key(r[2]), L.num(r[fcol])) for r in rows if len(r) > fcol}


def lsb_nm_names():
    got = lsb_rows('mob_pools')
    if not got:
        return set()
    rows, L = got
    return {key(r[1]) for r in rows if len(r) > 15 and L.num(r[14]) & MOBTYPE_NOTORIOUS}


_RECIPES = []


def synth_recipes():
    """recipes.json without desynthesis rows.  Scythe's JSON carries no desynth flag, so a row
    is dropped when LandSandBoat's synth_recipes.sql has the same ID and result marked Desynth,
    or (for Scythe-only IDs) when it turns one piece of equipment into a non-equipment item with
    a Lightning Crystal, the desynthesis signature."""
    if _RECIPES:
        return _RECIPES
    rec = load('recipes')
    eq_names = {key(e['name']) for e in load('equipment')}
    eq_ids = {e['id'] for e in load('equipment')}
    lsb = {}
    got = lsb_rows('synth_recipes')
    if got:
        rows, L = got
        lsb = {L.num(r[0]): (L.num(r[1]), L.num(r[21])) for r in rows if len(r) > 21}
    for r in rec:
        flag = lsb.get(r['id'])
        if flag and flag[1] == r['resultId']:
            if flag[0]:
                continue
        elif (key(r['crystalName']) == 'lightningcrystal' and len(set(r['ingredients'])) == 1
              and key(r['ingredients'][0]) in eq_names and r['resultId'] not in eq_ids):
            continue
        _RECIPES.append(r)
    return _RECIPES


#  ---------------------------------------------------------------- gear_guide.lua

CATEGORIES = [
    ('craft', 'Craftable', 'Made by synthesis. Shows the craft, its level and the ingredients (Scythe recipes.json).'),
    ('dynamis', 'Relic Armor (Dynamis)', 'Armor that drops from monsters in Dynamis zones, including Dynamis Divergence [D].'),
    ('hunt', 'Hunt NM Drops', 'Dropped by one of Scythe\'s custom NM Hunt monsters (the nm_hunts list, matched by name and zone).'),
    ('nm', 'Notorious Monster Drops', 'Dropped by named, rarer monsters.'),
    ('drop', 'Monster Drops', None),  # desc set in gear() from the drop types actually present
    ('shop', 'Scythe Shops', 'Sold by Scythe\'s own shops: the !shop command pages and the NM Hunt (Scyld) shop.'),
]


def gear(out_dir):
    equip = load('equipment')
    drops = load('drops')
    recipes = synth_recipes()
    shops = load('shops')
    zones = {key(title(z['name'])): z['id'] for z in load('zones')}
    # A hunt NM is a (name, zone) pair: many hunt names reuse retail/Abyssea mob names that
    # drop gear elsewhere, so a name-only match mislabels those drops.
    hunts = {(key(h['name']), h['zone']) for h in load('nm_hunts')}
    nms = lsb_nm_names()
    flags = lsb_item_flags()
    eq = {e['id']: e for e in equip}

    how = defaultdict(list)
    cats = defaultdict(set)
    drop_types = set()
    for r in recipes:
        if r['resultId'] not in eq:
            continue
        counts = {}
        for ing in r['ingredients']:
            counts[ing] = counts.get(ing, 0) + 1
        parts = ', '.join(('%d × %s' % (n, title(i))) if n > 1 else title(i) for i, n in counts.items())
        text = '%s: %s + %s' % (r['skills'], title(r['crystalName']), parts)
        if r.get('qty', 1) > 1:
            text += ' (makes %d)' % r['qty']
        how[r['resultId']].append(('craft', text, None, None, 0))
        cats[r['resultId']].add('craft')
    for d in drops:
        iid = d['itemId']
        if iid not in eq:
            continue
        zid = zones.get(key(d['zone']))
        mob = title(d['mob']) if d['mob'].islower() else d['mob']
        pct = d['gRate'] * d['iRate'] / 10000.0 if d['type'] == 1 else d['iRate'] / 10.0
        if d['type'] == 2:
            text, rate = 'Stolen from %s' % mob, 0
        elif d['type'] == 4:
            text, rate = 'Despoiled from %s' % mob, 0
        else:
            text, rate = 'Dropped by %s (%s%%)' % (mob, ('%.1f' % pct).rstrip('0').rstrip('.') if pct else '?'), pct
        if (key(d['mob']), zid) in hunts:
            kind, cat = 'nm', 'hunt'
        elif key(d['mob']) in nms:
            kind, cat = 'nm', 'nm'
        else:
            kind, cat = 'drop', 'drop'
        how[iid].append((kind, text, zid, None, rate))
        cats[iid].add(cat)
        if cat == 'drop':
            drop_types.add(d['type'])
        if d['zone'].lower().startswith('dynamis') and slot_name(eq[iid]['slot']) not in ('main', 'sub', 'ranged', 'ammo'):
            cats[iid].add('dynamis')
    for sh in shops:
        iid = sh['id']
        if iid not in eq:
            continue
        if sh['command'] == 'NM Hunt NPC':
            text = 'Sold at the NM Hunt shop (%s) for %s Scyld' % (sh['shop'], sh['price'])
            if sh.get('note'):
                text += ' — ' + sh['note']
            how[iid].append(('vendor', text, CELENNIA, 'NM Hunt', 0))
        else:
            text = 'Sold in %s (%s), price %s' % (sh['shop'], sh['command'], sh['price'])
            if sh.get('note'):
                text += ' — ' + sh['note']
            how[iid].append(('vendor', text, None, None, 0))
        cats[iid].add('shop')

    order = {'craft': 0, 'nm': 1, 'drop': 2, 'vendor': 3}
    items = []
    for iid, hs in how.items():
        e = eq[iid]
        seen, uniq = set(), []
        for h in sorted(hs, key=lambda h: (order[h[0]], -h[4], h[1])):
            k = (h[0], h[1], h[2])
            if k not in seen:
                seen.add(k)
                uniq.append(h)
        name = title(e['name'])
        f = flags.get(iid)
        rare = ex = None
        if f and f[0] == key(e['name']):
            rare, ex = bool(f[1] & FLAG_RARE), bool(f[1] & FLAG_EX)
        items.append((e.get('lvl') or 0, name, iid, e, rare, ex, uniq))
    items.sort(key=lambda t: (t[0], t[1].lower()))

    counts = defaultdict(int)
    for it in items:
        for c in cats[it[2]]:
            counts[c] += 1
    lines = [header('gear_guide.lua', BASE + 'data/{equipment,drops,recipes,shops,zones,nm_hunts}.json',
                    'Every Scythe equipment piece the site\'s data says how to get.  Read by VanaGuide\n'
                    '-- Server-Safe\'s Gear tab.  how = { kind, text, zone id or nil, npc or nil }.\n'
                    '-- rare/ex come from LandSandBoat item_basic.sql where the item id and name match;\n'
                    '-- the NM flag from LandSandBoat mob_pools.sql; hunt NMs from Scythe nm_hunts.json.'),
             'local G = {}', '', 'G.categories = {']
    verbs = ['Dropped by'] + [v for t, v in ((2, 'stolen from'), (4, 'despoiled from')) if t in drop_types]
    for cid, cname, cdesc in CATEGORIES:
        if cdesc is None:
            cdesc = (', '.join(verbs[:-1]) + ' or ' + verbs[-1] if len(verbs) > 1 else verbs[0]) + ' ordinary monsters.'
        lines.append('    { id = %s, name = %s, desc = %s, count = %d },' % (lstr(cid), lstr(cname), lstr(cdesc), counts[cid]))
    lines += ['}', '', 'G.items = {']
    for lvl, name, iid, e, rare, ex, hs in items:
        hw = ', '.join('{ %s, %s, %s, %s }' % (lstr(h[0]), lstr(h[1]), lval(h[2]), lval(h[3])) for h in hs)
        cat = ' '.join(c for c, _, _ in CATEGORIES if c in cats[iid])
        flagtxt = ''
        if rare is not None:
            flagtxt = 'rare = %s, ex = %s, ' % (lval(rare), lval(ex))
        lines.append('    { id = %d, name = %s, level = %d, slot = %s, jobs = %s, %scats = %s, how = { %s } },'
                     % (iid, lstr(name), lvl, lval(slot_name(e['slot'])), lstr(jobs_text(e['jobs'])),
                        flagtxt, lstr(cat), hw))
    lines += ['}', '', 'return G', '']
    write(out_dir, 'gear_guide.lua', lines)
    return len(items), dict(counts)


#  ---------------------------------------------------------------- skill_guides.lua

def skills(out_dir):
    recipes = synth_recipes()
    by_craft = defaultdict(list)
    for r in recipes:
        # Repairs (Broken X -> X) need a broken item you only get when that rod breaks, so they
        # are not practical skill-up recipes.
        if any(i.startswith('broken ') for i in r['ingredients']):
            continue
        levels = []
        for part in r['skills'].split(','):
            m = re.match(r'\s*([A-Za-z]+)\s+(\d+)', part)
            if m:
                levels.append((m.group(1), int(m.group(2))))
        if not levels:
            continue
        main = max(levels, key=lambda t: t[1])
        others = [t for t in levels if t is not main]
        by_craft[main[0]].append((main[1], others, r))
    src = url('server-info.html')
    desc_tail = ('Scythe: craft skill-ups are "effectively guaranteed" up to the recipe level, the common cap is '
                 '3200 so all 8 crafts can reach 110 with no specialization restriction, and the Advanced Support '
                 'NPC in Chocobo Circuit gives a 15-minute Imagery buff. Source: %s and %srecipes.json' % (src, BASE + 'data/'))
    guides = []
    for craft in CRAFTS + sorted(set(by_craft) - set(CRAFTS)):
        rs = by_craft.get(craft)
        if not rs:
            continue
        steps = []
        top = max(t[0] for t in rs)
        for lo in range(0, top, 10):
            band = [t for t in rs if lo < t[0] <= lo + 10]
            if not band:
                continue
            # Skill-ups are guaranteed up to a recipe's level, so the recipes nearest the top of
            # the band carry you furthest; prefer single-craft recipes with few ingredients.
            band.sort(key=lambda t: (any(' kit ' in ' %s ' % i for i in t[2]['ingredients']),
                                     -t[0], len(t[1]), len(t[2]['ingredients']), t[2]['result']))
            picks, names = [], set()
            for lv, others, r in band:
                if r['result'] in names:
                    continue
                names.add(r['result'])
                picks.append((lv, others, r))
                if len(picks) == 6:
                    break
            bl = []
            for lv, others, r in picks:
                counts = {}
                for ing in r['ingredients']:
                    counts[ing] = counts.get(ing, 0) + 1
                parts = ', '.join(('%d × %s' % (n, title(i))) if n > 1 else title(i) for i, n in counts.items())
                need = ''
                if others:
                    need = ', also needs %s' % ', '.join('%s %d' % o for o in others)
                bl.append('• %s (level %d)%s: %s + %s' % (title(r['result']), lv, need, title(r['crystalName']), parts))
            steps.append(('%s %d–%d' % (craft, lo, lo + 10), '\n'.join(bl)))
        guides.append((craft, 'Crafting',
                       'Recipes from Scythe\'s database, highest level first in each band: synthesize one until it '
                       'stops giving skill, then move on. ' + desc_tail, steps))
    write_guides(out_dir, 'skill_guides.lua', BASE + 'data/recipes.json and server-info.html',
                 'A crafting guide per craft, from Scythe\'s recipe list.  Read by VanaGuide Server-Safe\'s\n'
                 '-- Skills tab.  Scythe publishes no combat/magic skill-cap tables, so only crafts are here.', guides)
    return guides


#  ---------------------------------------------------------------- quest_guides.lua

QUESTS = [
    # (page, section heading or None for the intro, name, desc)
    ('fay-weapons.html', None, 'Succor to the Sidhe',
     'Repeatable quest that augments one of 20 Fay-line weapons; given by Callisto in Grauberg [S].'),
    ('dynamis-divergence.html', None, 'Dynamis Divergence entry',
     'How to enter the instanced Dynamis Divergence zones; Aurix in Ru\'Lude Gardens and the Enigmatic Footprints NPCs.'),
    ('sortie.html', 'Overview', 'Sortie entry',
     'How to start a Sortie run in Outer Ra\'Kaznar [U1]; Ruspix in Leafallia and the Diaphanous Transposer in Kamihr Drifts.'),
    ('weapon-progression.html', 'Step 0 — The !rema Shop', 'Base REMA weapon (!rema shop)',
     'The gate for buying a base Relic, Mythic, Empyrean or Ergon weapon with the !rema command.'),
    ('nm-hunt.html', None, 'Starting the NM Hunt',
     'How to begin Scythe\'s 475-NM hunt; the NM Hunts Master in Celennia Memorial Library.'),
    ('elite-hunts.html', 'Overview', 'Starting the Elite Hunts',
     'How to begin the Elite Hunts after all 475 regular hunt NMs; the NM Hunts Master in Celennia Memorial Library.'),
    ('scyld-shop.html', None, 'Spending Scyld',
     'How to spend the hunt currency at the NM Hunt shop NPC in Celennia Memorial Library.'),
    ('fate.html', 'Overview', 'Joining a FATE',
     'How to take part in one of Scythe\'s 88 open-world FATE events.'),
    ('siege.html', None, 'Joining a Siege raid',
     'How to take part in a server-wide 5-wave Siege raid.'),
    ('synergy.html', 'Overview', 'Synergy crafting',
     'How to use a Synergy Engineer and Synergy Furnace in any of 17 zones.'),
    ('trusts.html', 'How to upgrade a trust', 'Upgrading a Trust',
     'How to raise a Trust through its upgrade tiers.'),
    ('blue-magic.html', None, 'Learning Blue Magic',
     'How a Blue Mage learns spells from monsters on Scythe.'),
    ('guides.html', 'Your First Hour', 'Your First Hour',
     'The site\'s step-by-step first hour after logging in.'),
    ('guides.html', 'Path A — Never Played FFXI', 'Path A — Never Played FFXI',
     'The site\'s recommended path for new players.'),
    ('guides.html', 'Path B — Returning Retail Player', 'Path B — Returning Retail Player',
     'The site\'s recommended path for returning retail players.'),
    ('guides.html', 'Path C — Solo Player', 'Path C — Solo Player',
     'The site\'s recommended path for solo players.'),
    ('guides.html', 'Path D — Endgame Hunter', 'Path D — Endgame Hunter',
     'The site\'s recommended path for endgame hunters.'),
]


def find_section(page, heading):
    for h, b, o in sections(page):
        if h == heading:
            return b, o
    return [], []


def quests(out_dir):
    guides = []
    for page, heading, name, desc in QUESTS:
        b, o = find_section(page, heading)
        if not o:
            print('  quest skipped (no step list): %s %s' % (page, heading))
            continue
        steps = [('Step %d' % (i + 1), '• ' + t) for i, t in enumerate(o)]
        if b:
            steps.append(('Notes', bullets(b)))
        guides.append((name, 'Custom', '%s Source: %s' % (desc, url(page)), steps))
    write_guides(out_dir, 'quest_guides.lua', BASE + ' guide pages',
                 'Step-by-step walkthroughs from the Scythe site\'s guide pages (ordered lists only).\n'
                 '-- Read by VanaGuide Server-Safe\'s Quests tab.', guides)
    return guides


#  ---------------------------------------------------------------- server_notes.lua

def bullets(lines):
    return '\n'.join('• ' + x for x in lines)


def chunk(title_, lines, size=30):
    if len(lines) <= size:
        return [(title_, bullets(lines))]
    n = (len(lines) + size - 1) // size
    return [('%s (%d of %d)' % (title_, i + 1, n), bullets(lines[i * size:(i + 1) * size])) for i in range(n)]


def page_steps(page, only=None, skip=(), prefix=''):
    """Steps for a page: one per section (intro titled by the page's h1)."""
    out = []
    for h, b, o in sections(page):
        if only is not None and h not in only:
            continue
        if h in skip:
            continue
        lines = list(b) + ['%d. %s' % (i + 1, t) for i, t in enumerate(o)]
        if lines:
            out += chunk(prefix + (h or page_title(page)), lines)
    return out


def trust_steps():
    pages = sorted(p for p in json.load(open(raw_path('pages.json')))['pages'] if p.startswith('trusts/'))
    out = []
    for p in pages:
        lines = []
        for h, b, o in sections(p):
            if h in ('What They Do', 'Upgrade Requirements'):
                lines += [x for x in b if not x.startswith('These are the exact items')]
            elif h == 'Tier Upgrades':
                lines += [x for x in b if re.match(r'^(Base|Tier)', x)]
        if lines:
            out.append((page_title(p), bullets(lines)))
    return out, pages


def regional_steps():
    d = load('regional_bosses')
    out = []
    for b in d.get('bosses', []):
        out.append(('%s — %s' % (b.get('region'), b.get('boss')),
                    bullets(['Ritual zone: %s' % b.get('ritualZone'),
                             'Rite: %s — %s' % (b.get('rite'), b.get('description'))])))
    return out


def notes(out_dir, fetched_pages, gear_n, skill_n, quest_n):
    G = []
    U = url

    def add(name, desc, pages, steps):
        steps = [s for s in steps if s[1]]
        if steps:
            G.append((name, 'Server', '%s Source: %s' % (desc, ', '.join(U(p) for p in pages)), steps))

    add('Rates and progression', 'Experience, drop, skill-up and death-penalty settings as the site lists them.',
        ['server-info.html', 'index.html'],
        page_steps('server-info.html', only={'Rates', 'Death & Progression', 'Combat Settings'})
        + page_steps('index.html', only={'The server, by the numbers.'}))
    add('Master Levels and Exemplar Points', 'Post-99 Master Levels, EP costs and where EP comes from.',
        ['master-levels.html', 'colosseum.html'],
        page_steps('master-levels.html') + page_steps('colosseum.html', prefix='Colosseum (not yet playable): '))
    add('Travel and quality of life', 'Quality-of-life changes from retail.',
        ['server-info.html', 'other-features.html'],
        page_steps('server-info.html', only={'Quality of Life'})
        + page_steps('other-features.html', only={'Quality of Life', 'Progression & Systems'}))
    add('Commands', 'Scythe\'s custom chat commands.', ['other-features.html', 'nm-hunt.html', 'lumina-augments.html', 'guides.html'],
        page_steps('other-features.html', only={'Custom Commands'})
        + page_steps('nm-hunt.html', only={'Tracking Your Progress — !huntstatus'})
        + page_steps('guides.html', only={'ScytheSkills 1.1.0'}, prefix='Add-on: '))
    add('Crafting and gathering', 'Crafting rates, the hub crafting area, Synergy and the Empress\'s Repair Decree event.',
        ['server-info.html', 'other-features.html', 'synergy.html', 'crafting-event.html'],
        page_steps('server-info.html', only={'Crafting'})
        + page_steps('other-features.html', only={'Custom Content'})
        + page_steps('synergy.html', only={'Available Locations'}, prefix='Synergy: ')
        + page_steps('crafting-event.html', prefix='Repair Decree: '))
    add('Content and missions', 'Which expansions and systems are released, Dynamis settings and mission support.',
        ['server-info.html', 'missions.html', 'other-features.html'],
        page_steps('server-info.html', only={'Released & Verified Content', 'Dynamis Settings', 'Custom Systems Summary'})
        + page_steps('missions.html') + page_steps('other-features.html', only={'Server Events'}))
    add('NM Hunt', 'Scythe\'s 475 custom hunt NMs, Scyld, bounties and milestone rewards.',
        ['nm-hunt.html', 'scyld-shop.html'],
        page_steps('nm-hunt.html', skip={'NM Locations by Zone', 'Tracking Your Progress — !huntstatus'})
        + page_steps('scyld-shop.html', prefix='Scyld shop: '))
    add('NM Hunt locations', 'Every hunt NM by zone with grid squares where the site has them.', ['nm-hunt.html'],
        page_steps('nm-hunt.html', only={'NM Locations by Zone'}))
    add('Elite Hunts', 'The 25 gated elite encounters and their spawn conditions.', ['elite-hunts.html'],
        page_steps('elite-hunts.html'))
    add('Gear and weapons', 'Relic rebalance, REMA weapon paths and Fay weapon augments.',
        ['relic-weapons.html', 'weapon-progression.html', 'fay-weapons.html'],
        page_steps('relic-weapons.html') + page_steps('weapon-progression.html', skip={'Step 0 — The !rema Shop'})
        + page_steps('fay-weapons.html', only={'The Details'}, prefix='Fay weapons: '))
    add('Lumina gear augments', 'Exact-value augments applied by Angel in Chocobo Circuit.', ['lumina-augments.html'],
        page_steps('lumina-augments.html', skip={'Full Augment Catalog'}))
    add('Endgame activities', 'Siege raids, Sortie and Dynamis Divergence.',
        ['siege.html', 'sortie.html', 'dynamis-divergence.html'],
        page_steps('siege.html', prefix='Siege: ') + page_steps('sortie.html', prefix='Sortie: ')
        + page_steps('dynamis-divergence.html', skip={None}, prefix='Divergence: '))
    add('FATE', 'Open-world FATE events: rules, rewards and every zone\'s FATEs.', ['fate.html'],
        page_steps('fate.html'))
    add('Abyssea custom pops', 'Scythe\'s item-trade ??? pops for Abyssea NMs and the Boosted 125 drops.', ['abyssea.html'],
        page_steps('abyssea.html'))
    add('Regional bosses', 'The 40 open-world regional bosses and the rite that pulls each one forward. Live timers are not included.',
        ['regional-bosses.html', 'data/regional_bosses.json'],
        page_steps('regional-bosses.html', only={'Timer fallback plus a player-driven pop'}) + regional_steps())
    tsteps, tpages = trust_steps()
    add('Trusts and Login Points', 'How Trusts work on Scythe and what Login Points buy.',
        ['trusts.html', 'login-points.html'],
        page_steps('trusts.html', only={'What Are Trusts?', 'Quick Team-Building Tips', 'How to upgrade a trust'})
        + page_steps('login-points.html'))
    add('Trust roster', 'Each Trust\'s role, job, Login Points cost, tier upgrades and upgrade items, from its own page.',
        ['trusts.html', 'trusts/<name>.html (one page per Trust)'], tsteps)
    add('Blue Magic teachers', 'Which monster family or NM teaches each Blue Magic spell.', ['blue-magic.html'],
        page_steps('blue-magic.html'))
    add('Getting started', 'Connecting to Scythe and the first things to do.', ['getting-started.html', 'server-info.html'],
        page_steps('server-info.html', only={'Connection'}) + page_steps('getting-started.html'))
    add('Rules and FAQ', 'Server rules and the site\'s FAQ.', ['rules.html', 'faq.html'],
        page_steps('rules.html') + page_steps('faq.html'))
    add('Work in progress', 'Systems the site lists as unreleased. Not live on the server as of the fetch.',
        ['coming-soon.html', 'server-info.html', 'features.html'],
        page_steps('server-info.html', only={'Work in Progress'}, prefix='Server Info: ')
        + page_steps('features.html', only={'Work in Progress'}, prefix='Features: ')
        + [('Coming soon: ' + (h or 'Overview'), bullets(b[:1])) for h, b, o in sections('coming-soon.html') if b][:8])

    about = [
        ('What was fetched', bullets([
            'Site: %s (Scythe\'s own public site; it has no separate wiki).' % BASE,
            'Fetched on %s with an honest User-Agent, 1 second between requests, no login.' % FETCHED,
            'robots.txt: the host has none (the path returns the home page), so nothing was disallowed.',
            '%d HTML pages, crawled from the home page and the guides page through every same-site link (including %d Trust pages).' % (len(fetched_pages), len([p for p in fetched_pages if p.startswith('trusts/')])),
            'Static JSON the site\'s own Database page loads: ' + ', '.join('data/%s.json' % n for n in DATA_FILES) + ', and js/database.js for field meanings.'])),
        ('What each file holds', bullets([
            'gear_guide.lua: %d equipment pieces with a known source (recipes, monster drops, Scythe shops).' % gear_n,
            'skill_guides.lua: %d crafting guides from the %d synthesis recipes in recipes.json (%d desynthesis rows left out: LandSandBoat Desynth flag by recipe ID, or one equipment piece + Lightning Crystal for Scythe-only IDs; repair recipes using a Broken item are not suggested as skill-ups).' % (skill_n, len(synth_recipes()), len(load('recipes')) - len(synth_recipes())),
            'quest_guides.lua: %d step-by-step walkthroughs taken from the ordered lists on guide pages.' % quest_n,
            'server_notes.lua: the guides that follow, each bullet copied from the page named in its Source.'])),
        ('How fields were derived', bullets([
            'Drop rates: grouped drops (type 1) are group rate × item rate; other drops use the item rate. js/database.js labels type 1 as Steal, but the rows match LandSandBoat\'s grouped-drop layout, so type 2 is shown as Steal and type 4 as Despoil.',
            'Notorious-monster drops use LandSandBoat\'s mob_pools NM flag by monster name; custom hunt NMs come from nm_hunts.json.',
            'Rare/Ex flags come from LandSandBoat item_basic.sql only where the item id and name match Scythe\'s; otherwise they are left out.',
            '!shop prices are shown without a currency because the site does not name one; NM Hunt shop prices are Scyld.'])),
        ('Not covered', bullets([
            'Live data: regional boss timers, siege announcements, player counts.',
            'Item stats (item_mods.json) and the full Lumina augment catalog (lumina_augments.json) were fetched but are not converted.',
            'Artifact, relic, empyrean and quest rewards: the site\'s data has no per-item quest or upgrade sources beyond what the guide pages say.',
            'Combat and magic skill caps: the site publishes none.',
            'Pages not fetched: login.html, database.html (the data it loads was fetched), community.html, and off-site links (Discord, launcher download).',
            'Licence: the site states none. Content belongs to the Scythe team; reproduced here as facts with attribution.'])),
    ]
    G.insert(0, ('About this data', 'Server', 'What was fetched from the Scythe site on %s, how it was converted, and what is missing. Source: %s' % (FETCHED, BASE), about))
    write_guides(out_dir, 'server_notes.lua', BASE + ' (HTML pages and data/*.json)',
                 'Server notes for Scythe, one guide per topic.  Every bullet is text from the page named\n'
                 '-- in that guide\'s Source.  Read by VanaGuide Server-Safe.', G)
    return G


#  ---------------------------------------------------------------- writers

def write(out_dir, fname, lines):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, fname), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def write_guides(out_dir, fname, source, what, guides):
    lines = [header(fname, source, what), 'local S = {}', '', 'S.guides = {']
    for name, group, desc, steps in guides:
        lines.append('    { name = %s, group = %s, desc = %s, steps = {' % (lstr(name), lstr(group), lstr(desc)))
        lines.append(',\n'.join('            { title = %s, note = %s }' % (lstr(t), lstr(n)) for t, n in steps))
        lines.append('    } },')
    lines += ['}', '', 'return S', '']
    write(out_dir, fname, lines)


def convert():
    pages = json.load(open(raw_path('pages.json')))['pages']
    n_gear, counts = gear(OUT)
    sk = skills(OUT)
    qs = quests(OUT)
    ns = notes(OUT, pages, n_gear, len(sk), len(qs))
    print('gear items: %d  %s' % (n_gear, counts))
    print('skill guides: %d   quest guides: %d   server notes: %d' % (len(sk), len(qs), len(ns)))


if __name__ == '__main__':
    main()
