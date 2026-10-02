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
    # Table-style headers put the zone first: "Mhaura, Rycharde, !pos ...".
    for part in raw.split(',')[1:]:
        add(clean_npc_name(part))
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
        self.by_id = {}     # npcid -> (zone, row as in by_zone), for a header's `!gotoid`


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
            placed = (x, y, z, name, internal, bool(shown))
            out.by_zone.setdefault((npcid >> 12) & 0xFFF, []).append(placed)
            out.by_id[npcid] = ((npcid >> 12) & 0xFFF, placed)
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
    text = open(path, encoding='utf-8', errors='replace').read()
    for m in _AREA.finditer(text):
        kind, aid = m.group(1), int(m.group(2))
        n = [float(v) for v in re.findall(r'-?[\d.]+', m.group(3))]
        if kind == 'Cuboid' and len(n) == 6:
            out.setdefault(aid, ((n[0] + n[3]) / 2, (n[2] + n[5]) / 2, (n[1] + n[4]) / 2))
        elif kind == 'Cylindrical' and len(n) == 3:
            out.setdefault(aid, (n[0], n[1], None))
        elif kind == 'Spherical' and len(n) == 4:
            out.setdefault(aid, (n[0], n[2], n[1]))
    # Eastern Adoulin registers its areas through a local helper, a cube of half-width d
    # around (x, y, z): defineZoneAroundXYZ(zone, id, x, y, z, d).
    for m in re.finditer(r"defineZoneAroundXYZ\(\s*zone\s*,\s*(\d+)\s*,\s*(-?[\d.]+)\s*,"
                         r"\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,", text):
        out.setdefault(int(m.group(1)), (float(m.group(2)), float(m.group(4)),
                                         float(m.group(3))))
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


# --------------------------------------------------------------------------------------------
# Where a quest or mission starts. Used by gen_missions.py and gen_quests.py.
# --------------------------------------------------------------------------------------------

class Server:
    """The parts of a checkout a start is looked up in: zone ids, npc_list, and each zone's
    trigger areas (read on first use)."""

    def __init__(self, root):
        self.zone_ids = parse_zone_ids(root)
        self.zone_enum = {v: k for k, v in self.zone_ids.items()}
        self.npcs = parse_npc_list(root)
        self.dirs = zone_dirs(root, self.zone_ids)
        self._areas = {}

    def areas(self, zone):
        if zone not in self._areas:
            self._areas[zone] = trigger_areas(self.dirs.get(zone))
        return self._areas[zone]

    def script_zones(self, text):
        """Every zone a script mentions, in the order it first mentions them."""
        out = []
        for enum in re.findall(r"xi\.zone\.([A-Z][A-Z0-9_]*)", text):
            z = self.zone_ids.get(enum)
            if z is not None and z not in out:
                out.append(z)
        return out


# Header dialects. "-- Name : !pos x y z zone", and every variation on it that the scripts use:
# a comma, an equals sign or nothing for the colon ("-- Hadahda !pos ...", "-- Milazahn =
# !pos ..."), "!pos:", commas between the numbers, no zone ("-- Salimah : !pos -31.7 -6.8
# -73.3"), no name ("-- !pos 200.3 -2.25 37.1 168"), no "!pos" at all ("-- Unlucky Rat :
# -59.724 1.999 30.179 237"), an npc id instead of a position ("-- Raibaht : !gotoid
# 17748012"), and a whole zone instead of a position ("-- Norg : !zone 252", "-- !zone 50 =
# Whitegate"), which also says where the zone-less lines after it are.
_HEADER_POS = re.compile(r"--\s*(.*?)\s*[,:=]?\s*!pos:?\s+(-?[\d.]+),?\s+(-?[\d.]+),?\s+"
                         r"(-?[\d.]+)(?:,?\s+(\d+))?(?:\s.*)?$")
_HEADER_BARE = re.compile(r"--\s*([A-Za-z][^:!]*?)\s*:\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)"
                          r"\s+(-?\d+(?:\.\d+)?)\s+(\d+)\s*$")
