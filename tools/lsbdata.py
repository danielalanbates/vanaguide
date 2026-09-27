#!/usr/bin/env python3
"""Vanaguide :: tools/lsbdata.py

The parts of a LandSandBoat checkout that both generators need.

Quests and missions are written by the same people in the same house style, which is to say
in six house styles. Reading the header of one and the header of the other used to be two
copies of the same regex, and the copy in gen_missions.py knew about one dialect out of six --
so missions lost the NPC that quests had just gained.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import difflib
import math
import os
import re


def normalize(name):
    return re.sub(r'[^a-z0-9]', '', (name or '').lower())


def clean_npc_name(raw):
    """Header comments label the name as often as they just state it.

    "NPC: Ayame", "Door: Merchant's House (H-8)", "Ranpi-Monpi (S) -", "qm6 (H-10/Boat)" --
    the label, the map reference in brackets and a trailing dash are all decoration. What is
    left is either a name the server knows or it is not, and that is the useful question.

    Mission headers add one more decoration: a step number. "1. Enter Lower Delkfutt" is the
    first of three numbered instructions, and "1." is no part of anybody's name.

    The "Door:" label is stripped here, but the server's own name for a door keeps it
    ("Door:Neptune's Spire"), so a lookup has to try the raw label as well -- see
    name_candidates().
    """
    name = re.sub(r'^\s*\d+\.\s*', '', raw)
    name = re.sub(r'^\s*(?:NPC|Door|Marker|QM)\s*:\s*', '', name, flags=re.I)
    name = name.split(',')[0]
    name = re.sub(r'\s*\([^)]*\)\s*$', '', name)
    # "Glenne - Southern Sandoria": the name, then where to find it.
    name = re.split(r'\s+-\s+', name)[0]
    return name.strip(' -:\t')


def name_candidates(raw):
    """Every name a header label could be pointing at, most literal first.

    A header label is the NPC's name as often as it is something else with the name inside it:

        Door: Neptune's Spire              the server calls it "Door:Neptune's Spire"
        Shattered Telepoint (Konschtat)    the name, then which of three
        Granite Door (_4fx)                the name, then the server's internal name
        _700 (Oaken Door)                  the internal name, then the name
        Ploh Trishbahk (trigger area)      the name, then what it is for

    Each of those is tried in turn; whichever the server actually has is the answer.
    """
    out = []

    def add(name):
        name = (name or '').strip(' -:\t')
        if name and name not in out:
            out.append(name)

    raw = re.sub(r'^\s*\d+\.\s*', '', raw or '')
    add(raw)
    add(re.sub(r'\s*\([^)]*\)\s*$', '', raw))
    add(clean_npc_name(raw))
    for inner in re.findall(r'\(([^)]*)\)', raw):
        add(inner)
    # The server's internal names: `_4fx`, `qm_maw`, `Ergon_Locus_3`. Written into a label
    # they are the most exact thing it says.
    for token in re.findall(r"(?<![\w'])(_\w+|qm\w*|[A-Za-z]+(?:_\w+)+)(?![\w'])", raw):
        add(token)
    return out


def similar(a, b):
    """0..1: how alike two names are once spelling-insensitive. "Nashib" / "Nahshib" = 0.92."""
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def parse_zone_ids(root):
    """scripts/enum/zone.codegen.lua -> {ABYSSEA_ALTEPA: 218}."""
    out = {}
    path = os.path.join(root, 'scripts/enum/zone.codegen.lua')
    if not os.path.exists(path):
        return out
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r"\s*([A-Z][A-Z0-9_]*)\s*=\s*(\d+)", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


class NpcList(dict):
    """(zone, normalized display name) -> [(x, y, z, display name), ...].

    A dict, so every existing `in` and `.get` still means what it meant. `by_internal` is a
    second index on the server's internal name, for the one pass that needs it. `by_zone`
    lists every placed entity of a zone as (x, y, z, display name, internal name, has display
    name), for the question "what is standing at this spot?".
    """

    def __init__(self):
        super().__init__()
        self.by_internal = {}
        self.by_zone = {}


def parse_npc_list(root):
    """sql/npc_list.sql -> {(zone, normalized name): [(x, y, z), ...]}.

    Every row for a name, not the first: a name is not unique inside a zone.

    The header comment of a quest script names who to talk to, but only sometimes with a
    `!pos` beside it -- 160 quests, nearly all of them Abyssea dominion ops, name the NPC and
    no position at all. That is not a missing fact, only a missing copy of one: the server
    ships `npc_list.sql`, and the zone is encoded in the id.

        zone = (npcid >> 12) & 0xFFF

    Reading the shipped SQL rather than a live database keeps this a generator: it runs
    against a checkout, with no server up.
    """
    path = os.path.join(root, 'sql/npc_list.sql')
    out = NpcList()
    if not os.path.exists(path):
        return out
    row = re.compile(r"\((\d+),'((?:[^']|\\')*)','((?:[^']|\\')*)',\s*\d+,"
                     r"(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)")
    for line in open(path, encoding='utf-8', errors='replace'):
        if not line.startswith('INSERT'):
            continue
        for m in row.finditer(line):
            npcid = int(m.group(1))
            # The dump escapes an apostrophe as \' -- "Tales\' Beginning" is Tales' Beginning,
            # and the escaped form is what used to reach the player.
            internal = m.group(2).replace("\\'", "'")
            shown = m.group(3).replace("\\'", "'")
            name = shown or internal
            x, y, z = float(m.group(4)), float(m.group(5)), float(m.group(6))
            if x == 0.0 and y == 0.0 and z == 0.0:
                continue        # placed at runtime; a position of (0,0,0) is not one
            key = ((npcid >> 12) & 0xFFF, re.sub(r'[^a-z0-9]', '', name.lower()))
            # Every row, not the first one. A name is not unique inside a zone -- twenty
            # "Stone Door" in Ordelle's Caves, thirteen "Ornate Door" in the Quicksand Caves,
            # nine "Regal Pawprints" in Beaucedine -- and keeping only the first meant the
            # override below moved entries onto whichever instance happened to be earliest in
            # the file. Twenty-six entries were relocated that way, by eleven to twelve
            # hundred yalms, and both checks then blessed the new position: the server check
            # re-derived the same row, and the client sweep teleported there and found
            # another entity with the same name standing at it.
            places = out.setdefault(key, [])
            places.append((x, y, z, name))
            # The internal name, indexed separately and consulted only when the display name
            # has failed. A script's own section keys are internal names -- `['_6s1']`,
            # `['qm_maw']`, `['Lion_Springs']` -- and the display index cannot see them, so
            # the rescue pass that reads those keys could never fire for a door or a marker.
            # Kept out of the primary index deliberately: putting both namespaces in one map
            # changes which candidate the header pass picks, and doing that relocated four
            # entries onto the wrong NPC in a different zone.
            out.by_internal.setdefault(
                ((npcid >> 12) & 0xFFF, re.sub(r'[^a-z0-9]', '', internal.lower())),
                []).append((x, y, z, name))
            out.by_zone.setdefault((npcid >> 12) & 0xFFF, []).append(
                (x, y, z, name, internal, bool(shown)))
    return out


# --------------------------------------------------------------------------------------------
# The script itself: `mission.sections`, read as structure rather than as text.
#
# A header comment is somebody's summary of the script. The sections are the script: which
# zone, which NPC, which trigger area, at which stage of the mission. Where the header says
# nothing, or says it wrongly, this is what is left to ask -- and it can only be asked of the
# structure, because "the first NPC the text mentions" is as often a line of flavour dialogue
# for a mission that has not started yet as it is the NPC who starts it.
# --------------------------------------------------------------------------------------------

def _lua_depths(text):
    """Brace depth at every character, and whether that character is code (not a string or a
    comment). Braces inside strings and comments do not count."""
    n = len(text)
    depth = [0] * (n + 1)
    code = [True] * (n + 1)
    d, i = 0, 0
    while i < n:
        skip = None
        if text.startswith('--[[', i):
            end = text.find(']]', i)
            skip = n if end < 0 else end + 2
        elif text.startswith('--', i):
            end = text.find('\n', i)
            skip = n if end < 0 else end
        elif text[i] in '\'"':
            j = i + 1
            while j < n and text[j] != text[i] and text[j] != '\n':
                j += 2 if text[j] == '\\' else 1
            skip = min(n, j + 1)
        elif text.startswith('[[', i):
            end = text.find(']]', i)
            skip = n if end < 0 else end + 2
        if skip is not None:
            for k in range(i, skip):
                depth[k], code[k] = d, False
            i = skip
            continue
        depth[i] = d
        if text[i] == '{':
            d += 1
        elif text[i] == '}':
            d -= 1
        i += 1
    depth[n] = d
    return depth, code


def _lua_close(text, depth, code, open_at):
    """Index of the '}' that closes the '{' at open_at."""
    for k in range(open_at + 1, len(text)):
        if text[k] == '}' and code[k] and depth[k] == depth[open_at] + 1:
            return k
    return len(text)


def _lua_keys(text, depth, code, lo, hi, pattern):
    """Matches of `pattern` that sit directly inside the table text[lo..hi], in order, each with
    the text up to the next one."""
    hits = [m for m in pattern.finditer(text, lo + 1, hi)
            if code[m.start()] and depth[m.start()] == depth[lo] + 1]
    return [(m, text[m.start():(hits[i + 1].start() if i + 1 < len(hits) else hi)])
            for i, m in enumerate(hits)]


_ZONE_KEY = re.compile(r"\[\s*xi\.zone\.([A-Z0-9_]+)\s*\]\s*=\s*\{")
_ENTRY_KEY = re.compile(r"(?:\[\s*'([^']+)'\s*\]|\[\s*\"([^\"]+)\"\s*\]|\b(on[A-Z]\w*))\s*=")


def script_sections(text):
    """`mission.sections` (or `quest.sections`) as [(check text, [(ZONE_ENUM, [(key, body)])])].

    `key` is an NPC's internal name (`'Naja_Salaheem'`) or a handler (`'onZoneIn'`,
    `'onTriggerAreaEnter'`), in the order the script lists them. Sections built by a loop at
    run time rather than written out are invisible here, and that is the right answer: they
    name no one place.
    """
    m = re.search(r"\b(?:mission|quest)\.sections\s*=\s*\{", text)
    if not m:
        return []
    depth, code = _lua_depths(text)
    lo = m.end() - 1
    hi = _lua_close(text, depth, code, lo)
    out = []
    k = lo + 1
    while k < hi:
        if text[k] == '{' and code[k] and depth[k] == depth[lo] + 1:
            s_hi = _lua_close(text, depth, code, k)
            zones, first = [], None
            for zm, _ in _lua_keys(text, depth, code, k, s_hi, _ZONE_KEY):
                first = zm.start() if first is None else first
                z_lo = zm.end() - 1
                z_hi = _lua_close(text, depth, code, z_lo)
                entries = [(em.group(1) or em.group(2) or em.group(3), body)
                           for em, body in _lua_keys(text, depth, code, z_lo, z_hi, _ENTRY_KEY)]
                zones.append((zm.group(1), entries))
            out.append((text[k:first if first is not None else s_hi], zones))
            k = s_hi + 1
            continue
        k += 1
    return out


def section_keys(sections, zone_enum):
    """Every NPC key the script's sections name in one zone, normalized."""
    return {normalize(key) for _, zones in sections for z, entries in zones if z == zone_enum
            for key, _ in entries if not re.match(r'on[A-Z]', key)}


