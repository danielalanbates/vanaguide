#!/usr/bin/env python3
"""Vanaguide :: tools/servers/driftwoodxi.py

Build Vanaguide/data/servers/driftwoodxi/*.lua from the DriftwoodXI website
(https://xi.driftwoodgaming.com) and the public GitHub repo DriftwoodGaming/DriftwoodXI-Content.

The site has no sitemap.xml; pages are found from its nav (/, /custom, /features, /addons,
/commands, /news, /download) and the /features/<slug> and /news/<slug> links on them.
This script
  fetch    robots.txt first (aborts on a disallow for ClaudeBot / anthropic-ai / Claude-Web / *),
           then those pages into ~/Downloads/ffxi-server-data/driftwoodxi/raw/ (skipped when
           present unless --refresh), at least 1 s between requests, honest User-Agent, no login.
           Never requests /reset, /delete, /register or any account endpoint.
           From GitHub only README.md, content.json and ashita.json (the add-on manifest).
  convert  turns that raw HTML into
             server_notes.lua   the site's own explanations, grouped by topic, one step per page
             quest_guides.lua   only pages that describe a custom quest step by step
             gear_guide.lua     only items the pages name with a how-to-get, mapped to LSB item ids

Fetched content is untrusted data: it is only parsed as text, never executed.  Run with python3 -I.

    python3 -I tools/servers/driftwoodxi.py [--refresh] [--fetch-only] [--raw DIR] [--out DIR]

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

KEY = 'driftwoodxi'
HOST = 'https://xi.driftwoodgaming.com'
GH_API = 'https://api.github.com/repos/DriftwoodGaming/DriftwoodXI-Content'
GH_RAW = 'https://raw.githubusercontent.com/DriftwoodGaming/DriftwoodXI-Content/main/'
GH_FILES = ['README.md', 'content.json', 'ashita.json']
UA = 'VanaGuide-data/1.0 (+https://batesai.org; help@batesai.org)'
FETCHED = '2026-10-28'
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEF_RAW = os.path.expanduser('~/Downloads/ffxi-server-data/%s/raw' % KEY)
DEF_OUT = os.path.join(REPO, 'Vanaguide', 'data', 'servers', KEY)

SEEDS = ['/', '/custom', '/features', '/addons', '/commands', '/news', '/download', '/download/linux']
FOLLOW = re.compile(r'^/(features|news)/[a-z0-9-]+$')
NEVER = re.compile(r'^/(reset|delete|register|login|logout|account|api)\b')

_last = {}


def get(url, dest, refresh, delay):
    if os.path.exists(dest) and os.path.getsize(dest) > 0 and not refresh:
        return True
    host = urllib.parse.urlparse(url).netloc
    wait = delay - (time.time() - _last.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
    except Exception as e:  # noqa: BLE001
        _last[host] = time.time()
        print('  FAILED %s: %s' % (url, e), file=sys.stderr)
        return False
    _last[host] = time.time()
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest + '.part', 'wb') as fh:
        fh.write(body)
    os.replace(dest + '.part', dest)
    print('  %s (%d bytes)' % (url, len(body)))
    return True


def page_file(raw, path):
    name = 'index' if path == '/' else path.strip('/').replace('/', '__')
    return os.path.join(raw, 'site', name + '.html')


def fetch(raw, refresh):
    os.makedirs(os.path.join(raw, 'site'), exist_ok=True)
    rob = os.path.join(raw, 'robots.txt')
    if not get(HOST + '/robots.txt', rob, refresh, 1.0):
        sys.exit('robots.txt unavailable: not fetching')
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(open(rob, encoding='utf-8', errors='replace').read().splitlines())
    delay = 1.0
    for agent in ('ClaudeBot', 'anthropic-ai', 'Claude-Web', '*'):
        cd = rp.crawl_delay(agent)
        if cd:
            delay = max(delay, float(cd))

    def allowed(path):
        return not NEVER.match(path) and all(
            rp.can_fetch(a, HOST + path) for a in ('ClaudeBot', 'anthropic-ai', 'Claude-Web', '*'))

    seen, queue, skipped = set(), list(SEEDS), []
    while queue:
        p = queue.pop(0)
        if p in seen:
            continue
        seen.add(p)
        if not allowed(p):
            skipped.append(p)
            continue
        dest = page_file(raw, p)
        if not get(HOST + p, dest, refresh, delay):
            continue
        body = open(dest, encoding='utf-8', errors='replace').read()
        for href in re.findall(r'href="(/[^"#?]*)', body):
            if FOLLOW.match(href) and href not in seen:
                queue.append(href)
    with open(os.path.join(raw, 'skipped.txt'), 'w') as fh:
        fh.write('\n'.join(skipped))
    # GitHub: repo metadata + manifest files only (the package zips are client add-on code).
    get(GH_API, os.path.join(raw, 'github', 'repo.json'), refresh, 1.0)
    for f in GH_FILES:
        get(GH_RAW + f, os.path.join(raw, 'github', f), refresh, 1.0)


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


# ---------------------------------------------------------------- convert: HTML -> blocks

from html.parser import HTMLParser  # noqa: E402

SKIP_CLASSES = ('crumb', 'post-nav', 'custom-jumps', 'policy-jumps', 'post-meta', 'addon-shot',
                'eyebrow', 'policy-group-count', 'signpost', 'addon-grid', 'btn')
BLOCKS = ('h1', 'h2', 'h3', 'h4', 'p', 'li', 'tr', 'dt', 'dd', 'blockquote', 'pre')
VOID = ('img', 'br', 'hr', 'input', 'meta', 'link', 'source', 'wbr')


class Blocks(HTMLParser):
    """<main> -> [(kind, text)].  kind is a block tag, 'entry' (a command / add-on entry) or
    'usage'.  Text is whitespace-normalised; nothing in the page is ever executed."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.buf, self.kind = [], [], None
        self.in_main = False
        self.stack = []          # (tag, skip, entry)
        self.skip = 0
        self.entry = None        # list of parts while inside an entry div
        self.usage = False

    def flush(self):
        t = re.sub(r'\s+', ' ', ''.join(self.buf)).strip()
        if t and self.kind and self.entry is None:
            self.out.append((self.kind, t))
        elif t and self.entry is not None:
            self.entry.append(t)
        self.buf = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get('class') or ''
        if tag == 'main':
            self.in_main = True
        if not self.in_main or tag in VOID:
            if tag == 'br':
                self.buf.append(' ')
            return
        skip = tag in ('script', 'style', 'figure', 'nav', 'svg', 'button', 'form') or \
            any(c in cls.split() for c in SKIP_CLASSES)
        ent = tag == 'div' and ('cmd-entry' in cls.split() or 'policy-entry' in cls.split())
        istag = 'tag' in cls.split() and self.entry is not None
        self.stack.append((tag, skip, ent, 'cmd-usage' in cls.split(), istag))
        if skip:
            self.skip += 1
            return
        if self.skip:
            return
        if ent:
            self.flush()
            self.entry = []
            return
        if 'cmd-usage' in cls.split():
            self.flush()
            self.usage = True
            if self.entry is not None:
                self.entry.append('Usage:')
            return
        if tag == 'code' and self.usage:
            self.flush()
            return
        if tag in ('td', 'th') and self.buf:
            self.buf.append(' | ')
        if istag:
            self.buf.append(' (')
        if tag in BLOCKS:
            self.flush()
            self.kind = tag

    def handle_endtag(self, tag):
        if not self.in_main:
            return
        if tag == 'main':
            self.flush()
            self.in_main = False
            return
        # pop to the matching tag (tolerates unclosed <p>/<li>)
        idx = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                idx = i
                break
        if idx is None:
            return
        for t, skip, ent, usage, istag in reversed(self.stack[idx:]):
            if skip:
                self.skip -= 1
                continue
            if self.skip:
                continue
            if ent:
                self.flush()
                if self.entry:
                    self.out.append(('entry', join_entry(self.entry)))
                self.entry = None
            elif usage:
                self.flush()
                self.usage = False
                if self.entry is not None:
                    self.entry.append('\x00')
            elif t == 'code' and self.usage:
                self.flush()
            elif istag:
                self.buf.append(')')
            elif t in BLOCKS:
                self.flush()
                self.kind = None
        del self.stack[idx:]

    def handle_data(self, data):
        if self.in_main and not self.skip:
            self.buf.append(data)


