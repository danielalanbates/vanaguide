#!/usr/bin/env python3
"""Fetch CatsEyeXI pages from BG-Wiki and build VanaGuide per-server notes and quest guides.

    python3 -I tools/servers/catseyexi.py [--refresh] [--fetch-only]

Source: BG-Wiki (https://www.bg-wiki.com), the CatsEyeXI pages in the main namespace
("CatsEyeXI Systems/...", "CatsEyeXI Content/...", ...).  catseyexi.com itself was
checked: its robots.txt disallows /api/ (not fetched); its /wiki path is fetched once
only to record what it is.

Bulk first: the page list comes from api.php list=allpages / list=search, and page text
from api.php prop=revisions in a few multi-title requests (not page by page).  Raw
responses go to ~/Downloads/ffxi-server-data/catseyexi/raw/ and are re-used unless
--refresh is given.

Output (Vanaguide/data/servers/catseyexi/):
    server_notes.lua   one guide per topic, every bullet taken from a fetched wiki page
    quest_guides.lua   CatsEyeXI custom quests documented on "CatsEyeXI Systems/Quests"
gear_guide.lua and skill_guides.lua in that folder are generated from the server's
public code by tools/gen_gear_guide.py / gen_skill_guides.py and are NOT touched here.

Fetch rules: honest User-Agent; robots.txt read first and obeyed for ClaudeBot /
anthropic-ai / Claude-Web / *; BG-Wiki's Crawl-Delay (30 s) honoured between every
request to that host; no login, no challenge bypass.  Fetched text is data only: it is
parsed, never executed.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import html, json, os, re, sys, time
import urllib.error, urllib.parse, urllib.request, urllib.robotparser

KEY = 'catseyexi'
WIKI = 'https://www.bg-wiki.com'
SITE = 'https://catseyexi.com'
UA = 'VanaGuide-data/1.0 (+https://batesai.org; help@batesai.org)'
BOTS = ('ClaudeBot', 'anthropic-ai', 'Claude-Web', '*')
RAW = os.path.expanduser('~/Downloads/ffxi-server-data/catseyexi/raw')
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, 'Vanaguide', 'data', 'servers', KEY)
FETCHED = '2026-10-28'

# Pages whose text is fetched, in request batches (prop=revisions accepts many titles).
# Chosen for server notes (rates, systems, travel, commands, crafting, fishing, jobs,
# drops) and quests.  Left out on purpose: the per-slot equipment lists, Crystal Warrior
# / Wings Era sub-modes, endgame event pages (Abyssea, Dynamis, Sky, Sea, Ventures...),
# NPC directory and weaponskill tables: large, and not what the notes tab is for.
BATCHES = [
    ['CatsEyeXI Systems', 'CatsEyeXI Content', 'CatsEyeXI/New Player Guide', 'CatsEyeXI Commands',
     'CatsEyeXI Systems/Navigation', 'CatsEyeXI Content/EXP', 'CatsEyeXI Content/Accelerated',
     'CatsEyeXI Systems/Treasure Caskets', 'CatsEyeXI Systems/Login Campaigns',
     'CatsEyeXI Systems/Digging', 'CatsEyeXI Systems/Milestone Rewards',
     'CatsEyeXI Systems/Crafting Rewards', 'CatsEyeXI Systems/Augments',
     'CatsEyeXI Systems/Claim Shield', 'BGWiki:Copyrights', 'BGWiki:General disclaimer'],
    ['CatsEyeXI Systems/Quests', 'CatsEyeXI Content/Missions', 'CatsEyeXI Content/Drops',
     'CatsEyeXI Systems/Loxley Quest System (LQS)', 'CatsEyeXI Systems/Novice Trials',
     'CatsEyeXI Systems/Mog Vault', 'CatsEyeXI Systems/Custom Equipment'],
    ['CatsEyeXI Systems/Synthesis', 'CatseyeXI Crafting Guide', 'CatsEyeXI Systems/Fishing',
     'CatseyeXI/Fishing Guide', 'CatsEyeXI Systems/HELM'],
    ['CatsEyeXI Systems/Jobs', 'CatsEyeXI Systems/Trusts'],
]


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


class Host:
    """One host: robots.txt checked for every path, crawl delay honoured between requests."""

    def __init__(self, base, robots_file, refresh):
        self.base, self.refresh, self.last = base, refresh, 0.0
        path = os.path.join(RAW, robots_file)
        if refresh or not os.path.exists(path):
            st, body = self._get(base + '/robots.txt')
            if st != 200:
                sys.exit('%s/robots.txt -> HTTP %s; stopping' % (base, st))
            open(path, 'wb').write(body)
        self.rp = urllib.robotparser.RobotFileParser()
        self.rp.parse(open(path, encoding='utf-8', errors='replace').read().splitlines())
        self.delay = max([float(self.rp.crawl_delay(b) or 0) for b in BOTS] + [1.0])

    def _get(self, url):
        wait = self.last + getattr(self, 'delay', 1.0) - time.time()
        if wait > 0:
            time.sleep(wait)
        print('GET', url, flush=True)
        r = get(url)
        self.last = time.time()
        return r

    def allowed(self, url):
        return all(self.rp.can_fetch(b, url) for b in BOTS)

    def fetch(self, url, name):
        path = os.path.join(RAW, name)
        if not self.refresh and os.path.exists(path):
            return open(path, 'rb').read()
        if not self.allowed(url):
            print('robots.txt disallows', url, '- not fetched')
            return None
        st, body = self._get(url)
        if st != 200:
            print('HTTP', st, url, '- not saved')
            return None
        open(path, 'wb').write(body)
        return body


def api(params):
    return WIKI + '/api.php?' + urllib.parse.urlencode(dict(params, format='json'))


def fetch(refresh):
    os.makedirs(RAW, exist_ok=True)
    wiki = Host(WIKI, 'bgwiki_robots.txt', refresh)
    print('bg-wiki crawl delay', wiki.delay)
    for pre in ('CatsEyeXI', 'CatseyeXI'):
        # distinct names: the raw dir may sit on a case-insensitive file system
        wiki.fetch(api({'action': 'query', 'list': 'allpages', 'apprefix': pre, 'aplimit': 500}),
                   'allpages_%s.json' % ('a' if pre == 'CatsEyeXI' else 'b'))
    wiki.fetch(api({'action': 'query', 'list': 'search', 'srsearch': 'CatsEyeXI', 'srlimit': 500,
                    'srnamespace': 0, 'srwhat': 'title'}), 'search_catseyexi_ns0.json')
    wiki.fetch(api({'action': 'query', 'meta': 'siteinfo', 'siprop': 'rightsinfo|namespaces'}),
               'siteinfo.json')
    for i, titles in enumerate(BATCHES):
        wiki.fetch(api({'action': 'query', 'prop': 'revisions', 'rvprop': 'content|timestamp',
                        'rvslots': 'main', 'formatversion': 2, 'titles': '|'.join(titles)}),
                   'pages_%d.json' % i)
    site = Host(SITE, 'catseye_robots.txt', refresh)
    site.fetch(SITE + '/wiki', 'catseyexi_com_wiki.html')


def load_pages():
    pages = {}
    for i in range(len(BATCHES)):
        p = os.path.join(RAW, 'pages_%d.json' % i)
        if not os.path.exists(p):
            continue
        for pg in json.load(open(p))['query']['pages']:
            if pg.get('missing') or not pg.get('revisions'):
                continue
            rev = pg['revisions'][0]
            pages[pg['title']] = {'text': rev['slots']['main']['content'], 'ts': rev['timestamp']}
    return pages


# ---------------------------------------------------------------- wikitext -> plain text

def page_url(title):
    return WIKI + '/index.php?title=' + urllib.parse.quote(title.replace(' ', '_'), safe='/():\'')


MODE_ICONS = {'CatsEyeXI ACE.png': 'ACE', 'CatsEyeXI CW.png': 'CW', 'CatsEyeXI WEW.png': 'WEW'}
# Drop-rate templates, named as the CatsEyeXI pages explain them.
DROPS = {'cdrop': 'Common', 'vcdrop': 'Very Common', 'udrop': 'Uncommon', 'rdrop': 'Rare',
         'vrdrop': 'Very Rare', 'srdrop': 'Super Rare', 'urdrop': 'Ultra Rare', 'gdrop': 'Guaranteed'}
ELEMENTS = {'fire', 'ice', 'wind', 'earth', 'lightning', 'thunder', 'water', 'light', 'dark'}
SKILLCHAIN = {'magical', 'blunt', 'slashing', 'piercing', 'scission', 'transfixion', 'impaction',
              'reverberation', 'detonation', 'induration', 'liquefaction', 'compression',
              'distortion', 'fusion', 'fragmentation', 'gravitation', 'darkness'}
SILENT = {'itemicon', 'icon', 'imgpop2', 'private server', 'category', 'merit icon', 'clear',
          'toc', 'notoc'}
WORDS = {'rare': '[Rare]', 'ex': '[Ex]', 'ki': 'Key item', 'aug': '[Augmented]'}
unknown_templates = {}


def split_args(body):
    """Split a template body on top-level '|' (not inside [[ ]] or {{ }})."""
    out, depth, cur, i = [], 0, [], 0
    while i < len(body):
        two = body[i:i + 2]
        if two in ('{{', '[['):
            depth += 1; cur.append(two); i += 2; continue
        if two in ('}}', ']]') and depth:
            depth -= 1; cur.append(two); i += 2; continue
        if body[i] == '|' and depth == 0:
            out.append(''.join(cur)); cur = []; i += 1; continue
        cur.append(body[i]); i += 1
    out.append(''.join(cur))
    name, pos, kw = out[0].strip(), [], {}
    for a in out[1:]:
        m = re.match(r'\s*([A-Za-z][A-Za-z0-9 _]*?)\s*=(.*)$', a, re.S)
        if m:
            kw[m.group(1)] = m.group(2).strip()
        else:
            pos.append(a.strip())
    return name, pos, kw


def custom_equipment_text(kw):
    name = kw.get('Text Name') or kw.get('Item Name') or ''
    bits = [kw.get('Equipment Type', '')]
    if kw.get('Level'):
        bits.append('Lv' + kw['Level'])
    if kw.get('Jobs'):
        bits.append(kw['Jobs'])
    if kw.get('DMG'):
        bits.append('DMG:' + kw['DMG'])
    if kw.get('Delay'):
        bits.append('Delay:' + kw['Delay'])
    for k in sorted(k for k in kw if k.startswith('Row ')):
        if kw[k]:
            bits.append(kw[k])
    if kw.get('Rare') == 'y':
        bits.append('Rare')
    if kw.get('Ex') == 'y':
        bits.append('Ex')
    bits = [b for b in bits if b]
    return '%s (%s)' % (name, ', '.join(bits)) if bits else name


def render_template(body):
    name, pos, kw = split_args(body)
    low = name.lower()
    if low == 'category page header':
        return '\n'.join(v for v in (kw.get('Intro Text', ''), kw.get('Secondary Text', '')) if v)
    if low.startswith('#ifeq:'):
        a = name.split(':', 1)[1].strip()
        b = pos[0] if pos else ''
        return (pos[1] if len(pos) > 1 else '') if a == b else (pos[2] if len(pos) > 2 else '')
    if low.startswith('category') or low.startswith('#') or low in SILENT:
        return ''
    if low in DROPS:
        return '(%s)' % DROPS[low]
    if low in ELEMENTS:
        return name.capitalize()
    if low in SKILLCHAIN:
        return name
    if low in WORDS:
        return WORDS[low]
    if low == 'item tooltip':
        return kw.get('Name') or (pos[0] if pos else '')
    if low == 'tooltip':
        return kw.get('text') or (pos[0] if pos else '')
    if low == 'color':
        return pos[-1] if pos else ''
    if low == 'custom item':
        return kw.get('Text Name') or kw.get('Item Name', '')
    if low == 'custom equipment':
        return custom_equipment_text(kw)
    if low == 'gathering row':
        r = kw.get('Rarity', '').strip()
        r = DROPS.get(r.lower(), r)
        return '\n* ' + kw.get('Item', '') + (' (%s)' % r if r else '')
    if low == 'gathering table':
        return '\n' + (kw.get('Activity', '') + ':\n' if kw.get('Activity') else '') + kw.get('Gathering Row', '') + '\n'
    unknown_templates[name] = unknown_templates.get(name, 0) + 1
    return ''


def render_link(inner):
    parts = inner.split('|')
    target = parts[0].strip()
    if re.match(r'(?i)(file|image|media):', target):
        f = target.split(':', 1)[1].replace('_', ' ').strip()
        return '[%s] ' % MODE_ICONS[f] if f in MODE_ICONS else ''
    if re.match(r'(?i)category:', target) or (re.match(r'(?i):category:', target) and len(parts) == 1):
        return ''
    if len(parts) > 1 and parts[-1].strip():
        return parts[-1].strip()
    t = target.lstrip(':').replace('_', ' ')
    t = re.sub(r'^BGWiki:', '', t)
    return t.replace('#', ' § ')


def expand(text):
    """Links, then templates, innermost first.  Table braces are masked first."""
    text = re.sub(r'(?s)<!--.*?-->', '', text)
    text = re.sub(r'(?s)<nowiki>.*?</nowiki>', '', text)
    text = re.sub(r'(?s)<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', text)
    text = re.sub(r'</?(onlyinclude|includeonly|noinclude)>', '', text)
    text = text.replace('{{{!}}', '{|').replace('{{!}}}', '|}').replace('{{!}}', '|')
    text = re.sub(r'\{\{\{[^{}|]*\|([^{}]*)\}\}\}', r'\1', text)   # {{{param|default}}}
    text = re.sub(r'\{\{\{[^{}|]*\}\}\}', '', text)
    # {{Table Flex |Table 1=... |Table 2=...}} only lays its tables out side by side: unwrap it
    for _, body in reversed(top_templates(text, 'Table Flex')):
        i = text.find('{{' + body + '}}')
        inner = re.sub(r'(?m)^\s*\|\s*Table \d+\s*=', '\n', body[len('Table Flex'):])
        text = text[:i] + inner + text[i + len(body) + 4:]
    text = re.sub(r'\[\[#[^\[\]|]*\|\s*\[(\w+)\]\s*\]\]', r'[\1]', text)   # footnote mark [[#footnote-1 | [2]]]
    text = re.sub(r'(?m)^(\s*)\{\|', '\\1\x01', text)
    text = re.sub(r'(?m)^(\s*)\|\}', '\\1\x02', text)
    for _ in range(40):
        new = re.sub(r'\[\[([^\[\]]*)\]\]', lambda m: render_link(m.group(1)), text)
        new = re.sub(r'\{\{([^{}]*)\}\}', lambda m: render_template(m.group(1)), new)
        if new == text:
            break
        text = new
    text = re.sub(r'\[(?:https?:)?//[^\s\]]+\s+([^\]]+)\]', r'\1', text)
    text = re.sub(r'\[(https?://[^\s\]]+)\]', r'\1', text)
    return text


def inline(s):
    s = re.sub(r'(?i)<br\s*/?>', ' ', s)
    s = re.sub(r'(?i)<hr[^>]*>', ' ', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace("'" * 3, '').replace("'" * 2, '')
    s = html.unescape(s)
    s = re.sub(r'__[A-Z]+__', '', s)
    s = s.replace('\x01', '').replace('\x02', '')
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\s+([,.;:)])', r'\1', s)
    s = s.replace('( ', '(')
    return s


def strip_attr(cell):
    """Drop a leading 'style=... |' cell attribute."""
    m = re.match(r'\s*\|(?!\|)(.*)$', cell, re.S)   # empty attribute: '!| Header'
    if m:
        return m.group(1)
    m = re.match(r'\s*((?:[a-zA-Z-]+\s*=\s*("[^"]*"|\'[^\']*\'|[^\s|]+)\s*)+)\|(?!\|)(.*)$', cell, re.S)
    if m:
        return m.group(3)
    m = re.match(r'\s*style="[^"|]*\|(?!\|)(.*)$', cell, re.S)   # attribute with a missing close quote
    return m.group(1) if m else cell


def cell_text(cell):
    cell = re.sub(r'\n\s*[*#:]+\s*', '; ', cell)
    return inline(cell)


def split_nested(cell):
    """A cell holding a nested table: (own text, [nested row lines]).  Nested rows are
    stored as '\n\x03' + rendered line ('* ...', '** ...'); text after them stays the cell's."""
    parts = cell.split('\n\x03')
    own, sub = parts[0], []
    for p in parts[1:]:
        line, _, more = p.partition('\n')
        sub.append(line)
        if more.strip():
            own += '\n' + more
    return own, sub