_HEADER_GOTO = re.compile(r"--\s*(.*?)\s*[-:]?\s*!gotoid\s+(\d+)")
_HEADER_ZONE = re.compile(r"--\s*(.*?)\s*[:=]?\s*!zone\s+(\d+)(?:\s*=\s*(.*))?\s*$")
_HEADER_NAME = re.compile(r"--\s*([A-Z][A-Za-z'\- ]{2,40}?)\s*(?:\(([^)]*)\))?\s*$")


def header_places(text, lines, server, near=8.0):
    """Every positioned line of a script's header, in order, each read against the server:
    [{'label', 'zone', 'x', 'y', 'z', 'hit'}], `hit` being resolve_label()'s answer or None.

    `zone` is None when it cannot be told. It is the line's own, or -- for a line without
    one -- the zone of a `!zone` line above it or of the script, whichever has the labelled
    thing standing within `near` yalms of the coordinate. A line's own zone can be
    wrong ("Ornate Door (_521) : !pos -700 -20.25 -303.398 89", where the door is in the Walk
    of Echoes): another zone the script works in, with the labelled thing at the very same
    coordinate, is the zone it meant.
    """
    sections = script_sections(text)
    zones = server.script_zones(text)

    def keys(zone):
        return section_keys(sections, server.zone_enum.get(zone))

    out, context = [], None
    for raw in lines[:40]:
        line = raw.strip()
        if not line.startswith('--'):
            continue
        mz = _HEADER_ZONE.match(line)
        if mz and '!pos' not in line:
            context = int(mz.group(2))
            continue
        mg = _HEADER_GOTO.match(line)
        if mg:
            ent = server.npcs.by_id.get(int(mg.group(2)))
            if ent is not None:
                zone, r = ent
                out.append({'label': mg.group(1), 'zone': zone, 'x': r[0], 'y': r[1], 'z': r[2],
                            'hit': {'name': r[3], 'x': r[0], 'y': r[1], 'z': r[2],
                                    'shown': r[5], 'how': 'id', 'dist': 0.0}})
            continue
        m = _HEADER_POS.match(line) or _HEADER_BARE.match(line)
        if not m:
            continue
        label = m.group(1).strip()
        x, y, z = float(m.group(2)), float(m.group(3)), float(m.group(4))
        zone = int(m.group(5)) if m.group(5) else None
        hit = None
        if zone is not None:
            hit = resolve_label(label, zone, x, z, server.npcs, keys(zone), near)
            if hit is None:
                for other in zones:
                    if other == zone:
                        continue
                    cand = resolve_label(label, other, x, z, server.npcs, keys(other), near=1.5)
                    if cand is not None and cand['dist'] <= 1.5:
                        zone, hit = other, cand
                        break
        else:
            for other in ([context] if context is not None else []) + zones:
                cand = resolve_label(label, other, x, z, server.npcs, keys(other), near)
                if cand is not None and cand['dist'] <= near:
                    zone, hit = other, cand
                    break
            if zone is None:
                zone = context
        # Kept even when the zone cannot be told: it is still the header's first line, and a
        # quest whose first line cannot be placed asks the script instead of the second line.
        out.append({'label': label, 'zone': zone, 'x': x, 'y': y, 'z': z, 'hit': hit})
    return out


GENERIC_PLACE_LABELS = {'region', 'area', 'triggerarea', 'zone', 'here'}


def start_from_header(place):
    """A header_places() entry as a start: {'zone', 'x', 'y', 'z', 'npc', 'place'}.

    Whatever the server has standing there is the NPC, by the name the client shows; past five
    yalms from the comment's coordinate, the server's row is where the marker goes (the comment
    is prose somebody typed; npc_list is what the server spawns). A label nothing answers to is
    a place -- "1. Enter Lower Delkfutt", "Port Bastok HP" -- and is kept as one rather than
    presented as somebody to talk to.
    """
    hit, label = place['hit'], place['label']
    start = {'zone': place['zone'], 'x': place['x'], 'y': place['y'], 'z': place['z'],
             'npc': None, 'place': None}
    if hit is None:
        if label and not label.startswith('!'):
            name = clean_npc_name(label) or None
            # "Region" (a trigger area's label) is not a place anyone can find by name.
            if name and normalize(name) not in GENERIC_PLACE_LABELS:
                start['place'] = name
        return start
    if hit['shown']:
        start['npc'] = hit['name']
    if hit['dist'] > 5.0:
        start.update(x=hit['x'], y=hit['y'], z=hit['z'])
    return start