def join_entry(parts):
    """Entry segments -> one line: 'name (tag) \u2014 short. Usage: a; b; c \u2014 note'."""
    out, usage = [], None
    for x in parts:
        if x == 'Usage:':
            usage = []
        elif x == '\x00':
            if usage:
                out.append('Usage: ' + '; '.join(usage))
            usage = None
        elif usage is not None:
            usage.append(x)
        else:
            out.append(x)
    txt = ' \u2014 '.join(out)
    return re.sub(r'\s+\(\s*', ' (', re.sub(r'\s*\)', ')', txt))


def page_meta(raw_html):
    m = {}
    t = re.search(r'<span class="tag">([^<]*)</span>\s*<time datetime="([^"]+)"', raw_html)
    if t:
        m['tag'], m['date'] = html.unescape(t.group(1)), t.group(2)[:10]
    ex = re.search(r'(?s)<p class="post-excerpt">(.*?)</p>', raw_html)
    if ex:
        m['excerpt'] = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', ex.group(1)))).strip()
    for cls in ('addon-short', 'lede-left', 'cmd-short'):
        pass
    return m


def load_pages(raw):
    pages = {}
    site = os.path.join(raw, 'site')
    for f in sorted(os.listdir(site)):
        if not f.endswith('.html'):
            continue
        path = '/' + f[:-5].replace('__', '/')
        if path in ('/index', '/news', '/features'):
            continue  # home page has live player counts; the two indexes only repeat their posts' excerpts
        body = open(os.path.join(site, f), encoding='utf-8', errors='replace').read()
        if '<title>Not found' in body:
            continue
        p = Blocks()
        p.feed(body)
        p.close()
        blocks = list(p.out)
        meta = page_meta(body)
        title = next((t for k, t in blocks if k == 'h1'), path)
        blocks = [(k, t) for k, t in blocks if k != 'h1' and t != meta.get('excerpt')]
        pages[path] = dict(path=path, url=HOST + path, title=title, blocks=blocks, **meta)
    return pages