def tables_to_rows(lines):
    """Turn masked wikitables into one '*' line per row ("Header: value; ...")."""
    out, stack = [], []
    for ln in lines:
        s = ln.strip()
        if s.startswith('\x01'):
            stack.append({'hdr': [], 'rows': [], 'cur': None})
            continue
        if not stack:
            out.append(ln)
            continue
        t = stack[-1]
        if s.startswith('\x02'):
            stack.pop()
            rest = s[1:].strip()
            if t['cur'] is not None:
                t['rows'].append(t['cur'])
            rendered = []
            rows = t['rows']
            if not stack and len(rows) == 1 and rows[0][0] == 'd' and len(rows[0][1]) == 1:
                # a one-cell layout table: its content is ordinary page text
                out.extend(ln.replace('\x03', '') for ln in rows[0][1][0].split('\n'))
                if rest:
                    out.append(rest)
                continue
            for kind, cells in rows:
                split = [split_nested(x) for x in cells]
                cells = [cell_text(o) for o, _ in split]
                nested = ['*' + ln for _, sub in split for ln in sub]   # one level deeper
                if kind == 'h':
                    if len(cells) == 1 and t['hdr']:
                        rendered.append('*' + cells[0] + ':')   # a section row inside the table
                    else:
                        t['hdr'] = cells
                    rendered.extend(nested)
                    continue
                if not any(cells):
                    rendered.extend(nested)
                    continue
                h = t['hdr']
                if h and len(h) == len(cells):
                    txt = '; '.join('%s: %s' % (a, b) if a else b for a, b in zip(h, cells) if b)
                else:
                    txt = ' — '.join(c for c in cells if c)
                rendered.append('* ' + txt)
                rendered.extend(nested)
            if stack:
                p = stack[-1]
                if p['cur'] is None:
                    p['cur'] = ('d', [''])
                p['cur'][1][-1] += ''.join('\n\x03' + r for r in rendered)
            else:
                out.extend(rendered)
            if rest and not stack:
                out.append(rest)
            elif rest and stack[-1]['cur'] is not None:
                stack[-1]['cur'][1][-1] += ' ' + rest
            continue
        if s.startswith('|+'):
            continue
        if s.startswith('|-'):
            if t['cur'] is not None:
                t['rows'].append(t['cur'])
            t['cur'] = None
            continue
        if s.startswith('!') or s.startswith('|'):
            kind = 'h' if s.startswith('!') else 'd'
            body = s[1:]
            cells = re.split(r'!!|\|\|', body) if kind == 'h' else body.split('||')
            cells = [strip_attr(c) for c in cells]
            if t['cur'] is None or t['cur'][0] != kind:
                if t['cur'] is not None:
                    t['rows'].append(t['cur'])
                t['cur'] = (kind, [])
            t['cur'][1].extend(cells)
            continue
        if t['cur'] is not None and t['cur'][1]:
            t['cur'][1][-1] += '\n' + ln
    return out


