#!/usr/bin/env python3
"""Vanaguide :: tools/gen_missions.py

Build the mission database from LandSandBoat's server scripts — the same argument as
tools/gen_quests.py (see docs/QUEST_DATABASE.md), applied to scripts/missions/.

Mission ids matter more than quest ids, because missions are linear: a step waits on
"the current mission number is past this one", so an id that is off by one waits forever
or completes early.  Reading them out of the server's own enum is the only way to be sure.

    tools/gen_missions.py <path to a LandSandBoat checkout> [-o Vanaguide/data/missions.lua]

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lsbdata  # noqa: E402

# LandSandBoat's log names -> the names core/story.lua uses for packet 0x056 areas.
AREA_LOG = {
    'sandoria': 'sandoria', 'bastok': 'bastok', 'windurst': 'windurst',
    'zilart': 'zilart', 'cop': 'cop', 'toau': 'toau', 'wotg': 'wotg',
    'acp': 'acp', 'amk': 'amk', 'asa': 'asa', 'soa': 'adoulin', 'rov': 'rov',
    'tvr': 'tvr', 'assault': 'assault', 'campaign': 'campaign',
}


def parse_ids(root):
    """scripts/globals/missions.lua -> {area: {CONST: id}}"""
    text = open(os.path.join(root, 'scripts/globals/missions.lua'), encoding='utf-8').read()
    out, area = defaultdict(dict), None
    for line in text.splitlines():
        m = re.search(r"\[xi\.mission\.area\[xi\.mission\.log_id\.(\w+)\]\]", line)
        if m:
            area = m.group(1).lower()
            continue
        m = re.search(r"\['(\w+)'\]\s*=$", line)
        if m:
            area = m.group(1).lower()
            continue
        m = re.match(r"\s*([A-Z][A-Z0-9_]+)\s*=\s*(\d+)", line)
        if m and area:
            out[area][m.group(1)] = int(m.group(2))
    return out


class Server:
    """The parts of the checkout the start of a mission is looked up in: zone ids, npc_list,
    and each zone's trigger areas (read on first use)."""

    def __init__(self, root):
        self.zone_ids = lsbdata.parse_zone_ids(root)
        self.npcs = lsbdata.parse_npc_list(root)
        self.dirs = lsbdata.zone_dirs(root, self.zone_ids)
        self._areas = {}

    def areas(self, zone):
        if zone not in self._areas:
            self._areas[zone] = lsbdata.trigger_areas(self.dirs.get(zone))
        return self._areas[zone]


# Header lines: "-- Name : !pos x y z zone". The name is sometimes absent ("-- !pos x y z zone"),
# the zone sometimes absent ("-- Jugner Forest (S) : !pos x y z"), and "!zone N" stands in for a
# position when the place is a whole zone ("-- Norg : !zone 252").
_HEADER_POS = re.compile(r"--\s*(.*?)\s*[,:]?\s*!pos:?\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)"
                         r"(?:\s+(\d+))?(?:\s.*)?$")
_HEADER_ZONE = re.compile(r"--\s*(.+?)\s*:\s*!zone\s+(\d+)\s*$")

# What moves a mission along, as opposed to what only talks about it: `mission:event(...)` is
# dialogue with no consequence, and a line of it is where nearly every mission's giver says
# "come back later". A handler that does none of these is not where a mission starts.
_PROGRESS = re.compile(r"progressEvent\s*\(|startEvent\s*\(|startCutscene\s*\(|"
                       r"mission:complete\s*\(|mission:begin\s*\(|setMissionStatus|"
                       r"\breturn\s+\d+")
# A stage past the first: `missionStatus == 2`, `getVar(player, 'Status') >= 1`,
# `mission:getVar(player, 'Retrieve') == 1`, `vars.Status == 1` ...
_STAGE = re.compile(r"(missionStatus|getMissionStatus\([^)]*\)|"
                    r"getVar\(\s*player\s*,\s*'\w+'\s*\)|vars\.\w+)\s*(==|>=|>)\s*(\d+)")


def _later_stage(text):
    """True when `text` only lets a later stage of the mission through."""
    first = later = False
    for m in _STAGE.finditer(text):
        op, n = m.group(2), int(m.group(3))
        if op == '==' and n == 0:
            first = True
        elif op == '>' or n >= 1:
            later = True
    return later and not first