# ---------------------------------------------------------------- convert: blocks -> notes

MAX_BULLET = 320
MAX_BULLETS = 10

SENT = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"\u201c(])')


def clip(t, n=MAX_BULLET):
    """Shorten to whole sentences.  Never cuts inside a sentence: when the first sentence alone is
    longer than n it is kept whole."""
    if len(t) <= n:
        return t
    out = ''
    for s in SENT.split(t):
        if len(out) + len(s) + 1 > n:
            break
        out = (out + ' ' + s).strip()
    return out or SENT.split(t)[0]


def section_bullets(blocks, entry_len=MAX_BULLET, cap=MAX_BULLETS):
    """Blocks of one section -> bullets.  Lists, table rows and entries are kept whole-ish; each
    paragraph contributes its leading sentences.  A heading (h3/h4) is glued onto what follows."""
    bullets, head = [], None
    for k, t in blocks:
        if k in ('h3', 'h4'):
            head = t.rstrip(':')
            continue
        if k == 'entry':
            b = clip(t, entry_len)
        elif k == 'usage':
            continue
        else:
            b = clip(t)
        if head:
            b = '%s: %s' % (head, b)
            head = None
        bullets.append(b)
    if cap and len(bullets) > cap:
        bullets = bullets[:cap]
    return bullets


def split_h2(blocks):
    """[(heading or None, [blocks])] split on h2."""
    out, cur, head = [], [], None
    for k, t in blocks:
        if k == 'h2':
            if cur:
                out.append((head, cur))
            cur, head = [], t
        else:
            cur.append((k, t))
    if cur:
        out.append((head, cur))
    return out


def note(bullets):
    return '\n'.join('\u2022 ' + b for b in bullets)