def sections(wikitext):
    """[(heading path, [(depth, text), ...])]."""
    lines = tables_to_rows(expand(wikitext).split('\n'))
    secs, path, cur = [], [], []
    for ln in lines:
        s = ln.strip()
        m = re.match(r'^(=+)\s*(.*?)\s*\1\s*$', s)
        if m:
            if cur:
                secs.append((list(path), cur))
            lvl, title = len(m.group(1)), inline(m.group(2))
            path = [p for p in path if p[0] < lvl] + [(lvl, title)]
            cur = []
            continue
        if not s or s.startswith('#REDIRECT'):
            continue
        m = re.match(r'^([*#:;]+)\s*(.*)$', s)
        depth, body = (len(m.group(1)), m.group(2)) if m else (1, s)
        body = inline(body)
        if not body or re.fullmatch(r'[\W_]+', body):
            continue
        cur.append((depth, body))
    if cur:
        secs.append((list(path), cur))
    return secs


def note(bullets):
    return '\n'.join(('• ' if d <= 1 else '    ◦ ') + b for d, b in bullets)


# ---------------------------------------------------------------- outputs

TOPICS = [
    ('Server and game modes', 'What CatsEyeXI changes from retail, and its three game modes (Accelerated, Crystal Warrior, Wings Era Warrior).',
     ['CatsEyeXI Systems', 'CatsEyeXI Content', 'CatsEyeXI Content/Accelerated', 'CatsEyeXI/New Player Guide']),
    ('Rates and progression', 'Experience points, camps, milestone rewards and login campaigns.',
     ['CatsEyeXI Content/EXP', 'CatsEyeXI Systems/Milestone Rewards', 'CatsEyeXI Systems/Login Campaigns']),
    ('Crafting and gathering', 'Custom synthesis recipes and materials, crafting guide, crafting rewards, HELM and digging.',
     ['CatseyeXI Crafting Guide', 'CatsEyeXI Systems/Crafting Rewards', 'CatsEyeXI Systems/Synthesis',
      'CatsEyeXI Systems/HELM', 'CatsEyeXI Systems/Digging']),
    ('Fishing', 'Fishing changes and the fishing levelling guide.',
     ['CatseyeXI/Fishing Guide', 'CatsEyeXI Systems/Fishing']),
    ('Gear and drops', 'Monster drops changed on the server, and augments.',
     ['CatsEyeXI Content/Drops', 'CatsEyeXI Systems/Augments']),
    ('Quests and missions', 'Mission availability, quest notes, the custom quest system and the Novice Trials. Individual custom quests are in quest_guides.lua.',
     ['CatsEyeXI Content/Missions', 'CatsEyeXI Systems/Quests', 'CatsEyeXI Systems/Loxley Quest System (LQS)',
      'CatsEyeXI Systems/Novice Trials']),
    ('Combat and jobs', 'Job adjustments and trusts on CatsEyeXI.',
     ['CatsEyeXI Systems/Jobs', 'CatsEyeXI Systems/Trusts']),
    ('Travel and quality of life', 'Getting around, and the Mog Vault storage system.',
     ['CatsEyeXI Systems/Navigation', 'CatsEyeXI Systems/Mog Vault']),
    ('Commands', 'Custom ! commands typed in /say.', ['CatsEyeXI Commands']),
]
QUESTS = 'CatsEyeXI Systems/Quests'
# Fetched but not written: stub pages that only point elsewhere.
STUBS = ['CatsEyeXI Systems/Claim Shield', 'CatsEyeXI Systems/Treasure Caskets',
         'CatsEyeXI Systems/Custom Equipment']