def script_start(text, server):
    """Where the mission starts, read from its sections when the header gives no position.

    The first section that is the mission in progress (not "already finished", not a later
    stage) is searched in the order the script lists things, for the first handler that
    moves the mission along: an NPC to talk to, a trigger area to walk into, a zone to enter.
    Two such handlers in different zones at the head of the list -- the seven Cermet
    Headstones, "zone into Mhaura or Selbina" -- are a choice the player makes, not a place,
    and give no answer.
    """
    found = []
    for check, zones in lsbdata.script_sections(text):
        if 'hasCompleted' in check or not re.search(r"currentMission\s*==\s*mission\.missionId",
                                                    check):
            continue
        if _later_stage(check):
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
                ev = next((e for e in re.finditer(r"mission:event\s*\(\s*(\d+)", body)
                           if int(e.group(1)) in handled), None)
                if m is None or (ev is not None and ev.start() < m.start()):
                    m = ev
                if m is None or _later_stage(body[:m.start()]):
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
                    n = lsbdata.normalize(key)
                    rows = [r for r in server.npcs.by_zone.get(zone, [])
                            if n in (lsbdata.normalize(r[3]), lsbdata.normalize(r[4]))]
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


def mission_start(text, lines, title, server):
    """Where the mission starts: {'zone', 'x', 'y', 'z', 'npc', 'place', 'from'} or None.

    The header's first positioned line, as it has always been -- mission headers list places
    in the order the mission visits them -- but with its label read for what it is. The label
    is the NPC's name only some of the time: it is also a door with its internal name
    ("Granite Door (_4fx)"), the zone the NPC is in ("Batallia Downs"), a home point ("Port
    Bastok HP"), a step of instructions ("1. Enter Lower Delkfutt"), or the NPC's name misspelt
    ("Nashib"). Whatever the server has standing there is the NPC; a label nothing answers to
    is a place, and is kept as one rather than presented as somebody to talk to.
    """
    sections = None

    def keys(enum_zone):
        nonlocal sections
        if sections is None:
            sections = lsbdata.script_sections(text)
        enum = next((e for e, z in server.zone_ids.items() if z == enum_zone), None)
        return lsbdata.section_keys(sections, enum)

    script_zones = []
    for enum in re.findall(r"xi\.zone\.([A-Z][A-Z0-9_]*)", text):
        z = server.zone_ids.get(enum)
        if z is not None and z not in script_zones:
            script_zones.append(z)

    for line in lines[:40]:
        m = _HEADER_POS.match(line.strip())
        if not m:
            continue
        label = m.group(1).strip()
        x, y, z = float(m.group(2)), float(m.group(3)), float(m.group(4))
        zone = int(m.group(5)) if m.group(5) else None
        hit = None
        if zone is not None:
            hit = lsbdata.resolve_label(label, zone, x, z, server.npcs, keys(zone))
        if hit is None:
            # A header can give the wrong zone ("Ornate Door (_521) ... 89", where the door is
            # in the Walk of Echoes) or none at all. Another zone the script works in, with the
            # labelled thing standing at the very same coordinate, is the zone it meant.
            for other in script_zones:
                if other == zone:
                    continue
                cand = lsbdata.resolve_label(label, other, x, z, server.npcs, keys(other),
                                             near=1.5)
                if cand is not None and cand['dist'] <= 1.5:
                    zone, hit = other, cand
                    break
        if zone is None:
            continue
        place = lsbdata.clean_npc_name(label) if label and not label.startswith('!') else None
        start = {'zone': zone, 'x': x, 'y': y, 'z': z, 'npc': None, 'place': place}
        if hit is not None:
            start['place'] = None
            if hit['shown']:
                start['npc'] = hit['name']
            # The comment is prose somebody typed; npc_list is what the server spawns. Past
            # five yalms they are not the same spot, and the marker goes where the NPC is.
            if hit['dist'] > 5.0:
                start.update(x=hit['x'], y=hit['y'], z=hit['z'])
        return start

    found = script_start(text, server)
    if found is None:
        for line in lines[:40]:
            m = _HEADER_ZONE.match(line.strip())
            if m:
                found = {'kind': 'zone', 'zone': int(m.group(2)), 'from': None}
                break
    if found is None:
        return None
    start = {'zone': found['zone'], 'x': found.get('x'), 'y': found.get('y'),
             'z': found.get('z'), 'npc': None, 'place': None, 'from': found.get('from')}
    if found['kind'] == 'npc' and found['shown']:
        start['npc'] = found['name']
    return start


