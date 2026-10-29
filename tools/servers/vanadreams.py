#!/usr/bin/env python3
"""Vanaguide :: tools/servers/vanadreams.py

Build Vanaguide/data/servers/vanadreams/*.lua from the Vanadreams wiki (https://vanadreams.org/wiki/).

The wiki is a static reader (app.js) over data/<name>.json "generated from the server repo".
This script
  fetch    downloads robots.txt, the wiki's app.js and its JSON files into
           ~/Downloads/ffxi-server-data/vanadreams/raw/ (skipped when present unless --refresh),
           one request per second, honest User-Agent, no login
  convert  turns that raw data into
             gear_guide.lua     equipment with how to get it: drops (with rates), shops, recipes,
                                quest rewards, battlefields
             skill_guides.lua   craft levelling bands from the server's recipes, with shop prices
             quest_guides.lua   quest and mission walkthroughs (walk-quests / walk-missions)
             server_notes.lua   the wiki's server guide: modes, rates, changes, commands

Fetched content is untrusted data: it is only parsed as JSON / text, never executed.
Run with python3 -I.

    python3 -I tools/servers/vanadreams.py [--refresh] [--fetch-only] [--raw DIR] [--out DIR]

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.request
import urllib.robotparser
from collections import defaultdict

KEY = 'vanadreams'
HOST = 'https://vanadreams.org'
WIKI = HOST + '/wiki/'
UA = 'VanaGuide-data/1.0 (+https://batesai.org; help@batesai.org)'
FETCHED = '2026-10-28'
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEF_RAW = os.path.expanduser('~/Downloads/ffxi-server-data/%s/raw' % KEY)
DEF_OUT = os.path.join(REPO, 'Vanaguide', 'data', 'servers', KEY)

NAMED = ['meta', 'index', 'zonelist', 'contrib', 'quests', 'walk-quests', 'missions', 'walk-missions',
         'recipes', 'synergy', 'jobs', 'keyitems', 'battlefields', 'itemguides', 'jobguides', 'itemkeys']

_last = [0.0]


def get(url, dest, refresh, delay):
    if os.path.exists(dest) and os.path.getsize(dest) > 0 and not refresh:
        return True
    wait = delay - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
    except Exception as e:  # noqa: BLE001
        _last[0] = time.time()
        print('  FAILED %s: %s' % (url, e), file=sys.stderr)
        return False
    _last[0] = time.time()
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest + '.part', 'wb') as fh:
        fh.write(body)
    os.replace(dest + '.part', dest)
    print('  %s (%d bytes)' % (url, len(body)))
    return True


def fetch(raw, refresh):
    os.makedirs(os.path.join(raw, 'data'), exist_ok=True)
    rob = os.path.join(raw, 'robots.txt')
    get(HOST + '/robots.txt', rob, refresh, 1.0)
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(open(rob, encoding='utf-8', errors='replace').read().splitlines())
    delay = 1.0
    for agent in ('ClaudeBot', 'anthropic-ai', 'Claude-Web', '*'):
        if not rp.can_fetch(agent, WIKI + 'data/meta.json'):
            sys.exit('robots.txt disallows %s for /wiki/: not fetching' % agent)
        cd = rp.crawl_delay(agent)
        if cd:
            delay = max(delay, float(cd))
    get(WIKI + 'app.js', os.path.join(raw, 'app.js'), refresh, delay)
    for n in NAMED:
        get(WIKI + 'data/%s.json' % n, os.path.join(raw, 'data', n + '.json'), refresh, delay)
    meta = json.load(open(os.path.join(raw, 'data', 'meta.json')))
    for s in meta.get('shards', []):
        get(WIKI + 'data/items-%d.json' % s, os.path.join(raw, 'data', 'items-%d.json' % s), refresh, delay)
    for s in meta.get('zshards', []):
        get(WIKI + 'data/zones-%d.json' % s, os.path.join(raw, 'data', 'zones-%d.json' % s), refresh, delay)
    get(WIKI, os.path.join(raw, 'wiki_index.html'), refresh, delay)
    # the list of player-written guides (public, read-only); recorded, not converted (see About this data)
    get(HOST + '/api/public/wiki/guides', os.path.join(raw, 'player_guides.json'), refresh, delay)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', default=DEF_RAW)
    ap.add_argument('--out', default=DEF_OUT)
    ap.add_argument('--refresh', action='store_true')
    ap.add_argument('--fetch-only', action='store_true')
    a = ap.parse_args()
    fetch(a.raw, a.refresh)
    if a.fetch_only:
        return
    convert(a.raw, a.out)


# ---------------------------------------------------------------- convert

JOBS = ['WAR', 'MNK', 'WHM', 'BLM', 'RDM', 'THF', 'PLD', 'DRK', 'BST', 'BRD', 'RNG', 'SAM', 'NIN', 'DRG', 'SMN',
        'BLU', 'COR', 'PUP', 'DNC', 'SCH', 'GEO', 'RUN']
CRAFTS = ['Woodworking', 'Smithing', 'Goldsmithing', 'Clothcraft', 'Leathercraft', 'Bonecraft', 'Alchemy', 'Cooking']
CRYSTAL = {4096: 'Fire', 4097: 'Ice', 4098: 'Wind', 4099: 'Earth', 4100: 'Lightning', 4101: 'Water', 4102: 'Light',
           4103: 'Dark'}
SLOT = {'main': 'main', 'sub': 'sub', 'range': 'ranged', 'ammo': 'ammo', 'head': 'head', 'body': 'body',
        'hands': 'hands', 'legs': 'legs', 'feet': 'feet', 'neck': 'neck', 'waist': 'waist', 'ear': 'ear',
        'ring': 'ring', 'back': 'back'}
MAX_CRAFT_LEVEL = 200
DYNAMIS_ZONES = {39, 40, 41, 42, 134, 135, 185, 186, 187, 188, 294, 295, 296, 297}
SYN_RANKS = ['Amateur', 'Recruit', 'Initiate', 'Novice', 'Apprentice', 'Journeyman', 'Craftsman', 'Artisan', 'Adept',
             'Veteran', 'Expert', 'Authority', 'Luminary', 'Master', 'Grandmaster', 'Legend']
AS_OF_RE = re.compile(r'Data reflects the Vanadreams server as of\s*(?:<[^>]+>\s*)*([0-9]{1,2} [A-Z][a-z]{2} [0-9]{4})')


def q(s):
    s = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', str(s)).replace('\r', '')
    return "'" + s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n') + "'"


def lnum(v):
    return 'nil' if v is None else str(int(v))


def header(fh, fname, what):
    fh.write('-- Vanaguide :: data/servers/%s/%s\n' % (KEY, fname))
    fh.write('-- GENERATED by tools/servers/%s.py from %s (the Vanadreams wiki, data/*.json), fetched %s.  Do not hand-edit.\n'
             % (KEY, WIKI, FETCHED))
    fh.write('-- %s\n' % what)
    fh.write('-- Source data: Vanadreams wiki ("a static reader over data/*.json generated from the server repo").\n')
    fh.write('-- No licence is stated on the source; facts only, attributed to vanadreams.org.\n')
    fh.write('--\n-- Copyright (c) 2026 Bates LLC.  All rights reserved.\n\n')


def load(raw, name):
    with open(os.path.join(raw, 'data', name + '.json'), encoding='utf-8') as fh:
        return json.load(fh)


# ---- a small, data-only reader for JavaScript array literals (strings, numbers, nested arrays)

def js_array(src, i):
    """Parse the array literal that starts at src[i] == '['. Returns (value, end index)."""
    def ws(j):
        while j < len(src) and src[j] in ' \t\r\n':
            j += 1
        return j

    def val(j):
        j = ws(j)
        c = src[j]
        if c == '[':
            out, j = [], ws(j + 1)
            if src[j] == ']':
                return out, j + 1
            while True:
                v, j = val(j)
                out.append(v)
                j = ws(j)
                if src[j] == ',':
                    j = ws(j + 1)
                    if src[j] == ']':
                        return out, j + 1
                    continue
                if src[j] == ']':
                    return out, j + 1
                raise ValueError('bad array at %d: %r' % (j, src[j:j + 40]))
        if c in '\'"':
            buf, j = [], j + 1
            while src[j] != c:
                if src[j] == '\\':
                    n = src[j + 1]
                    buf.append({'n': '\n', 't': '\t'}.get(n, n))
                    j += 2
                else:
                    buf.append(src[j])
                    j += 1
            return ''.join(buf), j + 1
        m = re.match(r'-?[0-9.]+', src[j:])
        if m:
            return float(m.group(0)), j + len(m.group(0))
        if src.startswith('null', j):
            return None, j + 4
        raise ValueError('unexpected %r at %d' % (src[j:j + 40], j))
    return val(i)


# ---- HTML -> plain text lines

def text(h):
    h = re.sub(r'<[^>]+>', '', h)
    return re.sub(r'\s+', ' ', html.unescape(h)).strip()


def html_lines(h):
    """Block-level HTML -> list of plain text lines (paragraphs, list items, table rows, definitions)."""
    h = re.sub(r'(?is)<(script|style|figure|img)[^>]*>.*?</\1>', ' ', h)
    h = re.sub(r'(?is)<img[^>]*>', ' ', h)
    h = re.sub(r'(?is)<summary>.*?</summary>', ' ', h)
    h = re.sub(r'(?is)<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>', lambda m: '\n' + m.group(1) + ': ', h)
    h = re.sub(r'(?is)</t[dh]>\s*<t[dh][^>]*>', ' | ', h)
    h = re.sub(r'(?is)<(br|/?p|/?li|/?ul|/?ol|/?tr|/?div|/?dd|/?dt|/?dl|/?table|/?thead|/?tbody|/?details|/?blockquote|/?h[1-6])\b[^>]*>', '\n', h)
    out = []
    for ln in h.split('\n'):
        t = text(ln)
        if t and t not in ('▲ Menu',):
            out.append(t)
    return out


def html_sections(h, first_title):
    """Split HTML at <h2>/<h3> into [(title, [lines])]."""
    parts = re.split(r'(?is)<h[23][^>]*>(.*?)</h[23]>', h)
    secs = []
    if html_lines(parts[0]):
        secs.append((first_title, html_lines(parts[0])))
    for k in range(1, len(parts), 2):
        t = text(parts[k]) or first_title
        ls = html_lines(parts[k + 1]) if k + 1 < len(parts) else []
        if ls:
            secs.append((t, ls))
    return secs


def bullets(lines, cap=3000):
    out, n = [], 0
    for ln in lines:
        b = '• ' + ln
        if n + len(b) > cap:
            out.append('• …')
            break
        out.append(b)
        n += len(b) + 1
    return '\n'.join(out)


def guide_line(fh, name, group, desc, steps):
    fh.write('    { name = %s, group = %s, desc = %s, steps = {\n' % (q(name), q(group), q(desc)))
    fh.write(',\n'.join('            { title = %s, note = %s }' % (q(t), q(n)) for t, n in steps))
    fh.write('\n    } },\n')


# ---- shared lookups

class Data:
    def __init__(self, raw):
        self.raw = raw
        self.items = {}
        for f in sorted(os.listdir(os.path.join(raw, 'data'))):
            if re.fullmatch(r'items-\d+\.json', f):
                self.items.update({int(k): v for k, v in load(raw, f[:-5]).items()})
        self.zname = {int(z[0]): z[1] for z in load(raw, 'zonelist')}
        self.nm = set()   # (zone id, monster name) of notorious monsters, from the zone shards
        for f in sorted(os.listdir(os.path.join(raw, 'data'))):
            if re.fullmatch(r'zones-\d+\.json', f):
                for zid, z in load(raw, f[:-5]).items():
                    for m in z.get('mobs', []):
                        if m.get('nm'):
                            self.nm.add((int(zid), m['n']))
        # level 255 in a recipe's skill list marks a recipe the server does not let anyone make; leave those out
        self.recipes = [r for r in load(raw, 'recipes') if isinstance(r.get('id'), int)
                        and max(r['sk'].values()) < MAX_CRAFT_LEVEL]
        self.dropped_recipes = sum(1 for r in load(raw, 'recipes') if isinstance(r.get('id'), int)) - len(self.recipes)
        self.synergy = [r for r in load(raw, 'synergy') if isinstance(r.get('id'), int)]
        self.quests = load(raw, 'quests')
        self.missions = load(raw, 'missions')
        self.bfs = load(raw, 'battlefields')
        self.contrib = load(raw, 'contrib')
        with open(os.path.join(raw, 'app.js'), encoding='utf-8') as fh:
            self.app = fh.read()
        idx = os.path.join(raw, 'wiki_index.html')
        m = AS_OF_RE.search(open(idx, encoding='utf-8').read()) if os.path.exists(idx) else None
        self.as_of = m.group(1) if m else None

    def iname(self, i):
        if i == 65535:
            return 'Gil'
        it = self.items.get(i)
        return it['n'] if it else 'Item %d' % i

    def zn(self, z):
        return self.zname.get(z, 'zone %s' % z) if z is not None else ''


def pct(r):
    return '100%' if r >= 1000 else ('%.1f%%' % (r / 10.0))


def ingredients(d, ins):
    seen = {}
    for x in ins:
        seen[x] = seen.get(x, 0) + 1
    return ', '.join(('%d × %s' % (c, d.iname(x))) if c > 1 else d.iname(x) for x, c in seen.items())


def recipe_text(d, r, main=None):
    sk = sorted(r['sk'].items(), key=lambda kv: (kv[0] != main, -kv[1]) if main else (-kv[1], kv[0]))
    crystal = CRYSTAL.get(r['cr'], d.iname(r['cr'])) + ' Crystal' if r['cr'] in CRYSTAL else d.iname(r['cr'])
    return '%s: %s + %s' % (', '.join('%s %d' % kv for kv in sk), crystal, ingredients(d, r['in']))


def jobs_text(js):
    if set(js) >= set(JOBS):
        return 'All jobs'
    return ' '.join(j for j in JOBS if j in js)


# ---- gear_guide.lua

def gear(d, out):
    qi = {i: x for i, x in enumerate(d.quests)}
    mk = defaultdict(list)
    hq = defaultdict(list)
    for r in d.recipes:
        if r.get('ds'):
            continue
        mk[r['out'][0]].append(r)
        for x in set(r['out'][1:]):
            if x != r['out'][0]:
                hq[x].append(r)
    smk = defaultdict(list)
    for r in d.synergy:
        smk[r['out'][0]].append(r)
    cats_used = defaultdict(int)
    rows = []
    for iid, it in d.items.items():
        eq = it.get('eq')
        if not eq:
            continue
        how, cats = [], []

        def add(kind, cat, t, z=None, npc=None):
            how.append((kind, t, z, npc))
            if cat not in cats:
                cats.append(cat)
        for r in sorted(mk.get(iid, []), key=lambda r: (max(r['sk'].values()), r['id'])):
            add('craft', 'craft', recipe_text(d, r))
        for r in sorted(hq.get(iid, []), key=lambda r: (max(r['sk'].values()), r['id'])):
            add('craft', 'craft', 'High-quality result of ' + recipe_text(d, r))
        for r in smk.get(iid, []):
            rk = ', '.join('%s %s' % (s if s != 'Synergy' else 'rank', SYN_RANKS[k] if 0 <= k < len(SYN_RANKS) else k)
                           for s, k in r['rk'])
            fw = ', '.join('%s %d' % kv for kv in r['fw'].items())
            add('craft', 'craft', 'Synergy (%s; fewell %s): %s' % (rk, fw, ingredients(d, r['in'])))
        for qid in it.get('qr', []):
            qq = qi.get(qid)
            if qq:
                add('quest', 'quest', 'Quest: %s (%s)' % (qq['n'], qq['a']), qq.get('z'), qq.get('g') or None)
        for b in it.get('bf', []):
            if 0 <= b < len(d.bfs):
                bf = d.bfs[b]
                add('battlefield', 'battlefield', 'Battlefield reward: %s (%s)' % (bf['n'], d.zn(bf.get('z'))), bf.get('z'))
        drops = sorted(it.get('mob', []), key=lambda m: (m[3] != 'd', -m[2]))
        for z, mob, rate, kind in drops:
            if kind == 's':
                add('drop', 'drop', 'Stolen from %s' % mob, z)
            elif (z, mob) in d.nm:
                add('nm', 'nm', 'Notorious monster %s (%s)' % (mob, pct(rate)), z)
                if z in DYNAMIS_ZONES and 'dynamis' not in cats:
                    cats.append('dynamis')
            else:
                add('drop', 'drop', 'Dropped by %s (%s)' % (mob, pct(rate)), z)
                if z in DYNAMIS_ZONES and 'dynamis' not in cats:
                    cats.append('dynamis')
        shop_npcs = set()
        for z, npc, price in sorted(it.get('shop', []), key=lambda s: s[2]):
            add('vendor', 'vendor', 'Sold by %s for %d gil' % (npc, price), z, npc)
            shop_npcs.add(npc)
        for npc, z, cost in it.get('sold', []):
            if npc in shop_npcs and not cost:
                continue
            if cost and not cost.endswith(' gil'):
                add('exchange', 'exchange', 'From %s for %s' % (npc, cost), z, npc if z is not None else None)
            else:
                add('vendor', 'vendor', ('Sold by %s for %s' % (npc, cost)) if cost else 'Sold by %s' % npc,
                    z, npc if z is not None else None)
        if not how:
            continue
        for c in cats:
            cats_used[c] += 1
        slot = SLOT.get((eq.get('slot') or ['other'])[0].lower(), 'other')
        rows.append((it['n'], iid, eq.get('lv') or 0, slot, jobs_text(eq.get('jobs', [])), bool(it.get('rare')),
                     bool(it.get('ex')), ' '.join(cats), how))
    rows.sort(key=lambda r: (r[2], r[0].lower(), r[1]))
    cat_defs = [
        ('craft', 'Craftable', 'Made by synthesis or at a synergy furnace. Shows the craft, its level and the ingredients.'),
        ('quest', 'Quest Rewards', 'Given for finishing a quest.'),
        ('battlefield', 'Battlefield Rewards', 'Won from a battlefield (BCNM, KSNM, ENM and other fights).'),
        ('dynamis', 'Dynamis Drops', 'Drops from monsters in a Dynamis zone.'),
        ('nm', 'Notorious Monster Drops', 'Dropped by named, rarer monsters.'),
        ('drop', 'Monster Drops', 'Dropped by (or stolen from) ordinary monsters.'),
        ('vendor', 'Merchants', 'Sold by an NPC for gil.'),
        ('exchange', 'Exchanges', 'Bought with sparks, points or another currency instead of gil.'),
    ]
    path = os.path.join(out, 'gear_guide.lua')
    with open(path, 'w', encoding='utf-8') as fh:
        header(fh, 'gear_guide.lua', 'Every piece of Vanadreams equipment the wiki gives a source for. how = { kind, text, zone id or nil, npc or nil }')
        fh.write('local G = {}\n\nG.categories = {\n')
        for cid, name, desc in cat_defs:
            if cats_used.get(cid):
                fh.write('    { id = %s, name = %s, desc = %s, count = %d },\n' % (q(cid), q(name), q(desc), cats_used[cid]))
        fh.write('}\n\nG.items = {\n')
        for name, iid, lv, slot, jobs, rare, ex, cats, how in rows:
            hs = ', '.join('{ %s, %s, %s, %s }' % (q(k), q(t), lnum(z), q(n) if n else 'nil') for k, t, z, n in how)
            fh.write('    { id = %d, name = %s, level = %d, slot = %s, jobs = %s, rare = %s, ex = %s, cats = %s, how = { %s } },\n'
                     % (iid, q(name), lv, q(slot), q(jobs), str(rare).lower(), str(ex).lower(), q(cats), hs))
        fh.write('}\n\nreturn G\n')
    return path, len(rows)


# ---- skill_guides.lua (crafting bands from the server's recipes, priced from the server's shops)

def skills(d, out):
    def cheapest(i):
        best = None
        for z, npc, price in d.items.get(i, {}).get('shop', []):
            if best is None or price < best[2]:
                best = (z, npc, price)
        return best

    guides = []
    for craft in CRAFTS:
        recs = [r for r in d.recipes if not r.get('ds') and r['sk'].get(craft)
                and r['sk'][craft] == max(r['sk'].values()) and r['out'][0] < 65535]
        if not recs:
            continue
        top = max(r['sk'][craft] for r in recs)
        steps = []
        for lo in range(0, top, 10):
            band = [r for r in recs if lo < r['sk'][craft] <= lo + 10]
            if not band:
                continue

            def cost(r):
                unknown, total = 0, 0
                for x in set(r['in']):
                    c = cheapest(x)
                    if c is None:
                        unknown += 1
                    else:
                        total += c[2] * r['in'].count(x)
                return (unknown, total, r['sk'][craft], r['id'])
            seen, pick = set(), []
            for r in sorted(band, key=cost):
                if r['out'][0] in seen:
                    continue
                seen.add(r['out'][0])
                pick.append(r)
                if len(pick) == 4:
                    break
            lines = []
            for r in pick:
                parts = []
                counts = {}
                for x in r['in']:
                    counts[x] = counts.get(x, 0) + 1
                for x, c in counts.items():
                    s = ('%d × %s' % (c, d.iname(x))) if c > 1 else d.iname(x)
                    ch = cheapest(x)
                    if ch:
                        s += ' (%s, %s, %d gil)' % (ch[1], d.zn(ch[0]), ch[2])
                    parts.append(s)
                other = ', '.join('%s %d' % kv for kv in r['sk'].items() if kv[0] != craft)
                crystal = (CRYSTAL[r['cr']] + ' Crystal') if r['cr'] in CRYSTAL else d.iname(r['cr'])
                qn = r['q'][0] if r.get('q') else 1
                outn = d.iname(r['out'][0]) + (' x%d' % qn if qn and qn > 1 else '')
                lines.append('%s (cap %d)%s: %s + %s' % (outn, r['sk'][craft], (', also needs ' + other) if other else '',
                                                         crystal, ', '.join(parts)))
            steps.append(('%s %d–%d' % (craft, lo, lo + 10), '\n'.join('• ' + x for x in lines)))
        guides.append((craft, 'Crafting',
                       'In each band, synthesize one of these until it stops giving skill, then move on. Cheapest first, '
                       'from the Vanadreams recipe list; prices are the cheapest NPC shop price the wiki lists (the wiki gives no guild shop prices, so guild-only materials show no price). '
                       'Vanadreams: crafting skill-ups twice as likely, crafting HQ chance 5×. Source: %s#craft-%d'
                       % (WIKI, CRAFTS.index(craft)), steps))
    path = os.path.join(out, 'skill_guides.lua')
    with open(path, 'w', encoding='utf-8') as fh:
        header(fh, 'skill_guides.lua', 'Crafting levelling guides built from the Vanadreams recipe list. Read by the Skills tab.')
        fh.write('local S = {}\n\nS.guides = {\n')
        for g in guides:
            guide_line(fh, *g)
        fh.write('}\n\nreturn S\n')
    return path, len(guides)


# ---- quest_guides.lua

def reward_lines(d, r):
    if not r:
        return []
    out = []
    if r.get('gil'):
        out.append('%s gil' % format(r['gil'], ','))
    if r.get('exp'):
        out.append('%s experience points' % format(r['exp'], ','))
    if r.get('items'):
        names = [d.iname(i) for i in r['items']]
        if len(names) > 12:
            out.append('One of %d items, including %s' % (len(names), ', '.join(names[:12])))
        else:
            out.append('Items: ' + ', '.join(names))
    if r.get('ki'):
        out.append('Key items: ' + ', '.join(r['ki']))
    if r.get('title'):
        out.append('Title: ' + r['title'])
    if r.get('fame'):
        out.append('Fame: %s (%s)' % (r['fame'][1], r['fame'][0]) if isinstance(r['fame'], list) else 'Fame')
    return out


def walk_steps(d, w, r):
    steps = []
    if w.get('req'):
        steps.append(('Before you start', '\n'.join('• ' + x for x in w['req'])))
    for n, x in enumerate(w.get('st', []), 1):
        steps.append(('Step %d' % n, x))
    if w.get('nt'):
        steps.append(('Good to know', '\n'.join('• ' + x for x in w['nt'])))
    rl = reward_lines(d, r)
    if rl:
        steps.append(('Reward', '\n'.join('• ' + x for x in rl)))
    return steps


def quest_guides(d, out):
    wq = load(d.raw, 'walk-quests')
    wm = load(d.raw, 'walk-missions')
    guides = []
    for i, qq in enumerate(d.quests):
        w = wq.get(str(i))
        if not w:
            continue
        desc = w.get('s', '')
        if qq.get('g') or qq.get('z') is not None:
            desc += ' Starts with %s%s.' % (qq.get('g') or 'an unknown NPC',
                                            (' in ' + d.zn(qq['z'])) if qq.get('z') is not None else '')
        desc += ' Source: %s#quest-%d' % (WIKI, i)
        guides.append((qq['n'], qq['a'], desc.strip(), walk_steps(d, w, qq.get('r'))))
    nq = len(guides)
    for i, m in enumerate(d.missions):
        w = wm.get(str(i))
        if not w:
            continue
        desc = w.get('s', '')
        if m.get('no'):
            desc += ' Mission %s.' % m['no']
        desc += ' Source: %s#mission-%d' % (WIKI, i)
        guides.append((m['n'], 'Mission: ' + m['x'], desc.strip(), walk_steps(d, w, m.get('r'))))
    path = os.path.join(out, 'quest_guides.lua')
    with open(path, 'w', encoding='utf-8') as fh:
        header(fh, 'quest_guides.lua', 'Quest and mission walkthroughs from the Vanadreams wiki (walk-quests.json, walk-missions.json).')
        fh.write('local S = {}\n\nS.guides = {\n')
        for g in guides:
            guide_line(fh, *g)
        fh.write('}\n\nreturn S\n')
    return path, nq, len(guides) - nq


# ---- server_notes.lua

def app_block(app, key, nxt):
    a = app.index("\n  %s: ['" % key)
    b = app.index("\n  %s: ['" % nxt, a) if nxt else len(app)
    return app[a:b]


def changed_rows(app):
    sec = app_block(app, 'server', 'systems')
    i = sec.index('})([[') + 3
    rows, _ = js_array(sec, i)
    doors = [(text(t), text(s)) for t, s in re.findall(r'(?s)<a class="door"[^>]*><b>(.*?)</b><span>(.*?)</span></a>', sec)]
    groups = []
    gi = sec.find('const GROUPS = ')
    if gi >= 0:
        groups, _ = js_array(sec, sec.index('[', gi))
    return {r[0]: r[1] for r in rows}, [r[0] for r in rows], doors, groups


def systems(app):
    sec = app_block(app, 'systems', 'patches')
    i = sec.index("[['")
    table, j = js_array(sec, i)
    head = re.search(r'<thead><tr>(.*?)</tr></thead>', sec)
    cols = [text(c) for c in re.findall(r'<th>(.*?)</th>', head.group(1))] if head else []
    intro = text(re.search(r'(?s)<p>(.*?)</p>', sec).group(1))
    rest = sec[sec.index("</tbody></table></div>'}", j) + len("</tbody></table></div>'}"):]
    rest = rest[:rest.rfind('`')]
    return intro, cols, table, html_sections(rest, 'Overview')


def patches(app):
    sec = app_block(app, 'patches', None)
    i = sec.index("[['")
    rows, _ = js_array(sec, i)
    return rows


def commands(d):
    found = {}
    srcs = [('app', d.app)] + [(k, v[1]) for k, v in d.contrib.items()]
    for key, h in srcs:
        for block in re.findall(r'(?is)<(?:p|li|dd|td)[^>]*>(.*?)</(?:p|li|dd|td)>', h):
            for c in re.findall(r'<code>(![a-zA-Z][^<]*)</code>', block):
                c = html.unescape(c).strip()
                if c.startswith('!pos'):
                    continue
                base = c.split()[0]
                found.setdefault(base, [])
                t = text(block)
                if t not in [x[0] for x in found[base]] and len(found[base]) < 3:
                    found[base].append((t, key))
    return found


def server_notes(d, out):
    rows, order, doors, groups = changed_rows(d.app)
    intro, cols, table, sys_secs = systems(d.app)
    pat = patches(d.app)
    cmds = commands(d)
    src_guide = WIKI + '#guide'
    src_server = WIKI + '#guide-server'
    src_sys = WIKI + '#guide-systems'
    guides = []
    used_rows = set()

    def row_steps(keys):
        st = []
        for k in keys:
            if k in rows:
                used_rows.add(k)
                st.append((k, '• ' + rows[k]))
        return st

    def contrib_steps(key, cap=2500):
        if key not in d.contrib:
            return []
        title, h = d.contrib[key][0], d.contrib[key][1]
        return [('%s: %s' % (title, t) if t != title else title, bullets(ls, cap)) for t, ls in html_sections(h, title)]

    # About this data
    n_contrib = len(d.contrib)
    pg = os.path.join(d.raw, 'player_guides.json')
    n_player = len(json.load(open(pg)).get('guides', [])) if os.path.exists(pg) else 0
    about = [
        ('What was fetched', '\n'.join([
            '• Fetched %s from %s with the User-Agent "%s". robots.txt (https://vanadreams.org/robots.txt) says "User-agent: *  Allow: /" and welcomes agents and crawlers.' % (FETCHED, WIKI, UA),
            '• The wiki is a static reader (app.js) over data/*.json files that the wiki says are "generated from the server repo". Fetched: meta, index, zonelist, contrib (%d server guide pages), quests, walk-quests, missions, walk-missions, recipes, synergy, jobs, keyitems, battlefields, itemguides, jobguides, itemkeys, the item shards and the zone shards, plus app.js (the Server guide, Rates and modes, and Patch history pages).' % n_contrib,
            '• The wiki footer says: "Data reflects the Vanadreams server as of %s." The Patch history page lists changes up to %s.' % (d.as_of or 'an unstated date', pat[0][0] if pat else 'an unstated date'),
            '• No login, no account, no posting. %d item records, %d recipes, %d quests, %d missions.' % (len(d.items), len(d.recipes), len(d.quests), len(d.missions)),
        ])),
        ('What these files hold', '\n'.join([
            '• gear_guide.lua: every equipment item the wiki gives at least one source for: crafting and synergy recipes, quest rewards, battlefield rewards, monster drops with the wiki\'s rates (notorious monsters marked from the zone data), steals, NPC shops and spark/point exchanges.',
            '• skill_guides.lua: crafting levelling bands from the server\'s own recipe list, priced from the cheapest NPC shop the wiki lists.',
            '• quest_guides.lua: every quest and mission the wiki has a walkthrough for.',
            '• server_notes.lua: the wiki\'s Server guide (what is different from the original game), Rates and modes, Patch history, the in-game commands it mentions, and each of its %d guide pages.' % n_contrib,
        ])),
        ('What is NOT covered', '\n'.join([
            '• Fishing: the wiki publishes no fish/bait/skill data, so there is no fishing levelling guide here (see the Vanafish and Fishing Records guides below for what the wiki does say).',
            '• Combat and magic skill caps: not published separately by the wiki; the stock VanaGuide skill guides apply, with the server\'s 2× skill-up rate.',
            '• Recipes whose skill list includes level 255 (%d of them; the server data\'s way of marking a recipe nobody can make) are left out.' % d.dropped_recipes,
            '• Guild shop prices: the wiki lists guild shops but not their prices, so the crafting guides only price items sold by ordinary NPC shops.',
            '• Artifact and relic categories: the wiki does not mark items that way, so those items appear under how they are actually obtained.',
            '• Player-written guides (%d listed at /api/public/wiki/guides on %s): written by individual players, not the server, and not copied.' % (n_player, FETCHED),
            '• Monster pages, zone maps, NPC lists, key items, job abilities and spells: on the wiki, not converted.',
            '• The wiki states no licence. Final Fantasy is a registered trademark of Square Enix; Vanadreams says it is a free, non-profit, fan-run server with no affiliation to Square Enix.',
        ])),
    ]
    guides.append(('About this data', 'Server', 'What was fetched from the Vanadreams wiki on %s, and what is not covered. Source: %s' % (FETCHED, WIKI), about))

    # Only on Vanadreams
    if doors:
        guides.append(('Only on Vanadreams', 'Server', 'Features the wiki lists as only on Vanadreams. Source: ' + src_server,
                       [(t, '• ' + s) for t, s in doors]))

    # Character modes + rates table
    mode_steps = [('Three modes', '• ' + intro)]
    if cols and len(cols) >= 5:
        for r in table:
            mode_steps.append((r[0], '\n'.join('• %s: %s' % (cols[c], r[c] or '(none)') for c in range(1, len(cols)))))
    guides.append(('Character modes and rates', 'Server', 'Default, Classic and Moogle Mode compared with the standard game, setting by setting. Source: ' + src_sys, mode_steps))
    guides.append(('Rates and progression', 'Server', 'Experience, capacity points, level caps and new characters on Vanadreams. Source: %s; %s#guide-c_server_rates' % (src_server, WIKI),
                   row_steps(['New characters', 'Level caps', 'Experience', 'Capacity points', 'Merits and rings']) + contrib_steps('server_rates')))
    guides.append(('Systems', 'Server', 'Classic, Moogle Mode, Records of Eminence, Unity, capacity and job points, Master Levels, synergy and magic bursts. Source: ' + src_sys,
                   [(t, bullets(ls)) for t, ls in sys_secs]))
    guides.append(('Crafting and gathering', 'Server', 'Skill-up and HQ rates, synergy and crafting help. Source: %s; %s' % (src_server, src_sys),
                   row_steps(['Skills and crafting']) + [(t, bullets(ls)) for t, ls in sys_secs if t == 'Synergy'] + row_steps(['Adoulin'])))
    guides.append(('Gear and drops', 'Server', 'Drops, gil, upgrades, augments and gear sources. Source: ' + src_server,
                   row_steps(['Drops and gil', 'Upgrades', 'Augments', 'Endgame gear', 'Auction house', 'Mog Bonanza', 'Gobbie Mystery Box', 'Login Campaign'])))
    guides.append(('Combat and skills', 'Server', 'Combat pace, monster strength, notorious monsters and trusts. Source: ' + src_server,
                   row_steps(['Combat pace', 'Monsters', 'Notorious monsters', 'Beastmasters', 'Seekers fights', 'Trusts'])))
    guides.append(('Quests, missions and content', 'Server', 'Which expansions and endgame content run on Vanadreams. Source: ' + src_server,
                   row_steps(['Content', 'Endgame built in 2026', 'Magian trials', 'Clan Centurio', 'Ambuscade', 'Aeonic weapons', 'Reives', 'Mog Garden', 'Escha and Reisenjima'])))
    guides.append(('Travel and quality of life', 'Server', 'Movement, level-capped zones, friends, linkshell and network help. Source: ' + src_server,
                   row_steps(['Movement', 'Promathia zones', 'Friends', 'Linkshell', 'Blocked network'])))
    left = [k for k in order if k not in used_rows]
    if left:
        guides.append(('Other changes', 'Server', 'The rest of the wiki\'s list of changes from the original game. Source: ' + src_server, row_steps(left)))
    if cmds:
        cst = []
        for c in sorted(cmds):
            cst.append((c, '\n'.join('• ' + t for t, _ in cmds[c])))
        guides.append(('Commands', 'Server', 'Server commands (starting with !) that the wiki mentions, with the sentence each appears in. Addon commands (/vg, /crafty, /vanafish, /dreamyah) are in those addons\' guides below. Source: ' + src_guide, cst))
    if pat:
        guides.append(('Patch history', 'Server', 'The wiki\'s patch history, newest first. Source: %s#guide-patches' % WIKI,
                       [('%s: %s' % (r[0], text(r[1])), '• ' + text(r[2])) for r in pat]))
    # each wiki guide page
    for key in sorted(d.contrib, key=lambda k: d.contrib[k][0].lower()):
        title = d.contrib[key][0]
        st = [(t, bullets(ls, 2500)) for t, ls in html_sections(d.contrib[key][1], 'Overview')][:30]
        if not st:
            continue
        first = html_lines(d.contrib[key][1])
        summ = first[0] if first else title
        if len(summ) > 240:
            summ = summ[:237].rsplit(' ', 1)[0] + '…'
        guides.append(('Guide: ' + title, 'Server', '%s Source: %s#guide-c_%s' % (summ, WIKI, key), st))

    path = os.path.join(out, 'server_notes.lua')
    with open(path, 'w', encoding='utf-8') as fh:
        header(fh, 'server_notes.lua', 'What is different on Vanadreams, from the wiki\'s own server guide pages. Read by the Server notes view.')
        fh.write('local S = {}\n\nS.guides = {\n')
        for g in guides:
            if g[3]:
                guide_line(fh, *g)
        fh.write('}\n\nreturn S\n')
    return path, sum(1 for g in guides if g[3])


def convert(raw, out):
    os.makedirs(out, exist_ok=True)
    d = Data(raw)
    p, n = gear(d, out)
    print('%s: %d items' % (p, n))
    p, n = skills(d, out)
    print('%s: %d guides' % (p, n))
    p, a, b = quest_guides(d, out)
    print('%s: %d quests + %d missions' % (p, a, b))
    p, n = server_notes(d, out)
    print('%s: %d guides' % (p, n))



if __name__ == '__main__':
    main()