LICENCE = ['Text adapted from the CatsEyeXI pages of BG-Wiki (www.bg-wiki.com) by its contributors,',
           'licensed CC BY-NC-SA 3.0 (https://creativecommons.org/licenses/by-nc-sa/3.0/); this',
           'adaptation is shared under the same licence.  FINAL FANTASY XI (c) SQUARE ENIX CO., LTD.']


def lua(s):
    return "'" + s.replace('\\', '\\\\').replace("'", "\\'").replace('\r', '').replace('\n', '\\n') + "'"


def short(title):
    t = re.sub(r'^Catse?ye?XI[ /]*', '', title, flags=re.I)
    return t.replace('Systems/', '').replace('Content/', '') or 'Overview'


def topic_steps(pages, titles):
    steps, multi = [], len(titles) > 1
    for t in titles:
        text = pages[t]['text']
        if t == QUESTS:   # the quests themselves go to quest_guides.lua; keep the page's prose
            for _, body in reversed(top_templates(text, 'CatsEyeXI Quests')):
                i = text.find('{{' + body)
                text = text[:i] + text[i + len(body) + 4:]
        for path, bullets in sections(text):
            head = ' › '.join(p[1] for p in path if p[1]) or 'Overview'
            steps.append(((short(t) + ': ' + head) if multi else head, note(bullets)))
    return steps