def parse_mission(path, ids, server=None):
    text = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r"Mission:new\(\s*xi\.mission\.log_id\.(\w+)\s*,\s*xi\.mission\.id\.(\w+)\.([A-Z0-9_]+)", text)
    if not m:
        return None
    log_area, id_area, const = m.groups()
    area = AREA_LOG.get(id_area.lower(), id_area.lower())
    mid = ids.get(id_area.lower(), {}).get(const)
    if mid is None:
        mid = ids.get('nation', {}).get(const)
    if mid is None:
        return None

    lines = text.splitlines()
    title = lines[1].lstrip('- ').strip() if len(lines) > 1 else const.title()
    label = None
    if len(lines) > 2:
        # "-- San d'Oria M1-1" on the line under the title, where the file has one.
        m2 = re.match(r"--\s*(.*M\d+-\d+.*)$", lines[2].strip())
        if m2:
            label = m2.group(1).strip()

    start = mission_start(text, lines, title, server) if server is not None else None
    return {'area': area, 'id': mid, 'name': title, 'label': label, 'npc': start}


def lua_str(s):
    return "'" + str(s).replace('\\', '\\\\').replace("'", "\\'") + "'"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('-o', '--out', default='Vanaguide/data/missions.lua')
    args = ap.parse_args()

    ids = parse_ids(args.root)
    server = Server(args.root)
    missions, skipped = defaultdict(dict), 0

    def rank(m):
        s = m['npc']
        return 0 if s is None else (1 if s.get('x') is None else 2)

    for dirpath, dirnames, files in os.walk(os.path.join(args.root, 'scripts/missions')):
        dirnames.sort()
        for f in sorted(files):
            if not f.endswith('.lua'):
                continue
            m = parse_mission(os.path.join(dirpath, f), ids, server)
            if m is None:
                skipped += 1
                continue
            # A mission implemented in several files (first visit / repeat) keeps the entry
            # that says the most about where it starts.
            have = missions[m['area']].get(m['id'])
            if have is None or rank(m) > rank(have):
                missions[m['area']][m['id']] = m

    total = sum(len(v) for v in missions.values())
    positioned = sum(1 for a in missions.values() for m in a.values() if rank(m) == 2)
    zoned = sum(1 for a in missions.values() for m in a.values() if rank(m) == 1)

    with open(args.out, 'w', encoding='utf-8') as fh:
        fh.write("""-- Vanaguide :: data/missions.lua
-- GENERATED by tools/gen_missions.py from a LandSandBoat checkout.  Do not hand-edit.
--
-- Mission ids keyed the way packet 0x056 keys them, so `M|area,id|` in a guide and this
-- table are the same numbers.  Missions are linear: `M` waits for the current mission
-- number to pass the id, which is why these are generated rather than remembered.
--
-- Where it starts, when the script says:
--   zone    the zone, and x/z/y there (x/z/y nil when starting means entering the zone)
--   npc     who to talk to, by the name the client shows
--   place   what the script calls the spot, when nobody stands there to talk to
--   from    the zone to enter it from, when that matters
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local M = {}

""")
        fh.write('M.missions = {\n')
        for area in sorted(missions):
            fh.write('    %s = {\n' % area)
            for mid in sorted(missions[area]):
                m = missions[area][mid]
                bits = ['name = %s' % lua_str(m['name'])]
                if m['label']:
                    bits.append('label = %s' % lua_str(m['label']))
                if m['npc']:
                    n = m['npc']
                    bits.append('zone = %d' % n['zone'])
                    if n.get('x') is not None:
                        bits += ['x = %.1f' % n['x'], 'z = %.1f' % n['z']]
                        if n.get('y') is not None:
                            bits.append('y = %.1f' % n['y'])
                    if n.get('npc'):
                        bits.append('npc = %s' % lua_str(n['npc']))
                    if n.get('place'):
                        bits.append('place = %s' % lua_str(n['place']))
                    if n.get('from'):
                        bits.append('from = %d' % n['from'])
                fh.write('        [%d] = { %s },\n' % (mid, ', '.join(bits)))
            fh.write('    },\n')
        fh.write('}\n\n')
        fh.write("""function M.get(area, id)
    local a = M.missions[area]
    return a ~= nil and a[id] or nil
end

function M.area(area)
    local out = {}
    for id, m in pairs(M.missions[area] or {}) do out[#out + 1] = { id = id, mission = m } end
    table.sort(out, function(a, b) return a.id < b.id end)
    return out
end

return M
""")

    print('%d missions in %d storylines (%d with coordinates, %d with a zone only); '
          '%d files skipped' % (total, len(missions), positioned, zoned, skipped))


if __name__ == '__main__':
    sys.exit(main())