# Topic of each page: first matching pattern on its path wins.
TOPICS = [
    ('Commands', [r'^/commands$', r'every-command-on-one-page', r'custom-commands-and-modules',
                  r'your-login-commands']),
    ('Add-ons and the allowed list', [r'^/addons$', r'^/features$', r'nine-addons', r'allowed-addons',
                                       r'dwhub', r'dwmacro', r'dwreport', r'dwchat', r'dwparse',
                                       r'dwtracker', r'dwleaderboard', r'dwscan', r'dwcon$']),
    ('Your squad (alt-trusts)', [r'squad', r'dwgambits', r'dwengage', r'dwmerc', r'ten-sets',
                                 r'your-characters-keep-working', r'mercenary-battles', r'dread-beasts',
                                 r'the-fight-finds-you']),
    ('Rates and progression', [r'rates-and-progression', r'launch-balance-pass', r'ascension',
                               r'if-it-pays-it-counts', r'every-swing-counts', r'they-notice-you-later',
                               r'dwmerits', r'dwjobs', r'one-account-sixteen', r'welcome-to-driftwoodxi']),
    ('Expansions, quests and missions', [r'content-unlocked', r'one-expansion-at-a-time',
                                         r'finishing-chains-of-promathia', r'treasures-of-aht-urhgan',
                                         r'wings-of-the-goddess', r'seekers-of-adoulin', r'the-drift-board',
                                         r'the-special-shelf', r'dwquest', r'dwtoau', r'dwtod', r'dwfame',
                                         r'septembers-retail-patch']),
    ('Crafting and gathering', [r'craft', r'fishing', r'digging', r'the-artisan', r's-ranks']),
    ('Gear and drops', [r'drops-gil', r'treasure-caskets', r'rare-drops', r'the-outfitter', r'armsdealer',
                        r'driftmark-armory', r'armor-ladder', r'empyrean', r'relic', r'runes-bank',
                        r'disenchant', r'drift-exchange', r'exchange-gets-a-window', r'weapon-casts',
                        r'x-magic', r'heavenward-howl', r'dwspoils', r'conquest-point-exchange']),
    ('Endgame content', [r'nemesis', r'unleashed', r'raid', r'chain-trials', r'the-circuit',
                         r'any-arena', r'stone-and-tide', r'wind-pair', r'end-game-balancing',
                         r'break-damage-limit', r'esper', r'magicite', r'dwarena']),
    ('Combat and jobs', [r'balance-pass', r'combat-power', r'black-mage', r'blue-magic',
                         r'a-cleaner-log', r'ankabut']),
    ('Account, storage and economy', [r'inventory', r'thousand-slots', r'warehouse', r'politics',
                                      r'office-pays', r'dwbags', r'dwah', r'player-market', r'dwcpx']),
    ('Travel and quality of life', [r'teleporting', r'using-port', r'dwport', r'camera', r'controller',
                                    r'close-the-wiki-tab', r'website-is-open']),
    ('Client and launcher', [r'launcher', r'verify-your-game-files', r'defender', r'working-client',
                             r'hd-', r'linux', r'streamer', r'black-screen', r'^/download']),
]


def topic_of(path):
    for name, pats in TOPICS:
        if any(re.search(p, path) for p in pats):
            return name
    return 'Other news'


def page_steps(pg):
    """One page -> steps.  A feature page is one step; a news post is an intro step plus one per h2."""
    steps = []
    short = pg['title']
    if len(short) > 60:
        short = clip(short, 60)
    date = (' (%s)' % pg['date']) if pg.get('date') else ''
    for i, (head, blocks) in enumerate(split_h2(pg['blocks'])):
        bl = section_bullets(blocks)
        if i == 0 and head is None:
            if pg.get('excerpt'):
                bl = [clip(pg['excerpt'])] + bl
            title = pg['title'] + date
            bl = bl[:MAX_BULLETS]
        else:
            title = '%s \u2014 %s' % (short, head) if head else short
        if bl:
            steps.append(dict(title=title, note=note(bl)))
    if not steps and pg.get('excerpt'):
        steps.append(dict(title=pg['title'] + date, note=note([clip(pg['excerpt'])])))
    return steps


def whole_page_guide(pg, name, desc, entry_len=MAX_BULLET, cap=40):
    steps = []
    for head, blocks in split_h2(pg['blocks']):
        bl = section_bullets(blocks, entry_len=entry_len, cap=cap)
        if bl:
            steps.append(dict(title=head or pg['title'], note=note(bl)))
    return dict(name=name, group='Server', desc='%s Source: %s' % (desc, pg['url']), steps=steps)


def lua_str(s):
    return "'" + str(s).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n') + "'"