def write(name, what, guides):
    lines = ['-- Vanaguide :: data/servers/%s/%s' % (KEY, name),
             '-- GENERATED by tools/servers/%s.py from BG-Wiki CatsEyeXI pages (www.bg-wiki.com), fetched %s.  Do not hand-edit.' % (KEY, FETCHED),
             '-- ' + what]
    lines += ['-- ' + h for h in LICENCE]
    lines += ['--', '-- Copyright (c) 2026 Bates LLC.  All rights reserved.', '',
              'local S = {}', '', 'S.guides = {']
    for g in guides:
        lines.append('    { name = %s, group = %s, desc = %s, steps = {' % (lua(g['name']), lua(g['group']), lua(g['desc'])))
        for t, n in g['steps']:
            lines.append('            { title = %s, note = %s },' % (lua(t), lua(n)))
        lines.append('    } },')
    lines += ['}', '', 'return S', '']
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    open(path, 'w', encoding='utf-8').write('\n'.join(lines))
    print('wrote', path, len(guides), 'guides')


def top_templates(text, tname):
    """(offset, body) of every top-level {{tname ...}} in text, brace matched."""
    out, i = [], 0
    while True:
        i = text.find('{{' + tname, i)
        if i < 0:
            return out
        depth, j = 0, i
        while j < len(text):
            if text.startswith('{{', j):
                depth += 1; j += 2; continue
            if text.startswith('}}', j):
                depth -= 1; j += 2
                if depth == 0:
                    break
                continue
            j += 1
        out.append((i, text[i + 2:j - 2]))
        i = j


