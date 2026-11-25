#!/usr/bin/env python3
"""Fetch the MistXI website and build VanaGuide per-server notes.

    python3 -I tools/servers/mistxi.py [--refresh]

Source: https://mistxi.com (static Hugo site; robots.txt allows all agents;
no wiki, no data API).  Raw pages go to ~/Downloads/ffxi-server-data/mistxi/raw/
and are re-used unless --refresh is given.  Output:
Vanaguide/data/servers/mistxi/server_notes.lua (the site has no item, skill or
quest data, so no gear_guide / skill_guides / quest_guides files are written).

Every bullet below carries an evidence string that must appear verbatim in the
text of its fetched page; the build stops if any is missing, so a site change
cannot silently leave a stale claim in the output.  The approved addon/plugin
lists are parsed from the Server Info page itself.

Fetch rules: honest User-Agent, robots.txt read first and obeyed for
ClaudeBot / anthropic-ai / Claude-Web / *, >= 1.2 s between requests, no login,
no challenge bypass.  Fetched HTML is data only: it is parsed, never executed.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import html.parser, os, re, sys, time
import urllib.error, urllib.request, urllib.robotparser

KEY = 'mistxi'
HOST = 'https://mistxi.com'
UA = 'VanaGuide-data/1.0 (+https://batesai.org; help@batesai.org)'
RAW = os.path.expanduser('~/Downloads/ffxi-server-data/mistxi/raw')
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, 'Vanaguide', 'data', 'servers', KEY)
FETCHED = '2026-10-28'

# Server-info, docs, news and feature pages from sitemap.xml.  Left out on
# purpose: privacy/terms (legal), account/portal/password/GM pages (forms),
# auction-house/server-status/gallery (live widgets or images, no text facts),
# tag/category index pages that only repeat post teasers.
PAGES = ['/', '/server-info/', '/getting-started/', '/welcome-to-mistxi/', '/docs/',
         '/docs/commands/', '/docs/new-player-faq/', '/news/',
         '/news/changing-our-focus/', '/news/announcing-the-mistxi-lottery-and-login-campaign/',
         '/news/mistxi-launcher-announcement-/', '/news/introducing-discord-authentication/',
         '/news/new-site-is-live/', '/news/welcome-to-news/', '/tags/features/']


def fname(p):
    return (p.strip('/').replace('/', '__') or 'index').rstrip('-') + '.html'


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.headers.get('Content-Type', ''), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type', ''), e.read()


def fetch(refresh):
    os.makedirs(RAW, exist_ok=True)
    rpath = os.path.join(RAW, 'robots.txt')
    if refresh or not os.path.exists(rpath):
        code, ctype, body = get(HOST + '/robots.txt')
        if code != 200 or 'text/plain' not in ctype:
            print('STOP: robots.txt not readable (HTTP %d, %s). Not bypassing.' % (code, ctype))
            sys.exit(2)
        open(rpath, 'wb').write(body)
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(open(rpath, encoding='utf-8', errors='replace').read().splitlines())
    delay = max(1.2, float(rp.crawl_delay('*') or 0))
    for p in PAGES:
        for agent in ('ClaudeBot', 'anthropic-ai', 'Claude-Web', '*'):
            if not rp.can_fetch(agent, HOST + p):
                print('STOP: robots.txt disallows %s for %s.' % (p, agent))
                sys.exit(3)
        out = os.path.join(RAW, fname(p))
        if os.path.exists(out) and not refresh:
            continue
        time.sleep(delay)
        code, ctype, body = get(HOST + p)
        print('fetch', code, p, len(body))
        if code != 200 or b'Just a moment' in body:
            print('STOP: %s answered HTTP %d. Not bypassing.' % (p, code))
            sys.exit(4)
        open(out, 'wb').write(body)


class Text(html.parser.HTMLParser):
    BLOCK = ('p', 'li', 'h1', 'h2', 'h3', 'h4', 'tr', 'br', 'div', 'td', 'th', 'section')

    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, t, a):
        if t in ('script', 'style', 'noscript'):
            self.skip += 1
        if t in self.BLOCK:
            self.out.append('\n')

    def handle_endtag(self, t):
        if t in ('script', 'style', 'noscript'):
            self.skip -= 1

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d)


def page_text(p):
    t = Text()
    t.feed(open(os.path.join(RAW, fname(p)), encoding='utf-8').read())
    t = re.sub(r'[ \t\xa0]+', ' ', ''.join(t.out))
    return '\n'.join(l.strip() for l in t.split('\n') if l.strip())


def addon_lists(text):
    """Return (addons, plugins) from the Server Info 'Approved Ashita Addons' section."""
    sec = text.split('Approved Ashita Addons & Plugins', 1)[1]
    a = sec.split('\nAddons\n', 1)[1].split('\nPlugins\n', 1)
    addons = [l for l in a[0].split('\n')[1:] if re.fullmatch(r'[A-Za-z0-9_]+\*?', l)]
    plugins = [l for l in a[1].split('If an addon')[0].split('\n')[1:]
               if re.fullmatch(r'[A-Za-z0-9_]+\*?', l)]
    return addons, plugins


def U(p):
    return HOST + p


# (topic, [source pages], [(subtopic, [(bullet, page, evidence), ...]), ...])
# evidence must occur verbatim (after whitespace folding) in that page's text.
SI, GS, NEWS = '/server-info/', '/getting-started/', '/news/'
LOT = '/news/announcing-the-mistxi-lottery-and-login-campaign/'
FOCUS = '/news/changing-our-focus/'
LAUNCH = '/news/mistxi-launcher-announcement-/'
DISC = '/news/introducing-discord-authentication/'
FAQ = '/docs/new-player-faq/'
CMD = '/docs/commands/'
WEL = '/welcome-to-mistxi/'

TOPICS = [
    ('Servers and era', [SI, FOCUS, FAQ, WEL], [
        ('The Mist Cluster', [
            ('Main server: play.mistxi.com, an era-focused module aimed at a more period-correct experience, with carefully chosen QoL tweaks. Level cap 75.', SI, 'Main Server: play.mistxi.com'),
            ('99 Cap server: legacy.mistxi.com, the 99-cap version of MistXI from before the shift to era content. Level cap 99.', SI, '99 Cap Server: legacy.mistxi.com'),
            ('Development / staging server: volatile, may have downtime or data loss; staging environments may wipe, production aims to stay stable.', SI, 'Staging environments may wipe'),
            ('Runs on LandSandBoat emulation software (based on the Darkstar Project).', WEL, 'Running on the LandSandBoat emulation software'),
        ]),
        ('Content scope', [
            ('Content supported up to Wings of the Goddess.', SI, 'Content: Supported up to Wings of the Goddess'),
            ('Some content may be missing or unstable; the site points to the upstream LandSandBoat "What Works" tracker.', SI, 'Some content may be missing or unstable'),
            ('Fields of Valor / Grounds of Valor enabled (FoV + Tomes).', SI, 'Fields of Valor / Grounds of Valor: Enabled (FoV + Tomes)'),
            ('Retail Trust system; FAQ: all trusts that exist in the base emulator are supported.', FAQ, 'All trusts that exist within the base emulator are supported.'),
            ('Dual boxing allowed, maximum 2 per IP.', SI, 'Dual boxing: Allowed (maximum 2 per IP)'),
        ]),
        ('75-era focus (news, Jan 5, 2026)', [
            ('Primary development focus shifted to 75-era gameplay: era-accurate progression and pacing, group-focused content, cooperation and long-term goals.', FOCUS, 'officially shifting our primary development focus to 75-era'),
            ('The level 99 server stays online and playable, supported at a basic level; active development and new features go to the 75-era server.', FOCUS, 'The server will remain accessible and supported at a basic level.'),
        ]),
    ]),
    ('Rates and progression', [SI], [
        ('Rates', [
            ('EXP rate: 3x.', SI, 'EXP rate: 3×'),
            ('Movement speed: 1.5x.', SI, 'Movement speed: 1.5×'),
            ('Weapon and crafting skill-ups increased (no exact rate given).', SI, 'Weapon and crafting skill-ups increased'),
            ('Slightly increased HP/MP multipliers.', SI, 'Slightly increased HP/MP multipliers'),
            ('Multiple EXP rings may be owned.', SI, 'Multiple EXP rings may be owned'),
        ]),
        ('New characters', [
            ('Starting gil: 25,000.', SI, 'Starting gil: 25,000G'),
            ('Starting inventory: 80.', SI, 'Starting inventory: 80'),
            ('New players get the GlobalMist linkshell equipped.', SI, 'Global LS: GlobalMist equipped for new players'),
        ]),
        ('Level cap', [
            ('75 on the main server, 99 on the legacy server.', SI, 'Level cap: 75 (Main) / 99 (Legacy)'),
        ]),
    ]),
    ('Combat and healing', [SI], [
        ('Resting', [
            ('Healing tick frequency doubled.', SI, 'Healing tick frequency doubled'),
            ('TP loss on /heal reduced by 90%.', SI, 'TP loss on heal reduced by 90%'),
            ('Home Points warp and heal.', SI, 'Home Point warping and healing'),
        ]),
    ]),
    ('Travel and quality of life', [SI, LOT], [
        ('Travel', [
            ('Home Point warping enabled.', SI, 'Home Point warping and healing'),
            ('Outpost warps enabled.', SI, 'Outpost warps enabled'),
            ('All maps enabled.', SI, 'All maps enabled'),
            ('!signet grants your nation\'s signet for 2 hours.', LOT, 'Grants the player their nation’s signet for a period of 2 hours.'),
        ]),
    ]),
    ('Slumbering Gods Lottery', [SI, LOT], [
        ('How it works', [
            ('Monthly; one random eligible character wins 1,000,000 gil.', SI, 'Reward: 1,000,000 gil'),
            ('Same character cannot win again within 3 months.', SI, 'Cooldown: The same character cannot win again within 3 months'),
            ('Must have logged in within the last 14 days; GMs excluded.', SI, 'Activity requirement: Must have logged in within the last 14 days'),
            ('Winners announced on Discord; the last 10 winners are listed on the News page.', NEWS, 'The last 10 adventurers blessed by the Slumbering Gods.'),
        ]),
    ]),
    ('Monthly Login Campaign', [SI, LOT], [
        ('Points', [
            ('100 points per day you log in.', SI, 'Points: 100pts per day'),
            ('300-point streak bonus on the 3rd consecutive login day.', SI, 'Bonus: 300pts streak bonus on 3rd consecutive login day'),
            ('Campaign resets on the 1st of every month.', SI, 'Reset: On the 1st of every month, the campaign restarts'),
            ('Redeem at the Greeter Moogle in Port San d\'Oria, Port Bastok or Windurst Walls.', SI, 'Redeem: At the Greeter Moogle in Port San d’Oria, Port Bastok or Windurst Walls'),
        ]),
        ('Reward tiers (rotate occasionally; general schema)', [
            ('10 pt: potions / medicine.', SI, '10pt: Potions/Medicine'),
            ('50 pt: food items.', SI, '50pt: Food Items'),
            ('100 pt: EXP / skill books.', SI, '100pt: EXP/Skill Books'),
            ('300 pt: stacks (12x) of the 50 pt food items.', SI, '300pt: Stacks (12x) of the 50pt tier food items'),
            ('500 pt: furnishings / Mog House items.', SI, '500pt: Furnishings/MH Items'),
            ('750 pt: mounts.', SI, '750pt: Mounts'),
            ('1000 pt: endgame support items (sky god pops, etc.).', SI, '1000pt: Endgame supporting items (sky god pops, etc)'),
            ('1500 pt: endgame / rare gear.', SI, '1500pt: Endgame/rare gear'),
        ]),
    ]),
    ('Economy and policies', [SI], [
        ('Economy', [
            ('During low-activity periods, small controlled systems (the lottery and Auction House automation) keep the economy moving.', SI, 'such as the lottery and Auction House automation'),
            ('No pay-to-win and no hidden monetization; progression is earned by playing.', SI, 'There is no pay-to-win and no hidden monetization.'),
            ('Balance changes are guided by player feedback and visible patch notes.', SI, 'guided by player feedback and visible patch notes'),
        ]),
    ]),
    ('Commands', [CMD, LOT], [
        ('Player commands', [
            ('!help', CMD, '!help'),
            ('!status', CMD, '!status'),
            ('!warp (if enabled)', CMD, '!warp (if enabled)'),
            ('!signet: grants your nation\'s signet for 2 hours.', LOT, '!signet'),
        ]),
    ]),
    ('Setup and accounts', [GS, DISC, LAUNCH], [
        ('Accounts', [
            ('New accounts are created on the website (mistxi.com/create-account) and need Discord verification.', DISC, 'New accounts must be created via Discord authentication'),
            ('Discord is not required to log into the game; existing accounts can optionally be linked.', DISC, 'Discord is not required to log into the game'),
            ('Each Discord account can be linked to only one game account.', DISC, 'Each Discord account can be linked to only one game account'),
        ]),
        ('Client setup', [
            ('The official MistXI Launcher (v1.1.0 announced Feb 1, 2026) is Windows 10/11 64-bit only.', LAUNCH, 'This is v1.1.0'),
            ('Manual Ashita setup: File .\\ffxi-bootmod\\xiloader.exe, Command --server play.mistxi.com, Script default.txt.', GS, 'Command: --server play.mistxi.com'),
            ('PlayOnline file check: choose "For PlayOnline Members" and use ABCD1234 for username, password and account ID.', GS, 'Use ABCD1234 for username, password, and account ID'),
            ('Version mismatch after a server update: delete ROM\\0\\0.dat, then run the PlayOnline file check and repair.', GS, 'Delete \\ROM\\0\\0.dat and run PlayOnline file check'),
            ('Launcher keeps addon picks in mistxi.txt instead of default.txt so Ashita updates do not overwrite them.', LAUNCH, 'saved in mistxi.txt instead of default.txt'),
        ]),
    ]),
]


def check(texts, page, ev):
    if ev not in texts[page]:
        raise SystemExit('EVIDENCE MISSING on %s: %r' % (page, ev))


def lua(s):
    return "'" + s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n') + "'"


def build():
    texts = {p: page_text(p) for p in PAGES}
    guides = []
    fetched = ', '.join(U(p) for p in PAGES)
    about = [
        ('What was fetched', ['• %d pages of %s on %s: home, Server Info, Getting Started, Welcome, Docs (Commands, New Player FAQ) and every News post.' % (len(PAGES), HOST, FETCHED),
                              '• robots.txt allows all agents (User-agent: * / Disallow: empty).',
                              '• Each bullet in these notes is checked against the fetched page text when the file is generated.']),
        ('Not covered', ['• MistXI has no public wiki, item database or data API, so there is no MistXI-specific gear, skill or quest data here; Gear, Skills and Quests fall back to standard LandSandBoat data.',
                         '• Exact skill-up rates, HP/MP multipliers and custom job adjustments are not published on the site.',
                         '• Live pages (Auction House, Server Status, lottery winner table) and the Discord are not read.',
                         '• Notes describe the 75-cap main server unless they say otherwise.']),
        ('Licence', ['• Site text is "© 2026 MistXI. All rights reserved."; no open licence is stated. These notes are short factual summaries with source links, not copies of the pages.']),
    ]
    guides.append(('About this data', 'What this MistXI data is built from and what it leaves out. Source: ' + fetched,
                    [(t, '\n'.join(b)) for t, b in about]))
    for topic, srcs, subs in TOPICS:
        steps = []
        for title, bullets in subs:
            for _, page, ev in bullets:
                check(texts, page, ev)
            steps.append((title, '\n'.join('• ' + b for b, _, _ in bullets)))
        desc = 'MistXI %s, from the server\'s own website. Source: %s' % (
            # Proper names (e.g. 'Slumbering Gods Lottery') keep their capitals.
            topic if any(w[:1].isupper() for w in topic.split()[1:]) else topic[0].lower() + topic[1:],
            ' '.join(U(p) for p in srcs))
        guides.append((topic, desc, steps))
    addons, plugins = addon_lists(texts[SI])
    check(texts, SI, 'Only items on this list are permitted.')
    if len(addons) < 20 or len(plugins) < 5:
        raise SystemExit('addon list parse failed: %d addons, %d plugins' % (len(addons), len(plugins)))
    def wrap(names):
        names = [n.rstrip('*') + (' (launcher-managed)' if n.endswith('*') else '') for n in names]
        return '\n'.join('• ' + ', '.join(names[i:i + 8]) for i in range(0, len(names), 8))
    guides.append(('Approved Ashita addons and plugins',
                   'Only addons and plugins on these lists are permitted on MistXI; any may be removed if it hurts stability or integrity. Source: ' + U(SI),
                   [('Addons (%d)' % len(addons), wrap(addons)),
                    ('Plugins (%d)' % len(plugins), wrap(plugins))]))

    os.makedirs(OUT, exist_ok=True)
    lines = ['-- Vanaguide :: data/servers/%s/server_notes.lua' % KEY,
             '-- GENERATED by tools/servers/%s.py from %s, fetched %s.  Do not hand-edit.' % (KEY, HOST, FETCHED),
             '-- Source site text is (c) 2026 MistXI, all rights reserved; no open licence stated.',
             '-- These are short factual summaries with source URLs (see each guide desc).',
             '--',
             '-- Copyright (c) 2026 Bates LLC.  All rights reserved.',
             '', 'local S = {}', '', 'S.guides = {']
    for name, desc, steps in guides:
        lines.append('    { name = %s, group = \'Server\', desc = %s, steps = {' % (lua(name), lua(desc)))
        for t, n in steps:
            lines.append('            { title = %s, note = %s },' % (lua(t), lua(n)))
        lines.append('    } },')
    lines += ['}', '', 'return S', '']
    path = os.path.join(OUT, 'server_notes.lua')
    open(path, 'w', encoding='utf-8').write('\n'.join(lines))
    print('wrote %s: %d guides, %d steps, %d addons, %d plugins' % (
        path, len(guides), sum(len(g[2]) for g in guides), len(addons), len(plugins)))


def main():
    fetch('--refresh' in sys.argv)
    build()


if __name__ == '__main__':
    main()