def header(fname, extra=()):
    lines = ['-- Vanaguide :: data/servers/%s/%s' % (KEY, fname),
             '-- GENERATED by tools/servers/%s.py from %s and github.com/DriftwoodGaming/DriftwoodXI-Content,'
             ' fetched %s.  Do not hand-edit.' % (KEY, HOST, FETCHED),
             '-- Source text is (c) DriftwoodXI / Driftwood Gaming; no open licence is stated on the site or',
             '-- the GitHub repo.  Entries are short attributed excerpts; every guide desc or how text names',
             '-- the page it came from.']
    lines += ['-- ' + e for e in extra]
    lines += ['--', '-- Copyright (c) 2026 Bates LLC.  All rights reserved.', '']
    return '\n'.join(lines) + '\n'


def write_guides(path, fname, guides, var='S'):
    out = [header(fname), 'local %s = {}' % var, '', '%s.guides = {' % var]
    for g in guides:
        out.append('    { name = %s, group = %s, desc = %s, steps = {' % (lua_str(g['name']), lua_str(g['group']),
                                                                         lua_str(g['desc'])))
        out.append(',\n'.join('            { title = %s, note = %s }' % (lua_str(s['title']), lua_str(s['note']))
                               for s in g['steps']))
        out.append('    } },')
    out += ['}', '', 'return %s' % var, '']
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out))


def github_guide(raw):
    gdir = os.path.join(raw, 'github')
    try:
        content = json.load(open(os.path.join(gdir, 'content.json'), encoding='utf-8'))
    except (OSError, ValueError):
        return None
    pk = content.get('packages', [])
    bl = ['%s %s: %s' % (p.get('id'), p.get('version'), clip(str(p.get('summary') or ''), 200)) for p in pk]
    steps = [dict(title='Content feed %s (%d add-ons)' % (content.get('contentVersion'), len(pk)), note=note(bl))]
    try:
        ash = json.load(open(os.path.join(gdir, 'ashita.json'), encoding='utf-8'))
        steps.append(dict(title='Ashita bundle', note=note([
            'Bundle version %s; Ashita core %s.' % (ash.get('version'), (ash.get('core') or {}).get('version'))])))
    except (OSError, ValueError):
        pass
    return dict(name='Add-on versions (launcher feed)', group='Server',
                desc='The add-ons the DriftwoodXI launcher installs, with their versions and one-line summaries, '
                     'from the public content feed the launcher reads. Source: '
                     'https://github.com/DriftwoodGaming/DriftwoodXI-Content (content.json, ashita.json)',
                steps=steps)


# ---------------------------------------------------------------- convert: gear

GEAR = [
    # (page path, phrase that must appear on that page, display name, item_basic name, level filter,
    #  how list)
]
RELICS = ['Spharai', 'Mandau', 'Excalibur', 'Ragnarok', 'Guttler', 'Bravura', 'Gungnir', 'Apocalypse',
          'Kikoku', 'Amanomurakumo', 'Mjollnir', 'Claustrum', 'Annihilator', 'Gjallarhorn', 'Yoichinoyumi']
ARMS = 'Drift Board (/quests), ArmsDealer tab'
for _n in RELICS:
    GEAR.append(('/news/relics-at-the-armsdealer', _n, _n, (75, 0),
                 [('exchange', ARMS + ', Dynamis Weapons case: 250 Drift Coins (level 75, Rare/Ex)', None, None)]))
for _n, _c in (('Almace', 1000), ('Caladbolg', 1000), ('Verethragna', 1000), ('Daurdabla', 1500), ('Ochain', 1500)):
    GEAR.append(('/news/empyrean-weapons-and-oboro', _n, _n, (99, 0),
                 [('exchange', ARMS + ': %s Drift Coins (level 99, without afterglow)' % '{:,}'.format(_c), None, None)]))
for _n in ('Idris', 'Epeolatry'):
    GEAR.append(('/features/dwquest', _n, _n, (99, 119),
                 [('exchange', ARMS + ', Ergon Weapons case: 1,000 Drift Coins', None, None)]))
for _n, _c in (('Abyssal Earring', 100), ('Beastly Earring', 100), ('Bushinomimi', 100), ("Knight's Earring", 100),
               ('Suppanomimi', 100), ('Brutal Earring', 200), ('Loquacious Earring', 200), ('Stealth Earring', 200),
               ('Rajas Ring', 300), ('Sattva Ring', 300), ('Tamas Ring', 300)):
    _w = _n.split()[0]
    GEAR.append(('/news/the-armor-ladder-and-the-jeweler', _w, _n, None,
                 [('exchange', 'Drift Board (/quests), Jeweler tab: %d Drift Coins (Rare/Ex)' % _c, None, None)]))
