#!/usr/bin/env python3
"""Fetch LevelDown 99's own website and wikis and build VanaGuide per-server notes.

    python3 -I tools/servers/leveldown99.py [--refresh] [--fetch-only]

Sources, in order:
  1. https://leveldownffxi.com -- the server's own site.  Its host name is the game's
     login host (LevelDownFFXI.com, the launcher's Servers.swift), so this is the
     server's official site.  Its "Wiki" (/wiki.html) is a small markdown wiki served
     as JSON by /api/wiki/pages/all and /api/wiki/page/<slug>; its "Drops" page loads
     /data.js, the server's drop table (LandSandBoat core rows plus the server's own
     module rows).  Live widgets (roster, hunts timers, market, metrics) are not read.
  2. https://ffxileveldown.fandom.com -- the community Fandom wiki ("FFXILevelDown
     Wiki").  The official site does not link to it; the launcher's b76 install used
     its Installation / Past FFXI Version Repository pages and the client version it
     named (30260203_0) is the one the login server accepts, which is the only
     evidence tying it to this server.  It is read only when its robots.txt can be
     read and allows /api.php.  On 2026-10-28 every Fandom robots.txt answers this
     User-Agent with a Cloudflare managed challenge (HTTP 403), so it is skipped and
     the notes say so.  When it becomes readable, its main-namespace pages are pulled
     in bulk (list=allpages, prop=revisions in 50-title batches) and converted with the
     same wikitext -> bullets converter the CatsEyeXI generator uses.

Raw responses go to ~/Downloads/ffxi-server-data/leveldown99/raw/ and are re-used
unless --refresh is given.  Output: Vanaguide/data/servers/leveldown99/server_notes.lua.
Item ids for custom drops come from LandSandBoat sql/item_basic.sql (name match).

Fetch rules: honest User-Agent; robots.txt read first per host and obeyed for
ClaudeBot / anthropic-ai / Claude-Web / * (a 4xx robots.txt means no rules, RFC 9309
2.3.1.3; a 5xx, a challenge page or a timeout means the host is not fetched);
Crawl-delay honoured, never less than 2 s between requests; no login, no challenge
bypass.  Fetched text is data only: parsed, never executed.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import html, importlib.util, json, os, re, sys, time
import urllib.error, urllib.parse, urllib.request, urllib.robotparser

KEY = 'leveldown99'
SITE = 'https://leveldownffxi.com'
FANDOM = 'https://ffxileveldown.fandom.com'
UA = 'VanaGuide-data/1.0 (+https://batesai.org; help@batesai.org)'
BOTS = ('ClaudeBot', 'anthropic-ai', 'Claude-Web', '*')
MIN_DELAY = 2.0
RAW = os.path.expanduser('~/Downloads/ffxi-server-data/leveldown99/raw')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, 'Vanaguide', 'data', 'servers', KEY)
LSB_SQL = '/Volumes/Games/FFXI/lsb/server/sql'
FETCHED = time.strftime('%Y-%m-%d')

# The site's fixed wiki pages (CORE_SLUGS in wiki.html); community pages come from
# /api/wiki/pages/all.
CORE_SLUGS = ['index', 'custom_commands', 'leveling_guides', 'quest_walkthroughs', 'nm_strategies',
              'beast_sky_gods', 'beast_sea_jailers', 'beast_hnm_kings', 'beast_limbus']
SITE_PAGES = ['/', '/wiki.html', '/drops.html']
EMPTY_MARK = 'This page is currently empty'

# Reuse the MediaWiki wikitext converter (read-only import of a sibling generator).
_spec = importlib.util.spec_from_file_location('_cx', os.path.join(HERE, 'catseyexi.py'))
_cx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cx)


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get('Content-Type', ''), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type', ''), e.read()
    except (urllib.error.URLError, OSError) as e:
        return 0, '', str(e).encode()


class Host:
    """One host: robots.txt first, then polite cached fetches."""

    def __init__(self, base, tag, refresh):
        self.base, self.tag, self.refresh = base, tag, refresh
        self.rp, self.delay, self.last, self.status = None, MIN_DELAY, 0.0, ''
        rpath = os.path.join(RAW, tag + '_robots.txt')
        spath = os.path.join(RAW, tag + '_robots.status')
        if refresh or not os.path.exists(spath):
            code, ctype, body = get(base + '/robots.txt', 30)
            self.last = time.time()
            if code == 200 and 'text/plain' in ctype and b'Just a moment' not in body:
                open(rpath, 'wb').write(body)
                st = 'ok'
            elif 400 <= code < 500 and b'Just a moment' not in body and 'challenge' not in body[:4000].decode('latin-1').lower():
                st = 'none %d' % code          # no robots.txt: no rules
            else:
                open(os.path.join(RAW, '%s_robots.blocked-%d.html' % (tag, code)), 'wb').write(body)
                st = 'blocked %d %s' % (code, ctype.split(';')[0] or 'no response')
            open(spath, 'w').write(st)
        self.status = open(spath).read().strip()
        if self.status == 'ok':
            self.rp = urllib.robotparser.RobotFileParser()
            self.rp.parse(open(rpath, encoding='utf-8', errors='replace').read().splitlines())
            self.delay = max(MIN_DELAY, float(self.rp.crawl_delay('*') or 0))

    @property
    def usable(self):
        return self.status == 'ok' or self.status.startswith('none')

    def allowed(self, url):
        if not self.usable:
            return False
        return self.rp is None or all(self.rp.can_fetch(b, url) for b in BOTS)

    def fetch(self, url, name):
        path = os.path.join(RAW, name)
        if not self.refresh and os.path.exists(path):
            return open(path, 'rb').read()
        if not self.allowed(url):
            print('not fetched (robots/host):', url)
            return None
        wait = self.last + self.delay - time.time()
        if wait > 0:
            time.sleep(wait)
        code, ctype, body = get(url)
        self.last = time.time()
        print('fetch', code, url, len(body))
        if code != 200:
            return None
        open(path, 'wb').write(body)
        return body


def fetch(refresh):
    os.makedirs(RAW, exist_ok=True)
    site = Host(SITE, 'site', refresh)
    print('site robots:', site.status)
    if site.usable:
        for p in SITE_PAGES:
            site.fetch(SITE + p, 'site_' + (p.strip('/').replace('/', '__') or 'index.html'))
        lst = site.fetch(SITE + '/api/wiki/pages/all', 'wiki_pages_all.json')
        slugs = list(CORE_SLUGS)
        if lst:
            slugs += [p['slug'] for p in json.loads(lst) if p.get('slug') and p['slug'] not in slugs]
        for s in slugs:
            if re.fullmatch(r'[a-z0-9_-]+', s):
                site.fetch(SITE + '/api/wiki/page/' + s, 'wiki_page_%s.json' % s)
        site.fetch(SITE + '/data.js', 'site_data.js')
    fan = Host(FANDOM, 'fandom', refresh)
    print('fandom robots:', fan.status)
    if fan.usable and fan.allowed(FANDOM + '/api.php'):
        def api(params):
            return FANDOM + '/api.php?' + urllib.parse.urlencode(dict(params, format='json'))
        fan.fetch(api({'action': 'query', 'meta': 'siteinfo', 'siprop': 'general|rightsinfo'}),
                  'fandom_siteinfo.json')
        body = fan.fetch(api({'action': 'query', 'list': 'allpages', 'apnamespace': 0,
                              'apfilterredir': 'nonredirects', 'aplimit': 500}), 'fandom_allpages.json')
        titles = [p['title'] for p in json.loads(body)['query']['allpages']] if body else []
        for i in range(0, len(titles), 50):
            fan.fetch(api({'action': 'query', 'prop': 'revisions', 'rvprop': 'content|timestamp',
                           'rvslots': 'main', 'formatversion': 2, 'titles': '|'.join(titles[i:i + 50])}),
                      'fandom_pages_%d.json' % (i // 50))
    return site.status, fan.status


# ---------------------------------------------------------------- helpers

lua = _cx.lua


def raw(name):
    p = os.path.join(RAW, name)
    return open(p, 'rb').read() if os.path.exists(p) else None


def text_of_html(b):
    t = b.decode('utf-8', 'replace')
    t = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', t)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t))).strip()


def md_bullets(md):
    """Markdown page body -> (depth, text) bullets, one per non-empty line."""
    out = []
    for ln in md.replace('\r', '').split('\n'):
        s = ln.rstrip()
        if not s.strip():
            continue
        m = re.match(r'^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$', s)
        depth = 1 + (len(m.group(1)) // 2 if m else 0)
        body = (m.group(2) if m else s).strip()
        body = re.sub(r'^#+\s*', '', body)
        body = re.sub(r'\*\*(.+?)\*\*|__(.+?)__', lambda x: x.group(1) or x.group(2), body)
        body = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', body)
        # strip real HTML tags only; FFXI text uses <pos>, <t>, <me> literally
        body = re.sub(r'</?(?:br|p|div|span|b|i|u|em|strong|code|small|font|a)\b[^>]*>', '', body, flags=re.I).strip()
        if body:
            out.append((min(depth, 2), body))
    return out


def note(bullets):
    return '\n'.join(('• ' if d <= 1 else '    ◦ ') + b for d, b in bullets)


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def item_index():
    """normalised name -> set(ids), from both name columns of item_basic.sql."""
    idx = {}
    fn = os.path.join(LSB_SQL, 'item_basic.sql')
    rx = re.compile(r"INSERT INTO `item_basic` VALUES \((\d+),\d+,'((?:[^'\\]|\\.)*)','((?:[^'\\]|\\.)*)',")
    for line in open(fn, encoding='utf-8', errors='replace'):
        m = rx.match(line)
        if m:
            for col in (m.group(2), m.group(3)):
                idx.setdefault(norm(col.replace("\\'", '')), set()).add(int(m.group(1)))
    return idx


def title_case(s):
    small = {'of', 'the', 'a', 'an', 'and', 'in', 'on'}
    w = s.lower().split()
    return ' '.join(x if (i and x in small) else x[:1].upper() + x[1:] for i, x in enumerate(w))


# ---------------------------------------------------------------- guides

def site_guides():
    guides, used = [], []
    # Commands and any other filled-in pages of the site's own wiki.
    pages = []
    for fn in sorted(os.listdir(RAW)):
        m = re.fullmatch(r'wiki_page_(.+)\.json', fn)
        if m:
            d = json.loads(raw(fn))
            pages.append((m.group(1), d))
    empty = []
    for slug, d in sorted(pages, key=lambda x: (x[0] != 'custom_commands', x[0])):
        content = (d.get('content') or '').strip()
        if not content or content.startswith(EMPTY_MARK):
            empty.append(d.get('title') or slug)
            continue
        url = SITE + '/api/wiki/page/' + slug
        used.append(url)
        stamp = ' Last edited by %s on %s.' % (d.get('updated_by', '?'), d['last_update']) if d.get('last_update') else ''
        if slug == 'custom_commands':
            cmds, other = [], []
            for depth, b in md_bullets(content):
                m = re.match(r'^(![a-z0-9]+(?:\s+#)?)\s+-\s+(.*)$', b, re.I)
                if m:
                    cmds.append((1, '%s: %s' % (m.group(1), m.group(2).strip())))
                elif cmds:
                    cmds.append((2, b))
                else:
                    other.append((1, b))
            travel = [c for c in cmds if c[1].split(':')[0] in
                      ('!dem', '!mea', '!holla', '!vahzl', '!yhoator', '!home', '!homereturn', '!hangout', '!addallportals')]
            rest = [c for c in cmds if c not in travel]
            steps = []
            if other:
                steps.append(('Notes', note(other)))
            # keep sub-bullets with their command
            def grouped(sel):
                out, keep = [], False
                for c in cmds:
                    if c[0] == 1:
                        keep = c in sel
                    if keep:
                        out.append(c)
                return out
            steps.append(('Travel and teleports', note(grouped(travel))))
            steps.append(('Experience, jobs and fixes', note(grouped(rest))))
            guides.append({'name': 'Commands', 'group': 'Server',
                           'desc': 'Custom ! commands, from the server\'s own wiki (Custom Commands page).%s Source: %s/wiki.html (%s)' % (stamp, SITE, url),
                           'steps': steps})
        else:
            guides.append({'name': (d.get('title') or slug).title(), 'group': 'Wiki',
                           'desc': 'From the server\'s own wiki.%s Source: %s' % (stamp, url),
                           'steps': [('Page', note(md_bullets(content)[:40]))]})
    return guides, used, empty


def drop_guide():
    body = raw('site_data.js')
    if not body:
        return None, {}
    t = body.decode('utf-8', 'replace')
    rows = json.loads(t[t.index('['):t.rindex(']') + 1])
    counts = {}
    for r in rows:
        counts[r.get('type')] = counts.get(r.get('type'), 0) + 1
    mods = [r for r in rows if str(r.get('type', '')).lower() in ('module', 'coffer')]
    idx = item_index()
    order, by_src = [], {}
    for r in mods:
        src = r['source'].strip()
        if src not in by_src:
            by_src[src] = []
            order.append(src)
        if r['itemName'] not in [x['itemName'] for x in by_src[src]]:
            by_src[src].append(r)
    steps, matched, unmatched = [], 0, []
    for src in order:
        bl = []
        for r in by_src[src]:
            name = title_case(r['itemName'])
            ids = sorted(idx.get(norm(r['itemName'].replace("'", '')), ()))
            if str(r.get('itemId', '')).isdigit():
                ids = [int(r['itemId'])]
            rate = r.get('rate') or '?'
            if len(ids) == 1:
                matched += 1
                bl.append((1, '%s (item %d), rate: %s' % (name, ids[0], rate)))
            else:
                unmatched.append(r['itemName'])
                why = 'no LandSandBoat item has this name' if not ids else 'name matches items %s' % ', '.join(map(str, ids))
                bl.append((1, '%s (as spelled on the site; %s), rate: %s' % (name, why, rate)))
        zone = by_src[src][0].get('zone') or ''
        steps.append(('%s%s' % (src, ' (%s)' % zone if zone else ''), note(bl)))
    stats = {'rows': len(rows), 'counts': counts, 'module_rows': len(mods), 'matched': matched,
             'unmatched': unmatched}
    g = {'name': 'Custom battlefield rewards', 'group': 'Gear',
         'desc': 'Rewards from LevelDown\'s own server modules (the "Modules (Custom Addons)" rows of the site\'s drop table; duplicate rows merged). '
                 'The site gives every rate as "Varies". Item ids are matched by name against LandSandBoat item_basic.sql. Source: %s/drops.html (%s/data.js)' % (SITE, SITE),
         'steps': steps}
    return g, stats


def fandom_guides():
    pages = {}
    for fn in sorted(os.listdir(RAW)):
        if re.fullmatch(r'fandom_pages_\d+\.json', fn):
            for pg in json.loads(raw(fn))['query']['pages']:
                if pg.get('missing') or not pg.get('revisions'):
                    continue
                rev = pg['revisions'][0]
                pages[pg['title']] = rev['slots']['main']['content']
    guides = []
    for title in sorted(pages):
        steps = []
        for path, bullets in _cx.sections(pages[title]):
            head = ' › '.join(p[1] for p in path if p[1]) or 'Overview'
            steps.append((head, note(bullets[:40])))
        if steps:
            url = FANDOM + '/wiki/' + urllib.parse.quote(title.replace(' ', '_'))
            guides.append({'name': title, 'group': 'Fandom wiki',
                           'desc': 'From the FFXILevelDown Fandom wiki. Source: ' + url, 'steps': steps})
    lic = ''
    si = raw('fandom_siteinfo.json')
    if si:
        ri = json.loads(si).get('query', {}).get('rightsinfo', {})
        lic = ('%s %s' % (ri.get('text', ''), ri.get('url', ''))).strip()
    return guides, lic


def write(guides, header):
    lines = ['-- Vanaguide :: data/servers/%s/server_notes.lua' % KEY,
             '-- GENERATED by tools/servers/%s.py from %s (fetched %s).  Do not hand-edit.' % (KEY, SITE, FETCHED)]
    lines += ['-- ' + h for h in header]
    lines += ['--', '-- Copyright (c) 2026 Bates LLC.  All rights reserved.', '', 'local S = {}', '', 'S.guides = {']
    for g in guides:
        lines.append('    { name = %s, group = %s, desc = %s, steps = {' % (lua(g['name']), lua(g['group']), lua(g['desc'])))
        for t, n in g['steps']:
            lines.append('            { title = %s, note = %s },' % (lua(t), lua(n)))
        lines.append('    } },')
    lines += ['}', '', 'return S', '']
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'server_notes.lua')
    open(path, 'w', encoding='utf-8').write('\n'.join(lines))
    print('wrote', path, len(guides), 'guides')


def build(site_status, fan_status):
    home = raw('site_index.html')
    if not home:
        print('STOP: the official site was not fetched (robots: %s). Nothing written.' % site_status)
        return 2
    htxt = text_of_html(home)
    facts = []
    for ev in ('A Retail-Progressive Vana\'diel Sandbox',
               'Operating on robust LandSandBoat database tables'):
        if ev not in htxt:
            print('STOP: home page no longer says %r; review the notes.' % ev)
            return 5
    facts.append((1, 'The site describes the server as "A Retail-Progressive Vana\'diel Sandbox" running on LandSandBoat database tables.'))
    sg, used, empty = site_guides()
    dg, st = drop_guide()
    fg, flic = fandom_guides()
    fetched = [(1, 'Official site %s (its host is the game login host LevelDownFFXI.com), fetched %s. robots.txt: %s.' %
                (SITE, FETCHED, 'none (HTTP 404), so no rules' if site_status.startswith('none') else site_status)),
               (1, 'Site wiki: %d pages read through /api/wiki/page/<slug>; with text: %d (%s); still the empty placeholder: %d (%s).' %
                (len(used) + len(empty), len(used), ', '.join(u.rsplit('/', 1)[1] for u in used) or 'none',
                 len(empty), ', '.join(empty)))]
    if st:
        fetched.append((1, 'Drop table /data.js: %d rows (%s); %d are the server\'s own module rows, summarised under Custom battlefield rewards.' %
                       (st['rows'], ', '.join('%s %d' % kv for kv in sorted(st['counts'].items())), st['module_rows'])))
    if fg:
        fetched.append((1, 'Fandom wiki %s: %d main-namespace pages.' % (FANDOM, len(fg))))
    notcov = []
    if not fg:
        notcov.append((1, 'The FFXILevelDown Fandom wiki (%s) was not read: its robots.txt could not be read (%s; a Cloudflare challenge page), and this tool does not get around challenges. '
                          'Its pages (About Us, Custom Content, Custom Quests, Item Adjustments, Paragon Level, Progression Guide, Mythic Weapons and others) are therefore not in these notes. The official site does not link to it.' % (FANDOM, fan_status)))
    notcov += [(1, 'Retail (LandSandBoat core) monster and battlefield drops in /data.js are not repeated here; Gear falls back to standard LandSandBoat data.'),
               (1, 'Live pages (roster, NM hunt timers, market, metrics) and the Discord are not read.'),
               (1, 'The site publishes no EXP rate, level-cap table, quest walkthroughs or crafting data; its Leveling, Quest and Beast pages are empty placeholders.')]
    if st and st['unmatched']:
        notcov.append((1, 'Reward names with no matching LandSandBoat item (no item id given): %d, namely %s.' %
                       (len(set(st['unmatched'])), ', '.join(sorted(set(title_case(u) for u in st['unmatched']))))))
    lic = [(1, 'The site states no copyright or licence. These notes are short factual summaries with source links.')]
    if fg:
        lic.append((1, 'Fandom wiki text: %s.' % (flic or 'licence not stated in siteinfo')))
    about = {'name': 'About this data', 'group': 'Server',
             'desc': 'What this LevelDown 99 data is built from and what it leaves out. Source: %s/ %s/wiki.html %s/drops.html' % (SITE, SITE, SITE),
             'steps': [('What was fetched', note(fetched)), ('The server', note(facts)),
                       ('Not covered', note(notcov)), ('Licence', note(lic))]}
    guides = [about] + sg + ([dg] if dg else []) + fg
    header = ['Official site text has no stated licence; summaries with source URLs.']
    if fg:
        header.append('Fandom wiki text: %s; adaptation shared under the same terms.' % (flic or 'see the wiki'))
    write(guides, header)
    return 0


def main():
    refresh = '--refresh' in sys.argv
    site_status, fan_status = fetch(refresh)
    if '--fetch-only' in sys.argv:
        return 0
    return build(site_status, fan_status)


if __name__ == '__main__':
    sys.exit(main())