def header_zone(lines):
    """The first `!zone` header line's zone: "-- Norg : !zone 252"."""
    for raw in lines[:40]:
        m = _HEADER_ZONE.match(raw.strip())
        if m and '!pos' not in raw:
            return int(m.group(2))
    return None


def header_named(text, lines, title, server):
    """A header that names the NPC with no coordinate at all -- "-- Dominion Sergeant (Nanaa
    Mihgo's Camp)" -- as a start, or None.

    The zone is one the script works in where the server has an NPC of that name. Several
    rows of the name at different spots are told apart by the bracket: npc_list calls the
    sergeant of Nanaa Mihgo's camp `DSgt_Nanaa`. If the bracket does not pick exactly one, the
    answer is none rather than the first row: three sergeants stand in Abyssea - Altepa, and
    taking the first sent two quests out of three to the wrong camp.
    """
    for raw in lines[:12]:
        m = _HEADER_NAME.match(raw.strip())
        if not m or m.group(1).strip().lower() == title.lower():
            continue
        name, hint = m.group(1).strip(), m.group(2) or ''
        key = normalize(name)
        for zone in server.script_zones(text):
            rows = [r for r in server.npcs.by_zone.get(zone, []) if normalize(r[3]) == key]
            if len({(round(r[0]), round(r[2])) for r in rows}) > 1:
                words = [normalize(w) for w in re.findall(r"[A-Za-z]{4,}", hint)]
                rows = [r for r in rows if any(w in normalize(r[4]) for w in words)]
            if len({(round(r[0]), round(r[2])) for r in rows}) == 1:
                r = rows[0]
                return {'zone': zone, 'x': r[0], 'y': r[1], 'z': r[2],
                        'npc': r[3] if r[5] else None, 'place': None}
    return None


# What moves a quest or mission along, as opposed to what only talks about it:
# `mission:event(...)` is dialogue with no consequence, and a line of it is where nearly every
# giver says "come back later". A handler that does none of these is not where anything starts.
_PROGRESS = re.compile(r"progressEvent\s*\(|startEvent\s*\(|startCutscene\s*\(|"
                       r"(?:mission|quest):(?:complete|begin)\s*\(|setMissionStatus|"
                       r"\breturn\s+\d+|\breturn\s*\{\s*\d+")
# A stage past the first: `missionStatus == 2`, `getVar(player, 'Status') >= 1`,
# `mission:getVar(player, 'Retrieve') == 1`, `vars.Prog == 1` ...
_STAGE = re.compile(r"(missionStatus|getMissionStatus\([^)]*\)|"
                    r"getVar\(\s*player\s*,\s*'\w+'\s*\)|vars\.\w+)\s*(==|>=|>)\s*(\d+)")


def later_stage(text):
    """True when `text` only lets a later stage through."""
    first = later = False
    for m in _STAGE.finditer(text):
        op, n = m.group(2), int(m.group(3))
        if op == '==' and n == 0:
            first = True
        elif op == '>' or n >= 1:
            later = True
    return later and not first


def _opening(check, kind):
    """Is this section the quest or mission before anything has happened in it?"""
    if kind == 'quest':
        # "Available", or no status condition at all (Community Service's one section serves
        # every status, `vars.Prog >= 0`).
        return (('QUEST_AVAILABLE' in check or 'questStatus' not in check) and
                not later_stage(check))
    return ('hasCompleted' not in check and
            re.search(r"currentMission\s*==\s*mission\.missionId", check) is not None and
            not later_stage(check))