GEAR.append(('/news/the-artisan-lu-shang-and-a-walk-back', "Lu Shang's Fishing Rod", "Lu Shang's Fishing Rod", None,
             [('exchange', 'Drift Board (/quests), Artisan tab: 500 Drift Coins, no rank needed, one per character while you hold one; a broken rod is mended by Irmilant in Rabao instead', None, None),
              ('quest', 'Trade 5,000 carp to the brothers in Port San d\'Oria', 232, None)]))

SLOTS = [(0x0001, 'main'), (0x0002, 'sub'), (0x0004, 'ranged'), (0x0008, 'ammo'), (0x0010, 'head'),
         (0x0020, 'body'), (0x0040, 'hands'), (0x0080, 'legs'), (0x0100, 'feet'), (0x0200, 'neck'),
         (0x0400, 'waist'), (0x0800, 'ear'), (0x2000, 'ring'), (0x8000, 'back')]
JOBS = ['WAR', 'MNK', 'WHM', 'BLM', 'RDM', 'THF', 'PLD', 'DRK', 'BST', 'BRD', 'RNG', 'SAM',
        'NIN', 'DRG', 'SMN', 'BLU', 'COR', 'PUP', 'DNC', 'SCH', 'GEO', 'RUN']


def jobs_text(mask):
    if mask == 0 or mask & ((1 << 22) - 1) == (1 << 22) - 1:
        return 'All jobs'
    return ' '.join(j for i, j in enumerate(JOBS) if mask & (1 << i))


def norm(s):
    return re.sub(r'[^a-z0-9_.]', '', s.lower().replace(' ', '_'))


def lsb_items(sqldir):
    basic, equip = {}, {}
    rx = re.compile(r"^INSERT INTO `item_basic` VALUES \((\d+),\d+,'((?:[^'\\]|\\.)*)','((?:[^'\\]|\\.)*)',"
                    r"'(?:[^'\\]|\\.)*',[^,]*,[^,]*,([^,]*),")
    for line in open(os.path.join(sqldir, 'item_basic.sql'), encoding='utf-8', errors='replace'):
        m = rx.match(line)
        if m:
            basic[int(m.group(1))] = (m.group(2), m.group(3), m.group(4))
    rx = re.compile(r"^INSERT INTO `item_equipment` VALUES \((\d+),'([^']*)',(\d+),(\d+),(\d+),(\d+),\d+,\d+,(\d+),")
    for line in open(os.path.join(sqldir, 'item_equipment.sql'), encoding='utf-8', errors='replace'):
        m = rx.match(line)
        if m:
            i = int(m.group(1))
            equip[i] = dict(name=m.group(2), level=int(m.group(3)), ilevel=int(m.group(4)), jobs=int(m.group(5)),
                            mid=int(m.group(6)), slot=int(m.group(7)))
    return basic, equip


def find_item(display, lvl, basic, equip):
    n = norm(display.replace("'", ''))
    cands = [i for i, (bn, sn, _) in basic.items() if i in equip and
             (bn == n or sn == n or re.fullmatch(re.escape(n) + r'_\d+', bn) or equip[i]['name'] == n)]
    if not cands:
        return None, 'no LSB item named %s' % n
    if lvl:
        tier = [i for i in cands if equip[i]['level'] == lvl[0] and equip[i]['ilevel'] == lvl[1]]
        if not tier:
            return None, 'no %s at level %s' % (n, lvl)
        # Several ids at this level: the _ii / _iii names are the afterglow (upgraded) forms of the
        # same weapon, so prefer the plain one (ochain_99 11926, not ochain_99_ii 16199).
        plain = [i for i in tier if not re.search(r'_i{2,3}$', basic[i][0])]
        tier = plain or tier
        if len(tier) > 1:
            lowest = min(cands, key=lambda i: (equip[i]['level'], equip[i]['ilevel'], i))
            same = [i for i in tier if equip[i]['mid'] == equip[lowest]['mid']]
            tier = same or tier
            if len(tier) > 1 and lowest not in tier:
                tier = sorted(tier, key=lambda i: abs(i - lowest))[:1]
        cands = tier
    return min(cands), None


