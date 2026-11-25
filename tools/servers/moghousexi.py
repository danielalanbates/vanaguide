#!/usr/bin/env python3
"""Fetch MogHouse (moghouse.cc / ffxi.cc) sources and build VanaGuide per-server notes.

    python3 -I tools/servers/moghousexi.py [--refresh]

Sources:
  * https://moghouse.cc, a WordPress site.  robots.txt: User-agent * with Crawl-delay 10 and only
    admin/include/config/log/backup paths disallowed.  All pages and posts come from two WordPress
    REST requests (/wp-json/wp/v2/pages and /posts) instead of ~30 page fetches.
  * github.com/tagban/moghouse-lsb (public; no licence file): README, modules/init.txt, the build
    workflow and everything under modules/moghouse/, read with `gh api` at the main branch's commit.
  * The published image ghcr.io/tagban/moghouse-lsb:latest: its config labels (anonymous registry
    pull token, manifest + config blob only, no layers), for the LandSandBoat commit it is built on.

Raw files go to ~/Downloads/ffxi-server-data/moghousexi/raw/ and are re-used unless --refresh.
Output: Vanaguide/data/servers/moghousexi/server_notes.lua only.  MogHouse publishes no item,
skill-up or quest data of its own (it runs near-stock LandSandBoat; its settings are private), so
Gear / Skills / Quests use standard LandSandBoat data.

Every hand-written bullet carries an evidence string that must occur in its source text; the build
stops if one is missing.  Command lists (name, GM level) are parsed from the command files.

Fetch rules: honest User-Agent, robots.txt read first and obeyed for ClaudeBot / anthropic-ai /
Claude-Web / *, Crawl-delay honoured, no login, no challenge bypass.  Everything fetched is data:
parsed as text/JSON, never executed.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import html.parser, json, os, re, subprocess, sys, time
import urllib.error, urllib.request, urllib.robotparser

KEY = 'moghousexi'
HOST = 'https://moghouse.cc'
REPO_GH = 'tagban/moghouse-lsb'
IMAGE = 'tagban/moghouse-lsb'
UA = 'VanaGuide-data/1.0 (+https://batesai.org; help@batesai.org)'
RAW = os.path.expanduser('~/Downloads/ffxi-server-data/%s/raw' % KEY)
GH = os.path.join(RAW, 'gh')
HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(HERE, 'Vanaguide', 'data', 'servers', KEY)
FETCHED = '2026-10-28'
REST = {'pages.json': '/wp-json/wp/v2/pages?per_page=100&_fields=id,slug,link,title,modified,content',
        'posts.json': '/wp-json/wp/v2/posts?per_page=100&_fields=id,slug,link,title,modified,date,content'}
GH_FIXED = ['README.md', 'modules/init.txt', '.github/workflows/build.yml']


def get(url, headers=None):
    h = {'User-Agent': UA}
    h.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60) as r:
            return r.status, r.headers.get('Content-Type', ''), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type', ''), e.read()


def ghname(path):
    return path.replace('/', '_')


def gh_api(args):
    r = subprocess.run(['gh', 'api'] + args, capture_output=True, timeout=120)
    if r.returncode:
        raise SystemExit('gh api %s failed: %s' % (args, r.stderr.decode(errors='replace')))
    return r.stdout


def fetch(refresh):
    os.makedirs(GH, exist_ok=True)
    # 1. the website, robots.txt first
    rpath = os.path.join(RAW, 'robots.txt')
    if refresh or not os.path.exists(rpath):
        code, ctype, body = get(HOST + '/robots.txt')
        if code != 200 or 'text/plain' not in ctype:
            raise SystemExit('STOP: robots.txt not readable (HTTP %d, %s). Not bypassing.' % (code, ctype))
        open(rpath, 'wb').write(body)
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(open(rpath, encoding='utf-8', errors='replace').read().splitlines())
    delay = max(1.0, float(rp.crawl_delay('*') or 0), float(rp.crawl_delay('ClaudeBot') or 0))
    for name, path in REST.items():
        for agent in ('ClaudeBot', 'anthropic-ai', 'Claude-Web', '*'):
            if not rp.can_fetch(agent, HOST + path):
                raise SystemExit('STOP: robots.txt disallows %s for %s.' % (path, agent))
        out = os.path.join(RAW, name)
        if os.path.exists(out) and not refresh:
            continue
        time.sleep(delay)
        code, ctype, body = get(HOST + path)
        print('fetch', code, path, len(body))
        if code != 200 or 'json' not in ctype:
            raise SystemExit('STOP: %s answered HTTP %d (%s). Not bypassing.' % (path, code, ctype))
        open(out, 'wb').write(body)
    # 2. the repository at main's current commit
    cpath = os.path.join(GH, '_commit.json')
    if refresh or not os.path.exists(cpath):
        open(cpath, 'wb').write(gh_api(['repos/%s/commits/main' % REPO_GH]))
    sha = json.load(open(cpath))['sha']
    tpath = os.path.join(GH, '_tree.json')
    if refresh or not os.path.exists(tpath):
        open(tpath, 'wb').write(gh_api(['repos/%s/git/trees/%s?recursive=1' % (REPO_GH, sha)]))
    tree = json.load(open(tpath))['tree']
    paths = GH_FIXED + [t['path'] for t in tree
                        if t['type'] == 'blob' and t['path'].startswith('modules/moghouse/')]
    for p in paths:
        out = os.path.join(GH, ghname(p))
        if os.path.exists(out) and not refresh:
            continue
        open(out, 'wb').write(gh_api(['repos/%s/contents/%s?ref=%s' % (REPO_GH, p, sha),
                                      '-H', 'Accept: application/vnd.github.raw']))
        print('gh', p)
        time.sleep(1)
    # 3. the published image's labels (manifest + config blob; no layers)
    cfg = os.path.join(RAW, 'ghcr_config_latest.json')
    if refresh or not os.path.exists(cfg):
        code, _, body = get('https://ghcr.io/token?scope=repository:%s:pull' % IMAGE)
        if code != 200:
            raise SystemExit('STOP: ghcr token HTTP %d' % code)
        auth = {'Authorization': 'Bearer ' + json.loads(body)['token']}
        time.sleep(1)
        code, _, man = get('https://ghcr.io/v2/%s/manifests/latest' % IMAGE, dict(auth, Accept=
                           'application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'))
        if code != 200:
            raise SystemExit('STOP: ghcr manifest HTTP %d' % code)
        open(os.path.join(RAW, 'ghcr_manifest_latest.json'), 'wb').write(man)
        time.sleep(1)
        code, _, body = get('https://ghcr.io/v2/%s/blobs/%s' % (IMAGE, json.loads(man)['config']['digest']), auth)
        if code != 200:
            raise SystemExit('STOP: ghcr config HTTP %d' % code)
        open(cfg, 'wb').write(body)
    return sha, paths


class Text(html.parser.HTMLParser):
    BLOCK = ('p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'tr', 'br', 'div', 'td', 'th', 'section')

    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, t, a):
        if t in ('script', 'style'):
            self.skip += 1
        if t in self.BLOCK:
            self.out.append('\n')
        if t in ('td', 'th'):
            self.out.append(' | ')

    def handle_endtag(self, t):
        if t in ('script', 'style'):
            self.skip -= 1

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d)


def norm(s):
    for a, b in (('\u2019', "'"), ('\u2018', "'"), ('\u201c', '"'), ('\u201d', '"'),
                 ('\u2013', '-'), ('\u2014', '-'), ('\u2033', '"'), ('\xa0', ' '), ('\x92', "'")):
        s = s.replace(a, b)
    return s


def wp_texts():
    """slug -> (link, modified, plain text) for every page and post."""
    res = {}
    for f in REST:
        for p in json.load(open(os.path.join(RAW, f), encoding='utf-8')):
            body = re.sub(r'\[/?et_pb[^\]]*\]', '\n', p['content']['rendered'])  # Divi builder shortcodes
            t = Text()
            t.feed(body)
            t = re.sub(r'[ \t]+', ' ', norm(''.join(t.out)))
            res[p['slug']] = (p['link'], p['modified'][:10], '\n'.join(l.strip() for l in t.split('\n') if l.strip()))
    return res


def gh_text(path):
    return open(os.path.join(GH, ghname(path)), encoding='utf-8').read()


def commands():
    """[(name, permission)] from modules/moghouse/commands/*.lua."""
    res = []
    for f in sorted(os.listdir(GH)):
        m = re.fullmatch(r'modules_moghouse_commands_(\w+)\.lua', f)
        if not m:
            continue
        src = open(os.path.join(GH, f), encoding='utf-8').read()
        reg = re.search(r"registerCommand\('(\w+)'", src)
        perm = re.search(r'permission\s*=\s*(\d+)', src)
        if not reg or not perm:
            raise SystemExit('cannot parse command file %s' % f)
        res.append((reg.group(1), int(perm.group(1))))
    return res


def lua(s):
    return "'" + s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n') + "'"


# Source keys: 'wp:<slug>' = website page/post text; 'gh:<path>' = repository file.
GS, GMC, HOME, WEL, FUN = 'wp:getting-setup', 'wp:gm-commands', 'wp:home-moghouse-cc', 'wp:welcome-to-moghouse-cc', 'wp:fun-stuff'
README, INIT, CPPR, JUMP = 'gh:README.md', 'gh:modules/init.txt', 'gh:modules/moghouse/cpp/README.md', 'gh:modules/moghouse/jump.lua'
C = 'gh:modules/moghouse/commands/%s.lua'

# Player (GM level 0) commands: name -> [(bullet, source, evidence)].  Every level-0 command in the
# repository must have an entry here, and no entry may name a command that is not level 0.
PLAYER_CMDS = {
    'home': [('!home: warps you to your Home Point.', C % 'home', 'player:warp()')],
    'shop': [('!shop <page>: the BNET.cc shop, anywhere in the world. !shop alone lists the pages.', C % 'shop', 'opens a custom shop anywhere in the world'),
             ('Page 1: HQ elemental crystals, 3,000 gil each.', C % 'shop', '{ 4238, 3000 }, -- HQ Fire Crystal'),
             ('Page 2: food (Meat Jerky, Crab Sushi, Rice Dumpling, Blackened Frog) at Auction House prices.', C % 'shop', 'same price as AH so non exploitable'),
             ('Page 3: medicines and tools, e.g. Instant Reraise 15,000, Silent Oil / Prism Powder / Icarus Wing 5,000.', C % 'shop', '{ 4182, 15000 }, -- Instant Reraise'),
             ('Page 4: misc gear, e.g. Chariot / Empress Band 15,000, Emperor Band 35,000, Key Ring Belt 32,000.', C % 'shop', '{ 15763, 35000 }, -- Emperor Band'),
             ('Page 5: ninja tools, 500 gil each.', C % 'shop', 'All the ninja Tools you need'),
             ('Page 6: Corsair dice, 100 gil each.', C % 'shop', '{ 5502, 100 }, -- Allies\' Die'),
             ('Page 7: fireworks, 100 gil each.', C % 'shop', '{ 4186, 100 }, -- Airborne'),
             ('Page 8: costume sets (Chocobo, Moogle, Novennial, Dinner, swimsuits, Dream), 10,000 gil each.', C % 'shop', '-- CHOCOBO SET')],
    'job': [('!job: a shop of your current main job\'s Artifact (AF1) pieces plus a job neck/weapon item, 35,000-45,000 gil each.', C % 'job', '-- AF1'),
            ('Covers WAR through SCH; on GEO or RUN it refuses (the code calls those jobs broken).', C % 'job', 'GEO is Broken')],
    'apocnigh': [('!apocnigh: buy Ethereal, Hallow, Magnetic or Static Earring for 500,000 gil each.', C % 'apocnigh', '{ 15965, 500000 }, -- Ethereal Earring'),
                 ('Requires Zilart mission "Awakening" and Chains of Promathia "Dawn" completed, and nation rank 9 or higher.', C % 'apocnigh', 'Must have RoZ and CoP done and rank 9.')],
    'starlight': [('!starlight: holiday (Starlight) event shop: Dream +1 gear 30 gil a piece, plus a few event items. Opened to players for the event ("Modded 11/24").', C % 'starlight', 'Modded 11/24 to prep for the event.')],
    'fixspeed': [('!fixspeed: clears any movement-speed override, back to the server\'s regular speed.', C % 'fixspeed', 'player:setMod(xi.mod.MOVE_SPEED_OVERRIDE, 0)')],
    'grats': [('!grats: plays the congratulations animation seen with fireworks.', C % 'grats', 'triggers the congratulation animation')],
    'kill': [('!kill: a TRAP. It kills whoever types it and takes 20,000 EXP. Do not use it.', C % 'kill', 'kills whoever types it and takes 20000 exp')],
}

# GM level 1 commands (the website says players get GM level 1; see the 'Commands' guide).
GM1_CMDS = {
    'aery': ('!aery: teleport to Dragon\'s Aery (Fafnir / Nidhogg).', C % 'aery', 'Teleports player to Fafnir/Nidhogg.'),
    'cerberus': ('!cerberus: teleport to Cerberus.', C % 'cerberus', 'Teleports player to Cerberus.'),
    'dominion': ('!dominion: teleport to Behemoth\'s Dominion (Behemoth / King Behemoth).', C % 'dominion', 'Teleports player to Behemoth/King Behemoth.'),
    'kirin': ('!kirin: teleport to Kirin.', C % 'kirin', 'Teleports player to Kirin.'),
    'seahorror': ('!seahorror: spawns several commonly requested NMs at once.', C % 'seahorror', 'Spawns a ton of NMs at once.'),
    'chocobo': ('!chocobo: summons a chocobo to ride.', C % 'chocobo', 'Spawns a chocobo.'),
    'up': ('!up [n]: moves you up.', C % 'up', 'Alters vertical coordinate'),
    'down': ('!down [n]: moves you down.', C % 'down', 'Alters vertical coordinate'),
    'flash': ('!flash: maximum movement speed.', C % 'flash', 'Max movement speed.'),
    'fly': ('!fly: fly; walls and the ground still stop you unless your own wallhack was on at take-off. Again: back down on the nearest floor. With the MogHouse launcher, Space rises and X sinks.', C % 'fly', 'Space rises, X sinks'),
    'flymount': ('!flymount [name]: fly on a mount (chocobo by default, or e.g. hippogryph, tulfaire, levitus, fenrir; MogHouse-client-only bee, airship, boat, which other clients see as a retail mount).', C % 'flymount', '!flymount bee (sized to its rider)'),
    'gmgear': ('!gmgear: gives GM gear.', C % 'gmgear', 'GM Gear.'),
    'gmisland': ('!gmisland: sends you to a secret island.', C % 'gmisland', 'secret island'),
    'learnmagic': ('!learnmagic: learn all valid spells except Trusts.', C % 'learnmagic', 'Adds all valid spells EXCEPT TRUSTS'),
    'mobmp': ('!mobmp: a mob testing tool (targeted mob or by mob ID).', C % 'mobmp', 'MUST either target a mob first or else specify a Mob ID.'),
    'signet': ('!signet: grants Signet for (your rank + your nation\'s rank + 3) hours.', C % 'signet', '(player:getRank(nation) + GetNationRank(nation) + 3) * 3600'),
    'skyfx': ('!skyfx: a zone-wide look (aurora, wireframe, colour filter) that only MogHouse\'s own client draws; other clients see the zone as usual.', C % 'skyfx', 'Other clients see the zone as ever.'),
    'slap': ('!slap <player> [damage]: knocks the target back; damage is optional and defaults to 0 (no damage).', C % 'slap', 'local dmg = damage or 0'),
}

TOPICS = [
    ('What MogHouse is', [HOME, README, GS, WEL, 'image'], [
        ('The server', [
            ('MogHouse (moghouse.cc) is run by BNET.cc, which has served the FFXI community since nearly 2006 as part of eArena.net, with a publicly accessible private server for simple exploration.', HOME, 'served the Final Fantasy XI community from nearly 2006 as a part of eArena.net'),
            ('Server address: --server ffxi.cc. Both Windower and Ashita are supported.', GS, 'Server address: -server ffxi.cc'),
            ('It runs LandSandBoat (the newest base branch when the image is built) with MogHouse\'s own modules; nothing is compiled on the server, it pulls a built image.', README, 'The server pulls it; nothing is compiled there.'),
            ('This is a fun / GM-sandbox server: per the GM Commands page, players are set up as GM level 1, and there is no active Auction House because of !additem.', GMC, 'have an active Auction House due to !additem command'),
        ]),
        ('Status notes from the site', [
            ('Home page (last edited 2026-03-03): BNET.cc says it is ending its hosting of servers and moving to community-focused work; the site is kept as a client-setup guide and advice for would-be server hosts.', HOME, 'until we have finished ending our hosting of servers'),
            ('March 2023 post: a new server version dedicated to the Zilart era launched and ALL characters/accounts were reset.', WEL, 'ALL chars/accounts are reset'),
            ('The current module list does not enable any LandSandBoat era/ module; it only mentions them as available.', INIT, "LandSandBoat's era/ modules"),
        ]),
    ]),
    ('Modules that change gameplay', [INIT, CPPR, JUMP, README], [
        ('Loaded modules (modules/init.txt)', [
            ('Login announcement: "Player <name> has logged in." is shown to everyone at login (not when zoning).', INIT, 'has logged in." to everyone, at login (not when zoning)'),
            ('Discord bridge: Say, Shout and Yell are relayed for the Discord bot and sent to every zone, as the server settings say.', INIT, 'Say, Shout and Yell recorded for the bot'),
            ('A test NPC in the GM home.', INIT, 'a test NPC in the GM home'),
            ('MogHouse\'s GM commands (see the Commands guide).', INIT, "MogHouse's GM commands"),
        ]),
        ('/jump really jumps (jump.lua + jump.cpp)', [
            ('The game\'s /jump normally only plays an animation; here it lifts you a little, and if there is a higher floor within 3 yalms ahead you leap onto it (a rock, a step).', JUMP, 'Unless there is a higher floor within 3 yalms ahead'),
            ('A leap lands at most 6 yalms above where it started.', JUMP, 'MAX_RISE  = 6.0'),
            ('One jump at a time: jumps never stack into flying.', JUMP, 'they never stack'),
        ]),
        ('C++ helpers (modules/moghouse/cpp)', [
            ('knockback.cpp: lets scripts knock a player back as mob skills do (used by !slap).', CPPR, '`!slap` uses it'),
            ('jump.cpp: also holds !fly fliers to the zone\'s collision, so flying through walls or the ground is refused.', CPPR, "It also holds `!fly`'s fliers to the zone's collision"),
            ('skyfx.cpp: zone looks (aurora, wireframe, colour filter) drawn only by MogHouse\'s own client (ffxi-native); other clients see nothing new.', CPPR, 'other clients read only the weather'),
            ('mount.cpp: lets !flymount show the mount; MogHouse\'s own mounts (bee, airship, boat) are seen by other clients as a retail mount.', CPPR, 'MogHouse\'s client makes its own from 40 on'),
        ]),
        ('Turned off', [
            ('LandSandBoat\'s other optional modules (Home Point heal, AH pagination and sale notices, NM claim shield, chocobo-raising QoL, world-first announcements and more) are listed but commented out: off.', INIT, 'Off; to turn one on'),
            ('The custom HNM system (Fafnir/Nidhogg, Adamantoise/Aspidochelone, Behemoth/King Behemoth) is also off.', INIT, 'custom/lua/custom_hnm_system.lua'),
        ]),
    ]),
    ('Gear, skills and rates', [README, INIT], [
        ('What applies', [
            ('No module changes items, drops, crafting or skill-ups, so Gear and Skills here are standard LandSandBoat data.', INIT, "MogHouse's GM commands"),
            ('Rates and other server settings are kept in the server\'s private repository, not the public one, so EXP / skill-up rates are not published.', README, "the server's settings and passwords stay on the server"),
            ('Gear can be bought anywhere from the command shops in the Commands guide (!shop, !job, !apocnigh).', C % 'job', 'Job Shop for BNET.cc Players.'),
        ]),
    ]),
]


def build(sha, paths):
    wp = wp_texts()
    gh = {'gh:' + p: gh_text(p) for p in paths}
    cfg = json.load(open(os.path.join(RAW, 'ghcr_config_latest.json')))
    labels = cfg['config']['Labels']
    lsb = labels['cc.moghouse.lsb-commit']
    mogrev = labels['cc.moghouse.revision']
    built = cfg.get('created', '')[:10]
    oci_built = labels.get('org.opencontainers.image.created', '')[:10]
    if oci_built and oci_built != built:
        built_txt = 'image config "created" %s; OCI label org.opencontainers.image.created %s' % (built, oci_built)
    else:
        built_txt = 'image config "created" %s' % built
    robots = open(os.path.join(RAW, 'robots.txt'), encoding='utf-8').read()

    def text(src):
        if src.startswith('wp:'):
            return wp[src[3:]][2]
        return gh[src]

    def url(src):
        if src == 'image':
            return 'https://github.com/users/%s/packages/container/package/moghouse-lsb' % REPO_GH.split('/')[0]
        if src.startswith('wp:'):
            return wp[src[3:]][0]
        return 'https://github.com/%s/blob/%s/%s' % (REPO_GH, sha[:10], src[3:])

    def check(src, ev):
        if ev not in text(src):
            raise SystemExit('EVIDENCE MISSING in %s: %r' % (src, ev))

    cmds = commands()
    lvl = {n: p for n, p in cmds}
    p0 = sorted(n for n, p in cmds if p == 0)
    p1 = sorted(n for n, p in cmds if p == 1)
    staff = sorted(n for n, p in cmds if p >= 2)
    if sorted(PLAYER_CMDS) != p0:
        raise SystemExit('player command list changed: code %s, notes %s' % (p0, sorted(PLAYER_CMDS)))
    if sorted(GM1_CMDS) != p1:
        raise SystemExit('GM1 command list changed: code %s, notes %s' % (p1, sorted(GM1_CMDS)))

    # site's 2022 list of MogHouse-custom commands no longer in the repository
    site_custom = re.findall(r'\| (![\w/ !]+?)\n\| [^\n]*\n\| Y\b', wp['gm-commands'][2])
    site_names = set()
    for s in site_custom:
        site_names.update(x.strip().lstrip('!') for x in s.split('/'))
    gone = sorted(n for n in site_names if n not in lvl and n not in ('homepoint', 'bring'))  # !bring is stock LandSandBoat, per the site

    guides = []
    srcs_all = [wp[s][0] for s in ('home-moghouse-cc', 'getting-setup', 'gm-commands', 'other-servers', 'fun-stuff', 'welcome-to-moghouse-cc')]
    about = [
        ('What was fetched', [
            '• On %s: every page and post of %s through its WordPress REST API (%d pages, %d posts in two requests), robots.txt first.' % (
                FETCHED, HOST, len(json.load(open(os.path.join(RAW, 'pages.json')))), len(json.load(open(os.path.join(RAW, 'posts.json'))))),
            '• robots.txt: User-agent * with Crawl-delay 10 (honoured) and only admin/includes/config/logs/backup paths disallowed; no rule names ClaudeBot, anthropic-ai or Claude-Web.' if 'Crawl-delay: 10' in robots else '• robots.txt read and obeyed.',
            '• github.com/%s at commit %s: README, modules/init.txt, the build workflow and all %d files under modules/moghouse/.' % (
                REPO_GH, sha[:10], sum(1 for p in paths if p.startswith('modules/moghouse/'))),
            '• The published image ghcr.io/%s:latest (%s): label cc.moghouse.lsb-commit = LandSandBoat %s, MogHouse revision %s.' % (
                IMAGE, built_txt, lsb[:10], mogrev[:7]),
            '• Each bullet is checked against the fetched text when this file is generated; command levels are read from the code.']),
        ('Not covered', [
            '• No gear, skill or quest file is made for MogHouse: it publishes no item, drop, crafting or quest changes. Gear, Skills and Quests use standard LandSandBoat data.',
            '• EXP / skill-up rates and other settings are private (server-side settings), so they are unknown.',
            '• The site\'s ID reference pages (zone, music, weather, costume, mission/quest IDs), client setup guides and the Other Servers list are not converted.',
            '• Discord and live server status are not read. The GM Commands page dates from 2022 (last edited 2022-12-10); the repository code is newer and wins where they differ.']),
        ('Licence', [
            '• Neither the website nor the repository states a licence (all rights reserved by default). These notes are short factual summaries with source links, not copies.']),
    ]
    guides.append(('About this data', 'What this MogHouse data is built from and what it leaves out. Source: %s %s https://github.com/%s https://ghcr.io/%s' % (
        HOST + '/wp-json/wp/v2/pages', HOST + '/wp-json/wp/v2/posts', REPO_GH, IMAGE), [(t, '\n'.join(b)) for t, b in about]))

    for topic, srcs, subs in TOPICS:
        steps = []
        for title, bullets in subs:
            for _, src, ev in bullets:
                check(src, ev)
            steps.append((title, '\n'.join('• ' + b for b, _, _ in bullets)))
        if topic == 'What MogHouse is':
            steps.append(('Server build', '• Image ghcr.io/%s:latest (%s) is built on LandSandBoat commit %s (label cc.moghouse.lsb-commit) with MogHouse revision %s.\n• Rebuilt nightly when LandSandBoat or the repository changes; an image is published only if MogHouse\'s tests pass.' % (
                IMAGE, built_txt, lsb[:10], mogrev[:7])))
            check(README, 'if a test fails, nothing is published')
        desc = 'MogHouse server notes: %s. Source: %s' % (topic[0].lower() + topic[1:], ' '.join(dict.fromkeys(url(s) for s in srcs)))
        guides.append((topic, desc, steps))

    # Commands
    steps = []
    pb = []
    for n in p0:
        for b, src, ev in PLAYER_CMDS[n]:
            check(src, ev)
            pb.append(b)
    steps.append(('Player commands (GM level 0: everyone)', '\n'.join('• ' + b for b in pb[:1] + [b for b in pb[1:]])))
    g1 = []
    for n in p1:
        b, src, ev = GM1_CMDS[n]
        check(src, ev)
        g1.append(b)
    check(GMC, 'We have custom GM level setup for players which adjusts to Level 1 GM')
    steps.append(('GM level 1 commands', '• The GM Commands page (2022) says players are set up as GM level 1; if that still holds, these also work for players.\n' + '\n'.join('• ' + b for b in g1)))
    check(GMC, '!addallmaps')
    check(GMC, 'This allows the following to work.')
    steps.append(('Stock LandSandBoat GM commands', '• The site says its GM level 1 setup is what lets players use the listed commands; its example is !addallmaps (all maps).\n• The site lists !costume <id> (0 removes it), !changejob <JOB> <level>, !zone, !wallhack and many more; which ones work depends on their GM level in LandSandBoat.'))
    check(GMC, '!costume')
    check(FUN, '!wallhack')
    note = '• %d further commands are GM level 2+ (staff only) and are not listed.' % len(staff)
    if gone:
        note += '\n• Listed as MogHouse-custom on the 2022 site but not in the current code: %s.' % ', '.join('!' + g for g in gone)
    steps.append(('Not for players', note))
    cmd_srcs = [url(GMC), 'https://github.com/%s/tree/%s/modules/moghouse/commands' % (REPO_GH, sha[:10])]
    guides.append(('Commands', 'Commands on MogHouse, levels read from the command code. Source: ' + ' '.join(cmd_srcs), steps))

    # Getting started
    gs = [('Install the full FFXI client from the site\'s package (download every part into one folder and run part1.exe); it was last updated May 2019.', GS, 'last updated in May 2019'),
          ('Select all three options when installing.', GS, 'be sure to select all three options'),
          ('Then update / verify the client files, and pick Windower or Ashita as the bootloader.', GS, 'either Windower or Ashita (we support both)')]
    fun = [('!up and !down move you vertically; !wallhack, !flash and !fly toggle (use again to turn off).', FUN, 'All of the above commands can be used a second time (except for !up and !down) to turn off.'),
           ('If !wallhack leaves you at the wrong height, go back up to normal level to reset.', FUN, "sometimes you'll have to go back up to normal level to reset")]
    for _, s, e in gs + fun:
        check(s, e)
    guides.append(('Getting started', 'Client setup and the fun movement commands. Source: %s %s' % (url(GS), url(FUN)),
                   [('Client setup', '\n'.join('• ' + b for b, _, _ in gs)),
                    ('Movement fun (site post, 2021)', '\n'.join('• ' + b for b, _, _ in fun))]))

    os.makedirs(OUT, exist_ok=True)
    lines = ['-- Vanaguide :: data/servers/%s/server_notes.lua' % KEY,
             '-- GENERATED by tools/servers/%s.py from %s and github.com/%s @ %s, fetched %s.  Do not hand-edit.' % (KEY, HOST, REPO_GH, sha[:10], FETCHED),
             '-- Server image built on LandSandBoat %s.  No licence is stated by the site or the repository;' % lsb[:10],
             '-- these are short factual summaries with source URLs (see each guide desc).',
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
    print('wrote %s: %d guides, %d steps; commands: %d player, %d GM1, %d staff; LSB %s' % (
        path, len(guides), sum(len(g[2]) for g in guides), len(p0), len(p1), len(staff), lsb[:10]))


def main():
    sha, paths = fetch('--refresh' in sys.argv)
    build(sha, paths)


if __name__ == '__main__':
    main()