def lines_of(value):
    return [b for _, bs in sections(value) for b in bs]


def quest_guides(pages):
    text = pages[QUESTS]['text']
    heads = [(m.start(), inline(expand(m.group(2)))) for m in re.finditer(r'(?m)^(==+)\s*(.*?)\s*\1\s*$', text)]
    guides = []
    for pos, body in top_templates(text, 'CatsEyeXI Quests'):
        _, _, kw = split_args(body)
        # 'Windurst Waters{{!}}Windurst Waters (South)': a link target{{!}}label pair:
        # keep the label, as the rendered page shows it
        f = {k: inline(expand(re.sub(r'^[^{}\[\]|]*\{\{!\}\}', '', v.strip())))
             for k, v in kw.items() if k not in ('Requirements', 'Reward', 'Walkthrough')}
        area = ([h for p, h in heads if p < pos] or ['Custom'])[-1]
        modes = [m for m in ('ACE', 'CW', 'WEW') if re.search(r'\|\s*%s\s*=\s*y' % m, body)]
        where = f.get('NPC', '')
        if f.get('Zone'):
            where += (' in ' if where else '') + f['Zone']
        if f.get('Position'):
            where += ' (%s)' % f['Position']
        bits = []
        if where:
            bits.append('Start: ' + where + '.')
        if f.get('Level Requirement'):
            bits.append('Level ' + f['Level Requirement'] + '.')
        if f.get('Job'):
            bits.append('Job: ' + f['Job'] + '.')
        if modes:
            bits.append('Modes: ' + ' '.join(modes) + '.')
        if f.get('Repeatable', '').lower().startswith('y'):
            bits.append('Repeatable' + (' ' + f['Repeat Condition'] if f.get('Repeat Condition') else '') + '.')
        if f.get('Previous Quest'):
            bits.append('After: ' + f['Previous Quest'] + '.')
        if f.get('Next Quest'):
            bits.append('Leads to: ' + f['Next Quest'] + '.')
        bits.append('Source: ' + page_url(QUESTS))
        steps = []
        req = lines_of(kw.get('Requirements', ''))
        if req:
            steps.append(('Requirements', note(req)))
        n = 0
        for d, b in lines_of(kw.get('Walkthrough', '')):
            if d <= 1 or n == 0:
                n += 1
                steps.append(('Step %d' % n, '• ' + b))
            else:
                steps[-1] = (steps[-1][0], steps[-1][1] + '\n    ◦ ' + b)
        rew = lines_of(kw.get('Reward', ''))
        if rew:
            steps.append(('Reward', note(rew)))
        if steps:
            guides.append({'name': f.get('Quest Name') or 'Unnamed quest', 'group': area,
                           'desc': ' '.join(bits), 'steps': steps})
    return guides