def zone_dirs(root, zone_ids):
    """zone id -> scripts/zones/<folder>. The folder is the enum name in another spelling:
    AHT_URHGAN_WHITEGATE is Aht_Urhgan_Whitegate, SOUTHERN_SAN_DORIA_S is
    Southern_San_dOria_[S]."""
    base = os.path.join(root, 'scripts/zones')
    by_norm = {normalize(enum): zid for enum, zid in zone_ids.items()}
    out = {}
    if os.path.isdir(base):
        for folder in os.listdir(base):
            zid = by_norm.get(normalize(folder))
            if zid is not None:
                out[zid] = os.path.join(base, folder)
    return out


_AREA = re.compile(
    r"register(Cuboid|Cylindrical|Spherical)TriggerArea\(\s*(\d+)\s*((?:,\s*-?[\d.]+\s*)+)\)")


def trigger_areas(zone_dir):
    """{area id: (x, z)} from a zone's Zone.lua -- the middle of each trigger area the zone
    registers with literal numbers. The signatures are LandSandBoat's own
    (src/map/lua/lua_zone.cpp): Cuboid(id, xMin, yMin, zMin, xMax, yMax, zMax),
    Cylindrical(id, x, z, radius), Spherical(id, x, y, z, radius)."""
    out = {}
    path = os.path.join(zone_dir or '', 'Zone.lua')
    if not os.path.exists(path):
        return out
    for m in _AREA.finditer(open(path, encoding='utf-8', errors='replace').read()):
        kind, aid = m.group(1), int(m.group(2))
        n = [float(v) for v in re.findall(r'-?[\d.]+', m.group(3))]
        if kind == 'Cuboid' and len(n) == 6:
            out.setdefault(aid, ((n[0] + n[3]) / 2, (n[2] + n[5]) / 2, (n[1] + n[4]) / 2))
        elif kind == 'Cylindrical' and len(n) == 3:
            out.setdefault(aid, (n[0], n[1], None))
        elif kind == 'Spherical' and len(n) == 4:
            out.setdefault(aid, (n[0], n[2], n[1]))
    return out