def script_start(text, server, kind='mission'):
    """Where a mission (or quest) starts, read from its sections when the header gives no
    position: {'kind': 'npc'|'area'|'zone', 'zone', ...} or None.

    The first section that is the mission in progress (the quest still available), not a later
    stage, is searched in the order the script lists things for the first handler that moves it
    along: an NPC to talk to, a trigger area to walk into, a zone to enter. Two such handlers in
    different zones at the head of the list -- "zone into Mhaura or Selbina" -- are a choice
    the player makes, not a place, and give no answer.
    """
    found = []
    for check, zones in script_sections(text):
        if not _opening(check, kind):
            continue
        for enum, entries in zones:
            zone = server.zone_ids.get(enum)
            if zone is None:
                continue
            # Events this zone block finishes or updates. `mission:event(71)` is only dialogue
            # -- unless the block's onEventFinish does something when 71 ends, and then it is
            # the mission moving on (A Shantotto Ascension's zone-in cutscenes are all this).
            handled = {int(n) for key, body in entries if key in ('onEventFinish', 'onEventUpdate')
                       for n in re.findall(r"\[\s*(\d+)\s*\]\s*=", body)}
            for key, body in entries:
                if key in ('onEventFinish', 'onEventUpdate', 'onMobDeath', 'onTrade'):
                    continue
                m = _PROGRESS.search(body)
                ev = next((e for e in re.finditer(r"(?:mission|quest):event\s*\(\s*(\d+)", body)
                           if int(e.group(1)) in handled), None)
                if m is None or (ev is not None and ev.start() < m.start()):
                    m = ev
                if m is None or later_stage(body[:m.start()]):
                    continue
                if key == 'onZoneIn':
                    # "Enter X from Y" only when Y is the one way in; a choice of ways is no
                    # instruction.
                    came = set(re.findall(r"prevZone\s*==\s*xi\.zone\.([A-Z0-9_]+)", body))
                    found.append({'kind': 'zone', 'zone': zone,
                                  'from': server.zone_ids.get(came.pop()) if len(came) == 1
                                  else None})
                elif key == 'onTriggerAreaEnter':
                    areas = server.areas(zone)
                    spot = next((areas[int(a)] for a in re.findall(r"\[\s*(\d+)\s*\]\s*=", body)
                                 if int(a) in areas), None)
                    if spot is not None:
                        found.append({'kind': 'area', 'zone': zone,
                                      'x': spot[0], 'z': spot[1], 'y': spot[2]})
                elif not key.startswith('on'):
                    n = normalize(key)
                    rows = [r for r in server.npcs.by_zone.get(zone, [])
                            if n in (normalize(r[3]), normalize(r[4]))]
                    if rows:
                        r = rows[0]
                        found.append({'kind': 'npc', 'zone': zone, 'x': r[0], 'y': r[1],
                                      'z': r[2], 'name': r[3], 'shown': r[5],
                                      'places': {(round(p[0]), round(p[2])) for p in rows}})
        if found:
            break
    if not found:
        return None
    head = found[0]
    if len(found) > 1 and found[1]['kind'] == head['kind'] and found[1]['zone'] != head['zone']:
        return None
    if head['kind'] == 'npc' and len(head['places']) > 1:
        return None     # the same name standing in two places: which one is not said
    return head


def start_from_script(found):
    """A script_start() answer as a start: {'zone', 'x', 'y', 'z', 'npc', 'place', 'from'}."""
    start = {'zone': found['zone'], 'x': found.get('x'), 'y': found.get('y'),
             'z': found.get('z'), 'npc': None, 'place': None, 'from': found.get('from')}
    if found['kind'] == 'npc' and found['shown']:
        start['npc'] = found['name']
    return start


def find_npc(text, lines, title, zone_ids, npc_list, allow_zone_only=False):
    """Who to talk to, and where they stand, from a quest or mission script.

    Superseded by header_places() / header_named() / script_start() above, which the
    generators use; kept for its notes on the header dialects.

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