def gear_names():
    p = os.path.join(OUT, 'gear_guide.lua')
    if not os.path.exists(p):
        return set()
    src = open(p, encoding='utf-8').read()
    return {m.group(1).replace("\\'", "'").lower() for m in re.finditer(r"name = '((?:[^'\\]|\\.)*)'", src)}


def custom_gear(pages):
    """Custom Equipment shown on fetched pages whose name is not in gear_guide.lua."""
    known, seen, rows, srcs = gear_names(), set(), {}, set()
    for t, pg in pages.items():
        for _, body in top_templates(pg['text'], 'Custom Equipment'):
            _, _, kw = split_args(body)
            kw = {k: inline(expand(v)) for k, v in kw.items()}
            nm = kw.get('Text Name') or kw.get('Item Name')
            if not nm or nm.lower() in known or nm.lower() in seen:
                continue
            seen.add(nm.lower())
            srcs.add(t)
            rows.setdefault(kw.get('Equipment Type') or 'Other', []).append(
                '%s — on %s' % (custom_equipment_text(kw), short(t)))
    steps = [(slot, '\n'.join('• ' + r for r in sorted(v))) for slot, v in sorted(rows.items())]
    return steps, len(seen), sorted(srcs)


def build():
    pages = load_pages()
    used = [t for _, _, ts in TOPICS for t in ts if t in pages]
    guides = []
    for name, blurb, titles in TOPICS:
        titles = [t for t in titles if t in pages]
        if titles:
            guides.append({'name': name, 'group': 'Server', 'steps': topic_steps(pages, titles),
                           'desc': blurb + ' Source: ' + ', '.join(page_url(t) for t in titles)})
    cg_steps, cg_n, cg_src = custom_gear(pages)
    if cg_steps:
        guides.append({'name': 'Custom gear', 'group': 'Server', 'steps': cg_steps,
                       'desc': 'Custom equipment shown on the wiki whose name is not in this server\'s code-generated gear list (%d items): name (slot, level, jobs, stats). Source: %s' % (cg_n, ', '.join(page_url(t) for t in cg_src))})
    about = [
        ('What was fetched', '\n'.join(
            ['• %d BG-Wiki CatsEyeXI pages, fetched %s through the MediaWiki API in a few bulk requests, 30 s apart (BG-Wiki robots.txt Crawl-Delay).' % (len(used), FETCHED)] +
            ['• %s (last edited %s)' % (t, pages[t]['ts'][:10]) for t in used])),
        ('Licence and attribution', '• BG-Wiki states that its content other than Square Enix material is licensed CC BY-NC-SA 3.0 (page BGWiki:Copyrights).\n• These notes are adapted from CatsEyeXI pages written by BG-Wiki contributors and are shared under the same licence, non-commercially, with this attribution.\n• FINAL FANTASY XI (c) SQUARE ENIX CO., LTD.'),
        ('Not covered', '• Not fetched: per-slot equipment lists, Crystal Warrior and Wings Era Warrior pages, endgame pages (Abyssea, Dynamis, Sky, Sea, Ventures, Domain Invasion, HNMs, ZNMs, Dragonslaying and others), the NPC directory, monster list and weaponskill tables.\n• catseyexi.com/wiki is an index that links to BG-Wiki; it was read once.  catseyexi.com /api/ is disallowed by its robots.txt and was not fetched.\n• Fetched but not used, because they only point to other pages: ' + ', '.join(STUBS) + '.\n• Items and skill levelling for this server are in gear_guide.lua and skill_guides.lua, generated from the server\'s public code, not from the wiki.\n• Wiki pages can lag behind the live server; the server\'s patch notes win.'),
    ]
    guides.insert(0, {'name': 'About this data', 'group': 'Server', 'steps': about,
                      'desc': 'What these CatsEyeXI notes were built from, fetched %s. Source: %s/index.php?title=CatsEyeXI, %s/index.php?title=BGWiki:Copyrights, %s/wiki' % (FETCHED, WIKI, WIKI, SITE)})
    write('server_notes.lua', 'Server notes for CatsEyeXI: one guide per topic, every bullet taken from a fetched wiki page.', guides)
    write('quest_guides.lua', 'CatsEyeXI custom quests from the page "CatsEyeXI Systems/Quests": giver, requirements, steps, reward.', quest_guides(pages))
    if unknown_templates:
        top = sorted(unknown_templates.items(), key=lambda kv: -kv[1])[:30]
        print('templates rendered as nothing:', ', '.join('%s x%d' % kv for kv in top))


if __name__ == '__main__':
    refresh = '--refresh' in sys.argv
    fetch(refresh)
    if '--fetch-only' in sys.argv:
        sys.exit(0)
    build()