def resolve_label(label, zone, x, z, npc_list, keys=(), near=8.0):
    """What a header line is pointing at: {'name', 'x', 'y', 'z', 'shown', 'how'} or None.

    `label` is the header's text, `x`/`z` its coordinate, `keys` the normalized NPC keys the
    script's sections use in that zone. In order:

    1. A name the server has in that zone -- the label itself, or any name inside it (see
       name_candidates) -- standing within `near` yalms of the coordinate.
    2. Something standing within `near` yalms of the coordinate that the script itself
       interacts with (a section key), or whose name is the label's name misspelt. "Batallia
       Downs : !pos -48 0.1 435 105" names the zone, and three yalms away stands the Cavernous
       Maw the script's `['Cavernous_Maw']` section is about. "Nashib" is the server's
       "Nahshib", at the very coordinate.
    3. A name the client shows, farther away: the comment typed the coordinate wrong, and the
       server's row is the fact ("Hollowed Pathway" at x=215 where the server has x=-215).
       Only a shown name counts here. "Blank (Cait Sith)" also matches a dozen unnamed
       entities the server calls `blank`, three hundred yalms from the one the script means.

    None means the label is not an NPC at all -- a place, or an instruction.
    """
    rows = npc_list.by_zone.get(zone, []) if npc_list else []
    if not rows:
        return None

    def dist(r):
        return 0.0 if x is None else math.hypot(r[0] - x, r[2] - z)

    def found(r, how):
        return {'name': r[3], 'x': r[0], 'y': r[1], 'z': r[2], 'shown': r[5],
                'how': how, 'dist': dist(r)}

    names = [normalize(c) for c in name_candidates(label)]
    named = [[r for r in rows if n and n in (normalize(r[3]), normalize(r[4]))] for n in names]

    for hits in named:
        close = [r for r in hits if dist(r) <= near]
        if close:
            return found(min(close, key=dist), 'name')

    if x is not None:
        best = None
        for r in rows:
            d = dist(r)
            if d > near:
                continue
            own = {normalize(r[3]), normalize(r[4])}
            keyed = bool(own & set(keys))
            spelt = any(similar(o, n) >= 0.85 for o in own for n in names)
            if (keyed or spelt) and (best is None or d < best[0]):
                best = (d, r)
        if best is not None:
            return found(best[1], 'near')

    for n, hits in zip(names, named):
        shown = [r for r in hits if r[5] and normalize(r[3]) == n]
        if shown:
            return found(min(shown, key=dist), 'name')
    return None