def build_gear(pages, sqldir, out):
    basic, equip = lsb_items(sqldir)
    rows, misses = [], []
    for path, phrase, display, lvl, hows in GEAR:
        pg = pages.get(path)
        text = ' '.join(t for _, t in pg['blocks']) + ' ' + pg.get('excerpt', '') if pg else ''
        if phrase not in text:
            misses.append('%s: "%s" not on %s' % (display, phrase, path))
            continue
        iid, why = find_item(display, lvl, basic, equip)
        if iid is None:
            misses.append('%s: %s' % (display, why))
            continue
        e, f = equip[iid], basic[iid][2]
        rare, ex = 'FLAG_RARE' in f, 'FLAG_EX' in f
        if f.strip().isdigit():
            rare, ex = bool(int(f) & 0x8000), bool(int(f) & 0x4000)
        slot = next((nm for b, nm in SLOTS if e['slot'] & b), None)
        hs = [list(h[:2]) + [h[2], h[3]] for h in hows]
        hs = [(k, '%s. Source: %s' % (t, HOST + path), z, npc) for k, t, z, npc in hs]
        rows.append((display, iid, e['level'], slot, jobs_text(e['jobs']), rare, ex, hs))
    rows.sort(key=lambda r: r[0].lower())
    L = [header('gear_guide.lua', ['Only items a page names together with how to get them; item ids, level, slot, jobs',
                                   'and Rare/Ex are looked up in LandSandBoat sql/item_basic.sql + item_equipment.sql.',
                                   'how = { kind, text, zone id or nil, npc or nil }']),
         'local G = {}', '', 'G.categories = {',
         "    { id = 'custom', name = 'DriftwoodXI Shops', desc = %s, count = %d }," % (
             lua_str('Sold for Drift Coins on the Drift Board (/quests) shelves: the ArmsDealer, Jeweler and Artisan tabs.'),
             len(rows)),
         '}', '', 'G.items = {']
    for d, iid, lv, slot, jobs, rare, ex, hs in rows:
        how = ', '.join('{ %s, %s, %s, %s }' % (lua_str(k), lua_str(t), 'nil' if z is None else z,
                                               'nil' if n is None else lua_str(n)) for k, t, z, n in hs)
        L.append("    { id = %d, name = %s, level = %d, slot = %s, jobs = %s, rare = %s, ex = %s, cats = 'custom', how = { %s } },"
                 % (iid, lua_str(d), lv, lua_str(slot or ''), lua_str(jobs), str(rare).lower(), str(ex).lower(), how))
    L += ['}', '', 'return G', '']
    with open(os.path.join(out, 'gear_guide.lua'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L))
    return len(rows), misses


# ---------------------------------------------------------------- convert: main

SQLDIR = '/Volumes/Games/FFXI/lsb/server/sql'


