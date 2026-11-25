#!/usr/bin/env python3
"""Vanaguide :: tools/servers/legendaryrelaunch.py

Build per-server VanaGuide data for the FFXI private server "Legendary Relaunch"
(launcher world key: legendaryrelaunch) from its public MkDocs site, https://ffxi-legendary.com.

  fetch    robots.txt first (aborts if it disallows us), then the bulk endpoints
           /search/search_index.json, /assets/gear-data.json, /assets/item-search-data.json
           and the HTML of the pages listed in PAGES, into
           ~/Downloads/ffxi-server-data/legendaryrelaunch/raw/ (skipped if already present,
           unless --refresh).  Honest User-Agent, >= 1.5 s between requests, no login.
  convert  raw -> Vanaguide/data/servers/legendaryrelaunch/
             gear_guide.lua    gear-data.json items with a listed source, plus item-search-data
                               drops/sources; rare/ex from gear-data's flag bits (bit0 Ex, bit1 Rare)
             quest_guides.lua  the site's step-by-step progression pages, one step per section
             server_notes.lua  rates, systems, commands and rules, one step per page section
           No skill_guides.lua: the site lists no recipes or crafting skill-up bands.

Fetched content is untrusted data: it is parsed as JSON/HTML text only, never executed.

    python3 -I tools/servers/legendaryrelaunch.py [--refresh] [--raw DIR] [--out DIR]

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser

KEY = 'legendaryrelaunch'
BASE = 'https://ffxi-legendary.com/'
UA = 'VanaGuide-data/1.0 (+https://batesai.org; help@batesai.org)'
FETCHED = '2026-10-28'
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEF_RAW = os.path.expanduser('~/Downloads/ffxi-server-data/%s/raw' % KEY)
DEF_OUT = os.path.join(REPO, 'Vanaguide', 'data', 'servers', KEY)
LSB_SQL = '/Volumes/Games/FFXI/lsb/server/sql'

BULK = ['search/search_index.json', 'assets/gear-data.json', 'assets/item-search-data.json']

# server_notes topics: (guide name, [page paths])
NOTES = [
    ('Rates and progression', ['changes/', 'progression/subjob-exp/', 'progression/death-penalty/']),
    ('Gear and drops', ['reference/gear-vs-retail/', 'progression/reforge/', 'progression/weapon-forge/']),
    ('Crafting and gathering', ['economy/crafted-gear/']),
    ('Combat and skills', ['reference/ws-vs-retail/', 'progression/cross-job-abilities/',
                           'progression/cross-job-traits/', 'progression/spell-mastery/']),
    ('Travel and quality of life', ['reference/travel-and-warps/', 'progression/server-features/',
                                    'changes/background-systems/', 'economy/home-point/']),
    ('Commands', ['reference/commands/']),
    ('Rules', ['rules/']),
    ('Recent changes', ['changelog/']),
]
# quest_guides: step-by-step progression pages
QUESTS = ['getting-started/first-steps/', 'getting-started/your-session/', 'getting-started/leveling/',
          'getting-started/progression-guide/', 'progression/augmenting-guide/',
          'progression/weapon-journey/', 'progression/weapon-pilgrimage/', 'progression/prime-trials/']
PAGES = sorted({p for _, ps in NOTES for p in ps} | set(QUESTS))

MAX_BULLETS = 40
MAX_BULLET_LEN = 600
CHANGELOG_SECTIONS = 6


# ---------------------------------------------------------------- fetch

def raw_name(path):
    return (path.strip('/').replace('/', '_') or 'index') + ('' if path.endswith('.json') else '.html')


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read()


def fetch(raw, refresh):
    os.makedirs(raw, exist_ok=True)
    rp_path = os.path.join(raw, 'robots.txt')
    if refresh or not os.path.exists(rp_path):
        st, body = get(BASE + 'robots.txt')
        open(rp_path, 'wb').write(body)
        time.sleep(1.5)
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(open(rp_path, encoding='utf-8', errors='replace').read().splitlines())
    delay = max(1.5, float(rp.crawl_delay('ClaudeBot') or rp.crawl_delay('*') or 0))
    blocked = []
    for path in BULK + PAGES:
        url = BASE + path
        if not all(rp.can_fetch(a, url) for a in ('ClaudeBot', 'anthropic-ai', 'Claude-Web', '*')):
            blocked.append(url)
            continue
        dest = os.path.join(raw, raw_name(path))
        if os.path.exists(dest) and not refresh:
            continue
        try:
            st, body = get(url)
        except Exception as e:  # refused / challenged: stop, never retry around it
            print('FETCH FAILED %s: %s' % (url, e), file=sys.stderr)
            blocked.append(url)
            continue
        open(dest, 'wb').write(body)
        print('fetched %s (%d bytes)' % (url, len(body)))
        time.sleep(delay)
    if blocked:
        print('blocked/skipped: %s' % blocked, file=sys.stderr)
    return blocked


# ---------------------------------------------------------------- html -> sections

class Article(HTMLParser):
    """Split an MkDocs page's <article> into sections at h2: [(title, [bullets])]."""
    BLOCK = {'p', 'li', 'tr', 'h3', 'h4', 'dt', 'dd', 'summary'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0          # inside <article>
        self.skip = 0           # inside script/style/svg/nav/headerlink
        self.sections = [['', []]]
        self.buf = None
        self.tag = None
        self.cells = None
        self.header = None
        self.cell = None
        self.li_stack = 0
        self.h2 = None
        self.h1_seen = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'article':
            self.depth += 1
            return
        if not self.depth:
            return
        if tag in ('script', 'style', 'svg', 'nav', 'button') or 'headerlink' in (a.get('class') or ''):
            self.skip += 1
            return
        if self.skip:
            return
        if tag == 'h2' or (tag == 'h1' and self.h1_seen):
            self.h2 = []
        elif tag == 'h1':
            self.h1_seen = True
            self.skip += 1
        elif tag == 'tr':
            self.cells = []
        elif tag in ('td', 'th') and self.cells is not None:
            self.cell = []
        elif tag in ('p', 'li', 'h3', 'h4', 'dt', 'dd', 'summary') and self.cells is None:
            if tag == 'li':
                self.li_stack += 1
            if self.buf is not None and tag == 'li' and self.buf_text():
                self.flush()
            if self.buf is None or tag == 'li':
                self.buf = []
                self.tag = tag
        elif tag == 'br':
            self.text(' ')
        elif tag == 'thead':
            self.header = None

    def handle_endtag(self, tag):
        if tag == 'article':
            self.depth -= 1
            return
        if not self.depth:
            return
        if tag in ('script', 'style', 'svg', 'nav', 'button') or (tag in ('a', 'h1') and self.skip):
            if self.skip:
                self.skip -= 1
            return
        if self.skip:
            return
        if tag in ('h1', 'h2') and self.h2 is not None:
            self.sections.append([clean(''.join(self.h2)), []])
            self.h2 = None
        elif tag in ('td', 'th') and self.cell is not None:
            self.cells.append((tag, clean(''.join(self.cell))))
            self.cell = None
        elif tag == 'tr' and self.cells is not None:
            cells = self.cells
            self.cells = None
            if cells and all(t == 'th' for t, _ in cells):
                self.header = [c for _, c in cells]
            elif cells:
                vals = [c for _, c in cells]
                if self.header and len(self.header) == len(vals) and len(vals) > 1:
                    first = vals[0]
                    rest = ['%s %s' % (h, v) if h else v for h, v in zip(self.header[1:], vals[1:]) if v]
                    self.add('%s: %s' % (first, '; '.join(rest)) if rest else first)
                else:
                    self.add(' | '.join(v for v in vals if v))
        elif tag == 'table':
            self.header = None
        elif tag in ('p', 'li', 'h3', 'h4', 'dt', 'dd', 'summary') and self.buf is not None and self.tag == tag:
            self.flush()
        elif tag == 'li':
            self.li_stack = max(0, self.li_stack - 1)

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.text(data)

    def text(self, s):
        if self.h2 is not None:
            self.h2.append(s)
        elif self.cell is not None:
            self.cell.append(s)
        elif self.buf is not None:
            self.buf.append(s)

    def buf_text(self):
        return clean(''.join(self.buf or []))

    def flush(self):
        t = self.buf_text()
        if t:
            if self.tag in ('h3', 'h4', 'summary', 'dt'):
                t = t.rstrip(':') + ':'
            self.add(t)
        self.buf = None
        self.tag = None

    def add(self, t):
        t = clean(t)
        if t and (not self.sections[-1][1] or self.sections[-1][1][-1] != t):
            self.sections[-1][1].append(t)


def clean(s):
    s = html.unescape(s).replace('\u00b6', '').replace('\xa0', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def page_sections(raw, path):
    fn = os.path.join(raw, raw_name(path))
    if not os.path.exists(fn):
        return None, []
    src = open(fn, encoding='utf-8', errors='replace').read()
    m = re.search(r'<h1[^>]*>(.*?)</h1>', src, re.S)
    title = clean(re.sub(r'<[^>]+>', '', m.group(1))) if m else path
    p = Article()
    p.feed(src)
    secs = [(t, b) for t, b in p.sections if b]
    return title, secs


def split_weeks(secs):
    """The changelog is one long section; split it at its 'Week of ...' lines."""
    out = []
    for title, lines in secs:
        cur = [title, []]
        out.append(cur)
        for t in lines:
            if t.startswith('Week of '):
                cur = [t.rstrip(':'), []]
                out.append(cur)
            else:
                cur[1].append(t)
    return [(t, b) for t, b in out if b]


def bullets(lines):
    out = []
    for t in lines[:MAX_BULLETS]:
        if len(t) > MAX_BULLET_LEN:
            cut = t[:MAX_BULLET_LEN]
            cut = cut[:cut.rfind(' ')] if ' ' in cut else cut
            t = cut + ' …'
        out.append('• ' + t)
    if len(lines) > MAX_BULLETS:
        out.append('• (%d more lines on the source page)' % (len(lines) - MAX_BULLETS))
    return '\n'.join(out)


# ---------------------------------------------------------------- lua writers

def q(s):
    if s is None:
        return 'nil'
    s = str(s).replace('\\', '\\\\').replace("'", "\\'").replace('\r', '').replace('\n', '\\n')
    return "'" + s + "'"


def header(fn, what, source, extra=''):
    return ('-- Vanaguide :: data/servers/%s/%s\n'
            '-- GENERATED by tools/servers/%s.py from %s, fetched %s.  Do not hand-edit.\n'
            '-- %s\n%s'
            '-- Copyright (c) 2026 Bates LLC.  All rights reserved.\n'
            '-- Source content: ffxi-legendary.com (no licence stated on the site; facts are\n'
            '-- summarised and attributed, see the Source: line on each guide).\n\n'
            % (KEY, fn, KEY, source, FETCHED, what, extra))


def write_guides(path, head, guides):
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(head + 'local S = {}\n\nS.guides = {\n')
        for g in guides:
            fh.write('    { name = %s, group = %s, desc = %s, steps = {\n' % (q(g['name']), q(g['group']), q(g['desc'])))
            for st in g['steps']:
                fh.write('            { title = %s, note = %s },\n' % (q(st['title']), q(st['note'])))
            fh.write('        } },\n')
        fh.write('}\n\nreturn S\n')


# ---------------------------------------------------------------- zone / LSB helpers

def zone_ids():
    ids = {}
    fn = os.path.join(REPO, 'Vanaguide', 'data', 'zone_names.lua')
    for m in re.finditer(r"\[(\d+)\] = '((?:[^'\\]|\\.)*)'", open(fn, encoding='utf-8').read()):
        name = m.group(2).replace("\\'", "'")
        ids.setdefault(norm(name), int(m.group(1)))
    return ids


def norm(s):
    return re.sub(r'[^a-z0-9\[\]]', '', s.lower())


def lsb_flags():
    out = {}
    fn = os.path.join(LSB_SQL, 'item_basic.sql')
    if not os.path.exists(fn):
        return out
    rx = re.compile(r"INSERT INTO `item_basic` VALUES \((\d+),\d+,'(?:[^'\\]|\\.)*','(?:[^'\\]|\\.)*',"
                    r"'(?:[^'\\]|\\.)*',[^,]+,\d+,([^,]*),")
    for line in open(fn, encoding='utf-8', errors='replace'):
        m = rx.match(line)
        if m:
            out[int(m.group(1))] = ('FLAG_RARE' in m.group(2), 'FLAG_EX' in m.group(2))
    return out


# ---------------------------------------------------------------- gear

SLOT_BITS = [(1, 'main'), (2, 'sub'), (4, 'ranged'), (8, 'ammo'), (16, 'head'), (32, 'body'), (64, 'hands'),
             (128, 'legs'), (256, 'feet'), (512, 'neck'), (1024, 'waist'), (2048, 'ear'), (4096, 'ear'),
             (8192, 'ring'), (16384, 'ring'), (32768, 'back')]

CATS = [
    ('craft', 'Craftable', 'Listed by the server as made by synthesis. The site does not give the recipe.'),
    ('vendor', 'Merchants', 'Sold by a server NPC: the Gear Vendors, the !shop command, the Infamy Vendor, the Cosmetic Boutique or GM Home.'),
    ('drop', 'Monster Drops', 'Dropped by monsters, with the drop rate the server lists.'),
    ('reforge', 'Reforge and Forges', 'Upgraded through the server\'s Reforge, Weapon Forge, Divergence +4 Forge and Unity upgrade systems.'),
    ('endgame', 'Custom Endgame', 'Earned from the server\'s endgame content: Ambuscade, HTBF, Geas Fete, Unity Wanted NMs, Nyzul Isle, Omen, Voidwatch, Domain, Dynamis [D], Hades, dungeons and similar.'),
]
SRC_CAT = {
    'Crafting': 'craft',
    'Gear Vendor': 'vendor', '!shop': 'vendor', 'Infamy Vendor': 'vendor', 'Cosmetic Boutique': 'vendor',
    'GM Home': 'vendor',
    'Reforge': 'reforge', 'Weapon Forge': 'reforge', 'Divergence +4 Forge': 'reforge', 'Unity upgrade': 'reforge',
    'Augment Moogle': 'reforge',
}
SRC_TEXT = {
    'Crafting': 'Crafted (the server lists it as craftable; recipe not given)',
    'Gear Vendor': 'Sold by the Gear Vendors (Armor / Weapons Vendor, for seals)',
    '!shop': 'Sold through the !shop command',
    'Reforge': 'Reforge system (upgrade with AF, Relic or Empyrean Marks)',
    'HTBF': 'High-Tier Battlefields (HTBF)',
    'Dungeon (Infamy)': 'Dungeons (Infamy)',
}


def gear(raw, out):
    gd = json.load(open(os.path.join(raw, raw_name('assets/gear-data.json')), encoding='utf-8'))
    isd = json.load(open(os.path.join(raw, raw_name('assets/item-search-data.json')), encoding='utf-8'))
    jobs = gd['meta']['jobs']
    search = {x['i']: x for x in isd['items']}
    zones = zone_ids()
    lflags = lsb_flags()
    rows = []
    for it in gd['items']:
        iid = it['i']
        sx = search.get(iid, {})
        how, cats, seen = [], [], set()

        def add(kind, cat, text, zone=None, npc=None):
            k = (kind, text, zone)
            if k in seen:
                return
            seen.add(k)
            how.append((kind, text, zone, npc))
            if cat not in cats:
                cats.append(cat)

        labels = [s['s'] for s in it.get('src', []) if 's' in s] + list(sx.get('s', []))
        for lab in labels:
            cat = SRC_CAT.get(lab, 'endgame')
            kind = {'craft': 'craft', 'vendor': 'vendor', 'reforge': 'upgrade', 'endgame': 'content'}[cat]
            add(kind, cat, SRC_TEXT.get(lab, lab))
        drops = [(s['m'], s.get('z'), s.get('p')) for s in it.get('src', []) if 'm' in s]
        drops += [(d.get('mob'), d.get('zone'), d.get('pct')) for d in sx.get('d', [])]
        for mob, zone, pct in drops:
            if not mob:
                continue
            zid = zones.get(norm(zone)) if zone else None
            where = '' if zid is not None or not zone else ' in %s' % zone
            rate = ' (%s%%)' % ('%g' % float(pct)) if pct is not None else ''
            if mob.startswith('HTBF:'):
                add('content', 'endgame', 'High-Tier Battlefield %s%s' % (mob[5:].strip(), rate))
            else:
                add('drop', 'drop', 'Dropped by %s%s%s' % (mob, rate, where), zid, None)
        if not how:
            continue
        slot = next((n for b, n in SLOT_BITS if it['s'] & b), 'other')
        jm = it['j']
        if jm & 0x3FFFFF == 0x3FFFFF:
            jt = 'All jobs'
        else:
            jt = ' '.join(j for i, j in enumerate(jobs) if jm & (1 << i)) or 'No jobs (cannot be equipped)'
        if 'f' in it:
            rare, ex = bool(it['f'] & 2), bool(it['f'] & 1)
        else:
            rare, ex = lflags.get(iid, (False, False))
        name = sx.get('n') or it['n']
        rows.append((name.lower(), iid, name, it.get('l') or 0, slot, jt, rare, ex, cats, how))
    rows.sort(key=lambda r: (r[3], r[0], r[1]))
    counts = {c[0]: 0 for c in CATS}
    for r in rows:
        for c in r[8]:
            counts[c] += 1
    path = os.path.join(out, 'gear_guide.lua')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(header('gear_guide.lua',
                        'Equipment with a source on this server, from the site\'s Gear Finder and Item Finder data.',
                        'ffxi-legendary.com/assets/gear-data.json + item-search-data.json',
                        '-- how = { kind, text, zone id or nil, npc or nil }.  Rare/Ex from gear-data flag bits\n'
                        '-- (bit0 Ex, bit1 Rare); LSB item_basic.sql only where gear-data has no flags.\n'))
        fh.write('local G = {}\n\nG.categories = {\n')
        for cid, cname, cdesc in CATS:
            fh.write('    { id = %s, name = %s, desc = %s, count = %d },\n' % (q(cid), q(cname), q(cdesc), counts[cid]))
        fh.write('}\n\nG.items = {\n')
        for _, iid, name, lvl, slot, jt, rare, ex, cats, how in rows:
            hs = ', '.join('{ %s, %s, %s, %s }' % (q(k), q(t), 'nil' if z is None else z, q(n)) for k, t, z, n in how)
            fh.write('    { id = %d, name = %s, level = %d, slot = %s, jobs = %s, rare = %s, ex = %s, cats = %s, how = { %s } },\n'
                     % (iid, q(name), lvl, q(slot), q(jt), str(rare).lower(), str(ex).lower(), q(' '.join(cats)), hs))
        fh.write('}\n\nreturn G\n')
    return path, len(rows), gd.get('generated_at'), isd.get('generated_at')


# ---------------------------------------------------------------- notes / quests

def notes(raw, out, blocked, gen_times):
    guides = []
    covered = []
    for name, pages in NOTES:
        steps, urls = [], []
        for p in pages:
            title, secs = page_sections(raw, p)
            if not secs:
                continue
            urls.append(BASE + p)
            if p == 'changelog/':
                secs = split_weeks(secs)[:CHANGELOG_SECTIONS + 1]
            for st, lines in secs:
                t = '%s: %s' % (title, st) if st else title
                if len(pages) == 1 and st:
                    t = st
                steps.append({'title': t, 'note': bullets(lines)})
        if steps:
            covered.append(name)
            desc = {'Recent changes': 'The newest entries of the server changelog (older entries are on the page).'}.get(
                name, 'What the server\'s own site says about %s.' % name.lower())
            guides.append({'name': name, 'group': 'Server', 'desc': desc + ' Source: ' + ', '.join(urls), 'steps': steps})
    about = [
        {'title': 'What was fetched', 'note': '\n'.join([
            '• Site: https://ffxi-legendary.com (the server\'s own MkDocs wiki), fetched %s.' % FETCHED,
            '• robots.txt: no Disallow rules and no content-signal values for any agent; nothing was skipped.'
            if not blocked else '• Skipped (robots.txt or refused): ' + ', '.join(blocked),
            '• Bulk data: /assets/gear-data.json (generated %s) and /assets/item-search-data.json (generated %s).' % gen_times,
            '• %d wiki pages, read section by section: %s.' % (len(PAGES), ', '.join(PAGES)),
        ])},
        {'title': 'How it was turned into this guide', 'note': '\n'.join([
            '• Gear: every item in gear-data.json with a source label or drop, plus the drops and sources item-search-data.json lists for it.',
            '• Server notes: each step is one section of a site page; bullets are the page\'s own sentences, list items and table rows.',
            '• Quests: the site\'s step-by-step getting-started and progression pages, one step per section.',
            '• Long sections are cut at %d lines; the source page has the rest.' % MAX_BULLETS,
        ])},
        {'title': 'Not covered', 'note': '\n'.join([
            '• No crafting recipes or skill-up bands: the site does not publish them, so there is no Skills data for this server.',
            '• No retail story quests or missions: the site does not walk through them; use the standard guides.',
            '• Gear items the site lists with no source at all are left out.',
            '• Pages other than the ones named above (endgame content pages, spell lists, leaderboards) are not summarised here; see the site.',
            '• Values change with server updates; the site\'s own pages are the authority.',
        ])},
    ]
    guides.insert(0, {'name': 'About this data', 'group': 'Server',
                      'desc': 'What this server data was built from, when, and what it leaves out. Source: %srobots.txt, %ssearch/search_index.json' % (BASE, BASE),
                      'steps': about})
    path = os.path.join(out, 'server_notes.lua')
    write_guides(path, header('server_notes.lua', 'Server notes: rates, systems, commands and rules.', 'ffxi-legendary.com wiki pages'), guides)
    return path, len(guides)


def quests(raw, out):
    guides = []
    for p in QUESTS:
        title, secs = page_sections(raw, p)
        if not secs:
            continue
        intro = ''
        if secs and not secs[0][0]:
            intro = secs[0][1][0] if secs[0][1] else ''
        steps = []
        n = 0
        for st, lines in secs:
            n += 1
            steps.append({'title': st or 'Overview', 'note': bullets(lines)})
        summary = intro if len(intro) <= 300 else intro[:300].rsplit(' ', 1)[0] + ' …'
        guides.append({'name': title, 'group': 'Custom',
                       'desc': (summary + ' ' if summary else '') + 'Source: ' + BASE + p, 'steps': steps})
    path = os.path.join(out, 'quest_guides.lua')
    write_guides(path, header('quest_guides.lua', 'Step-by-step progression guides from the server\'s own wiki.', 'ffxi-legendary.com wiki pages'), guides)
    return path, len(guides)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--refresh', action='store_true')
    ap.add_argument('--raw', default=DEF_RAW)
    ap.add_argument('--out', default=DEF_OUT)
    a = ap.parse_args()
    blocked = fetch(a.raw, a.refresh)
    os.makedirs(a.out, exist_ok=True)
    gp, gn, t1, t2 = gear(a.raw, a.out)
    print('%s: %d items' % (gp, gn))
    qp, qn = quests(a.raw, a.out)
    print('%s: %d guides' % (qp, qn))
    np_, nn = notes(a.raw, a.out, blocked, (t1, t2))
    print('%s: %d guides' % (np_, nn))


if __name__ == '__main__':
    main()