def find_npc(text, lines, title, zone_ids, npc_list, allow_zone_only=False):
    """Who to talk to, and where they stand, from a quest or mission script.

    Six header dialects, then the script's own section tables, then a last pass that lets the
    server's npc_list overrule a position the comment states wrongly. Returns None only when
    the script really does name nobody anywhere.
    """
    # Header comments name who to talk to, in three dialects that all mean the same thing:
    #
    #   -- Balasiel : !pos -136 -11 64 230
    #   -- Curilla : !pos: -467.7 -3.5 -769.5 132
    #   -- Ahkk Jharcham, Whitegate , !pos 0.1 -1 -76 50
    #   -- Hadahda !pos -112 -7 -66 50
    #
    # Reading only the first cost 88 quests their NPC. The separator is a colon, a comma or
    # nothing at all, `!pos` may carry a colon of its own, and anything after a comma in the
    # name is the place in words -- "Ahkk Jharcham, Whitegate" is one NPC, not two.
    npc = None
    header_pos = re.compile(r"--\s*(.+?)\s*[,:]?\s*!pos:?\s+"
                            r"(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)")
    candidates = []
    for line in lines[:40]:
        m = header_pos.match(line)
        if m:
            candidates.append({
                'name': clean_npc_name(m.group(1)),
                'x': float(m.group(2)), 'y': float(m.group(3)), 'z': float(m.group(4)),
                'zone': int(m.group(5)),
            })
    # A quest often lists several positions -- the giver, the place it is turned in, a door on
    # the way. The first line is not reliably the giver: several name the town, or a door, and
    # one names "Region". The one whose name the server actually has an NPC for is.
    if candidates:
        npc = next((c for c in candidates if npc_list and
                    (c['zone'], re.sub(r'[^a-z0-9]', '', c['name'].lower())) in npc_list),
                   candidates[0])

    # A fourth dialect gives a position with no zone -- "-- Salimah : !pos -31.7 -6.8 -73.3" --
    # and a fifth gives a zone-less position with no name at all. Both are still usable: the
    # zone is in the script, in its own `xi.zone.X` references.
    script_zones = [zone_ids[z] for z in re.findall(r"xi\.zone\.([A-Z][A-Z0-9_]*)", text)
                    if zone_ids and z in zone_ids]
    if npc is None:
        for line in lines[:40]:
            m = re.match(r"--\s*(.*?)\s*[,:]?\s*!pos:?\s+"
                         r"(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*$", line)
            if m and script_zones:
                name = clean_npc_name(m.group(1))
                if name.lower() == title.lower():
                    name = ''
                # A script mentions several zones -- the one the quest is taken in is the one
                # that actually has this NPC standing in it. Guessing the first mentioned put
                # thirteen quests in the wrong zone.
                key = re.sub(r'[^a-z0-9]', '', name.lower())
                zone = next((z for z in script_zones
                             if npc_list and (z, key) in npc_list), script_zones[0])
                npc = {'name': name,
                       'x': float(m.group(2)), 'y': float(m.group(3)), 'z': float(m.group(4)),
                       'zone': zone}
                break

    # The other header style: the NPC named on its own, with the place in words rather than
    # coordinates -- "-- Dominion Sergeant (Nanaa Mihgo\'s Camp)". Every Abyssea dominion op
    # is written this way, which is why 160 quests came out of the generator with nobody to
    # talk to. The name is enough: the zone comes from the script\'s own `[xi.zone.X]` block
    # and the position from the server\'s npc_list.
    if npc is None and zone_ids and npc_list:
        zones = [zone_ids[z] for z in re.findall(r"xi\.zone\.([A-Z][A-Z0-9_]*)", text)
                 if z in zone_ids]
        header = []
        for line in lines[:12]:
            m = re.match(r"--\s*([A-Z][A-Za-z\'\- ]{2,40}?)\s*(?:\([^)]*\))?\s*$", line)
            if m and not m.group(1).strip().startswith('!'):
                header.append(m.group(1).strip())
        # The title line is a header comment too, and is not an NPC name.
        for name in [h for h in header if h.lower() != title.lower()]:
            key = re.sub(r'[^a-z0-9]', '', name.lower())
            for zone in zones:
                places = npc_list.get((zone, key))
                if places:
                    # There is no header coordinate to be nearest to here, so the first row
                    # is all there is to go on. Say so rather than implying a choice was made.
                    pos = places[0]
                    npc = {'name': name, 'x': pos[0], 'y': pos[1], 'z': pos[2], 'zone': zone}
                    break
            if npc:
                break

    # Last resort, and the most reliable of the lot when it fires: a quest's sections are keyed
    # by the NPC they belong to -- `[xi.zone.LOWER_JEUNO] = { ['Chalvatot'] = { onTrigger ...`.
    # A quest whose header says nothing at all still says this, and so does one whose header
    # names the town rather than the person ("Mhaura", "Chateau d'Oraguille") -- which reads as
    # an NPC the server has never heard of, and is really the parse missing the point.
    unresolved = (npc is not None and npc_list is not None and npc['name'] and
                  (npc['zone'], re.sub(r'[^a-z0-9]', '', npc['name'].lower())) not in npc_list)
    if (npc is None or unresolved) and zone_ids and npc_list:
        for m in re.finditer(r"\[\s*xi\.zone\.([A-Z][A-Z0-9_]*)\s*\]\s*=\s*\{(.{0,4000}?)\n\s*\}",
                             text, re.S):
            zone = zone_ids.get(m.group(1))
            if zone is None:
                continue
            for n in re.finditer(r"\[\s*'([^']{2,40})'\s*\]\s*=", m.group(2)):
                name = n.group(1)
                key = re.sub(r'[^a-z0-9]', '', name.lower())
                places = npc_list.get((zone, key)) or npc_list.by_internal.get((zone, key))
                if places:
                    # Nothing to be nearest to: the section key names the NPC and the script
                    # states no coordinate at all, so the first row is the only answer there
                    # is. Where several rows share the name this is a coin toss, and it says
                    # so here rather than pretending otherwise.
                    pos = places[0]
                    # The name the *client* shows, not the section key. This field is read
                    # out to the player ("Starts with ..."), and `_6s1` is not an instruction.
                    found = {'name': pos[3] or name, 'x': pos[0], 'y': pos[1], 'z': pos[2],
                             'zone': zone}
                    break
            else:
                continue
            break
        else:
            found = None
        if found:
            npc = found

    # The header comment and npc_list can disagree, and when they do the server wins: the
    # comment is prose somebody typed, npc_list is what the server actually spawns. Nine
    # quests are affected, one of them by 1540 yalms -- "An Eye for Revenge" has Curilla's z
    # written -769.5 where the server puts her at +770.2, a sign typed wrong once and copied
    # since. Disagreements under ten yalms are left alone; they are the same spot.
    if npc and npc_list and npc['name']:
        places = npc_list.get((npc['zone'], re.sub(r'[^a-z0-9]', '', npc['name'].lower())))
        # Of the rows that share the name in that zone, the nearest one. The comment is prose
        # somebody typed and npc_list is what the server spawns, so the server still wins the
        # position -- but "the server's row for this name" is a question with up to twenty
        # answers, and the right one is the one the comment was pointing at.
        if places:
            pos = min(places, key=lambda p: math.hypot(p[0] - npc['x'], p[2] - npc['z']))
            if math.hypot(pos[0] - npc['x'], pos[2] - npc['z']) > 10.0:
                npc = dict(npc, x=pos[0], y=pos[1], z=pos[2], from_server=True)

    if npc is not None:
        return npc

    # Nobody to talk to anywhere -- `allow_zone_only` decides whether that is worth a zone.
    # Missions want it: many begin by walking into a place rather than by talking to somebody.
    # Quests do not: a quest with no NPC and no coordinate is a quest with nothing to say, and
    # naming a zone the script happens to mention would be a guess dressed as a fact.
    # Nobody to talk to anywhere -- and for a whole class of missions that is the truth, not a
    # gap. A Crystalline Prophecy begins by *walking into* Lower Jeuno: the section is keyed
    # `[xi.zone.LOWER_JEUNO] = { onZoneIn = ... }` and names no NPC because none is involved.
    # "Go to Lower Jeuno" is still the instruction a guide should give, so the zone is kept
    # even though there is no coordinate to stand on. Twelve ACP missions and most of A
    # Shantotto Ascension are this shape.
    if not allow_zone_only:
        return None

    m = re.search(r"\[\s*xi\.zone\.([A-Z][A-Z0-9_]*)\s*\]\s*=", text)
    zone = (zone_ids or {}).get(m.group(1)) if m else None
    if zone:
        return {'name': '', 'zone': zone, 'x': None, 'y': None, 'z': None, 'zone_only': True}

    return None