def convert(raw, out):
    pages = load_pages(raw)
    os.makedirs(out, exist_ok=True)
    guides = []
    bytopic = {}
    special = {'/custom', '/commands', '/addons'}
    for path, pg in pages.items():
        if path in special:
            continue
        bytopic.setdefault(topic_of(path), []).append(pg)

    gear_n, misses = 0, []
    if os.path.isdir(SQLDIR):
        gear_n, misses = build_gear(pages, SQLDIR, out)
    else:
        misses = ['LSB sql dir %s not mounted: gear_guide.lua not written' % SQLDIR]

    skipped = []
    sk = os.path.join(raw, 'skipped.txt')
    if os.path.exists(sk):
        skipped = [s for s in open(sk).read().split() if s]
    site = os.path.join(raw, 'site')
    n_files = sum(1 for f in os.listdir(site) if f.endswith('.html'))
    n_feat = sum(1 for p in pages if p.startswith('/features/'))
    n_news = sum(1 for p in pages if p.startswith('/news/'))
    about = dict(name='About this data', group='Server',
                 desc='What this DriftwoodXI data is built from and what it leaves out. Source: %s/robots.txt, '
                      '%s/custom, %s/features, %s/news, %s/commands, %s/addons, '
                      'https://github.com/DriftwoodGaming/DriftwoodXI-Content' % ((HOST,) * 6),
                 steps=[
                     dict(title='What was fetched', note=note([
                         '%d pages of %s fetched on %s: the home page, /custom, /commands, /addons, /download, '
                         '/download/linux, the /features index and %d add-on pages, the /news index and %d news posts. '
                         'The home page and the two indexes are not used (live player counts; the indexes only repeat '
                         'the posts\' summaries), so %d pages are excerpted here.'
                         % (n_files, HOST, FETCHED, n_feat, n_news, len(pages)),
                         'From GitHub DriftwoodGaming/DriftwoodXI-Content: README.md, content.json (the launcher\'s '
                         'add-on feed) and ashita.json. The add-on zip packages were not downloaded.',
                         'The site has no sitemap.xml; pages were found from its navigation links.',
                         'robots.txt: User-agent * may not fetch /reset or /delete; nothing else is disallowed and no '
                         'Crawl-delay is set. Those two paths, /register and every account page were never requested%s.'
                         % ((' (also skipped: %s)' % ', '.join(skipped)) if skipped else ''),
                     ])),
                     dict(title='How it is written', note=note([
                         'Each bullet is an excerpt of the page named in its guide\'s Source list: lists, table rows and '
                         'command entries kept, paragraphs cut to their first whole sentences (never mid-sentence).',
                         'Each page is filed under one topic. News posts are dated; a later post can change what an '
                         'earlier one says, so read the newest first when they disagree.',
                         'The Gear tab lists %d items the pages name with a price or a way to get them; their ids, '
                         'levels and jobs come from standard LandSandBoat data.' % gear_n,
                     ])),
                     dict(title='Not covered', note=note([
                         'No per-quest walkthroughs, drop tables, crafting recipes or mob data: the site does not '
                         'publish them, so the Quests, Skills and other tabs use standard LandSandBoat data.',
                         'Set pieces the pages describe only by family (Outfitter artifact sets, Driftmark Karieyh, '
                         'Orvail and Thurandaut sets, Mythic weapons and the Empyreans not named) are not in the Gear tab.',
                         'The home page (live player counts) and the Discord server were not used.',
                         'Source text is (c) DriftwoodXI; no open licence is stated.',
                     ])),
                 ])
    guides.append(about)
    if '/custom' in pages:
        guides.append(whole_page_guide(pages['/custom'], 'What is custom here',
                                       'The site\'s own overview of everything that differs from retail.', cap=14))
    order = [t for t, _ in TOPICS] + ['Other news']
    for topic in order:
        pgs = bytopic.get(topic)
        if not pgs and topic != 'Commands':
            continue
        if topic == 'Commands':
            if '/commands' in pages:
                guides.append(whole_page_guide(pages['/commands'], 'Commands',
                                               'Every typed command and add-on window, by group.', entry_len=700, cap=60))
            if not pgs:
                continue
            topic = 'Commands: news'
        if topic == 'Add-ons and the allowed list' and '/addons' in pages:
            pgs = [pages['/addons']] + pgs
        feats = sorted([p for p in pgs if not p.get('date')], key=lambda p: p['path'])
        news = sorted([p for p in pgs if p.get('date')], key=lambda p: p['date'], reverse=True)
        steps = []
        for pg in feats + news:
            if pg['path'] == '/addons':
                steps += whole_page_guide(pg, '', '', cap=40)['steps']
            else:
                steps += page_steps(pg)
        guides.append(dict(name=topic, group='Server',
                           desc='%d page%s, add-on pages first, then news newest first. News bullets are kept as '
                                'posted: a later post can change what an earlier one says, so the newest one wins. '
                                'Source: %s' % (
                               len(feats + news), '' if len(feats + news) == 1 else 's',
                               ', '.join(p['url'] for p in feats + news)),
                           steps=steps))
    gh = github_guide(raw)
    if gh:
        guides.append(gh)
    write_guides(os.path.join(out, 'server_notes.lua'), 'server_notes.lua', guides)
    print('server_notes.lua: %d guides, %d steps' % (len(guides), sum(len(g['steps']) for g in guides)))
    print('gear_guide.lua: %d items' % gear_n)
    for m in misses:
        print('  gear miss: ' + m)


if __name__ == '__main__':
    main()
