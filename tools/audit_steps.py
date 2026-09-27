#!/usr/bin/env python3
"""Vanaguide :: tools/audit_steps.py

Verify every step of every guide in a running client on the LOCAL world.

For each step (tools/export_steps.lua writes the list): jump the guide to it, teleport the
character onto its marker (or into its zone), and have the addon write one row to
addons/Vanaguide/audit.csv (`/vg audit`): what the arrow says from here, whether the step's
NPC is loaded, whether its condition reads as done, and what the ground line is built from.
Then satisfy the step with the GM command a server would answer for (complete the quest or
mission, add the key item or item, set the level) and audit again, so the row pair proves the
guide notices the server's word.

Never point this at a hosted server: it teleports and sends GM commands.

    tools/audit_steps.py --game "<game dir>" --steps results/steps.jsonl [--guide N] [--limit N]

Resumable: steps with a 'pre' row in audit.csv are skipped.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import json
import os
import sys
import time

QUEST_LOG = {'sandoria': 'SANDORIA', 'bastok': 'BASTOK', 'windurst': 'WINDURST', 'jeuno': 'JEUNO',
             'other': 'OTHER_AREAS', 'outlands': 'OUTLANDS', 'ahturhgan': 'AHT_URHGAN',
             'wotg': 'CRYSTAL_WAR', 'abyssea': 'ABYSSEA', 'adoulin': 'ADOULIN', 'coalition': 'COALITION'}
MISSION_LOG = {'sandoria': 'SANDORIA', 'bastok': 'BASTOK', 'windurst': 'WINDURST', 'zilart': 'ZILART',
               'cop': 'COP', 'toau': 'TOAU', 'wotg': 'WOTG', 'acp': 'ACP', 'amk': 'AMK', 'asa': 'ASA',
               'adoulin': 'SOA', 'rov': 'ROV', 'tvr': 'TVR'}

# How LandSandBoat records a finished mission (src/map/lua/lua_base_entity.cpp completeMission,
# src/map/utils/charutils.cpp SendPartialMissionLog):
#  * `!completemission L X` does nothing unless X is L's *current* mission -- it only logs
#    "can't complete non current mission".  So every completion is `!addmission` first.
#  * Nations, Zilart, ToAU and WoTG then get a completed bit, which the client is sent.
#  * CoP gets no bit at all, and ACP/AMK/ASA/SoA/RoV get none the client is ever sent: for
#    these the only record is the current number, which completeMission resets to 0.  The
#    mission scripts finish them with completeMission + addMission(nextMission)
#    (scripts/globals/npc_util.lua), and LandSandBoat's own hasCompletedMission(COP, X) is
#    `X < current` -- so the harness has to move current past X the same way.
#  * TVR is sent nowhere (0x056_mission_tvr.cpp is a stub): no command can make it visible.
CURRENT_ONLY = {'cop', 'acp', 'amk', 'asa', 'adoulin', 'rov'}
NOT_SENT = {'tvr'}


def next_mission(steps):
    """(area, id) -> the next higher mission id any exported step uses in that area."""
    ids = {}
    for s in steps:
        if s.get('cond') in ('M', 'MA') and s.get('area') in MISSION_LOG and s.get('id') is not None:
            ids.setdefault(s['area'], set()).add(s['id'])
    out = {}
    for area, have in ids.items():
        ordered = sorted(have)
        for a, b in zip(ordered, ordered[1:]):
            out[(area, a)] = b
    return out


def gm_for(s, nxt=None):
    """The GM commands, in order, that make the step's condition true the way the server would."""
    c, area, i = s['cond'], s.get('area'), s.get('id')
    if c == 'Q' and area in QUEST_LOG: return [f'!completequest {QUEST_LOG[area]} {i}']
    if c == 'QA' and area in QUEST_LOG: return [f'!addquest {QUEST_LOG[area]} {i}']
    if c == 'M' and area in MISSION_LOG and area not in NOT_SENT:
        log = MISSION_LOG[area]
        cmds = [f'!addmission {log} {i}', f'!completemission {log} {i}']
        if area in CURRENT_ONLY:
            cmds.append(f'!addmission {log} {(nxt or {}).get((area, i), i + 1)}')
        return cmds
    if c == 'MA' and area in MISSION_LOG: return [f'!addmission {MISSION_LOG[area]} {i}']
    if c == 'KI' and s.get('ki') is not None: return [f'!addkeyitem {s["ki"]}']
    if c == 'IT' and s.get('item') is not None: return [f'!additem {s["item"]} {s.get("item_n") or 1}']
    if c == 'LV' and s.get('level'): return [f'!setplayerlevel {s["level"]}']
    return []


def clear_for(s):
    """Undo the step's condition first, so the 'pre' row can show it open."""
    c, area, i = s['cond'], s.get('area'), s.get('id')
    if c in ('Q', 'QA') and area in QUEST_LOG: return [f'!delquest {QUEST_LOG[area]} {i}']
    # `M`: clear the bit, then make X the current mission -- open for every log, since a
    # current number already past X would read as done.
    if c == 'M' and area in MISSION_LOG and area not in NOT_SENT:
        log = MISSION_LOG[area]
        return [f'!delmission {log} {i}', f'!addmission {log} {i}']
    if c == 'MA' and area in MISSION_LOG: return [f'!delmission {MISSION_LOG[area]} {i}']
    if c == 'KI' and s.get('ki') is not None: return [f'!delkeyitem {s["ki"]}']
    return []


def last_row(csv):
    with open(csv, encoding='utf-8', errors='replace') as fh:
        rows = fh.read().strip().splitlines()
    return rows[-1] if rows else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', required=True)
    ap.add_argument('--steps', required=True)
    ap.add_argument('--guide', type=int, default=0)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--zone-wait', type=float, default=20.0)
    ap.add_argument('--step-wait', type=float, default=4.0)
    ap.add_argument('--skip-zones', default='178')
    args = ap.parse_args()

    addon = os.path.join(args.game, 'addons', 'Vanaguide')
    cmd = os.path.join(addon, 'cmd.txt')
    csv = os.path.join(addon, 'audit.csv')
    skipz = {int(z) for z in args.skip_zones.split(',') if z.strip().isdigit()}

    def send(line):
        with open(cmd, 'a') as fh:
            fh.write(line + '\n')

    def consumed(timeout=15.0):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if os.path.getsize(cmd) == 0:
                    return True
            except OSError:
                return True
            time.sleep(0.25)
        return False

    def row_after(before, timeout=10.0):
        end = time.time() + timeout
        while time.time() < end:
            if os.path.exists(csv) and os.path.getsize(csv) > before:
                return True
            time.sleep(0.25)
        return False

    steps = [json.loads(l) for l in open(args.steps)]
    nxt = next_mission(steps)
    if args.guide:
        steps = [s for s in steps if s['guide'] == args.guide]
    done = set()
    if os.path.exists(csv):
        for line in open(csv, encoding='utf-8', errors='replace'):
            b = line.split(',')
            if len(b) > 5 and b[2] == 'pre' and (b[4] == '' or b[4] == b[5]):
                done.add((b[0], b[1]))
    todo = [s for s in steps if (str(s['guide']), str(s['step'])) not in done]
    # Zone order: a zone load costs ~20 s and there are far fewer zones than steps.
    todo.sort(key=lambda s: (s.get('zone') is None, s.get('zone') or 0, s['guide'], s['step']))
    if args.limit:
        todo = todo[:args.limit]
    print(f'{len(steps)} steps, {len(todo)} left to audit', flush=True)

    zone = None
    silent = 0
    stuck = 0
    for n, s in enumerate(todo, 1):
        g, i = s['guide'], s['step']
        if s.get('zone') in skipz:
            print(f'   {g}/{i} skipped: zone {s["zone"]} is on the skip list', flush=True)
            continue
        for line in clear_for(s):
            send(line)
            consumed()
        send(f'/vg audit {g} {i} jump')
        if not consumed():
            print('!! the client stopped reading cmd.txt -- stopping', flush=True)
            break
        def move(force_zone=False):
            nonlocal zone
            if s.get('zone') is None:
                time.sleep(1.0)
                return
            # A cross-zone `!pos` is sometimes refused (the character stays put and every later
            # row is taken from the wrong zone); `!zone` is not. So change zone first.
            if s['zone'] != zone or force_zone:
                send(f'!zone {s["zone"]}')
                consumed()
                time.sleep(args.zone_wait)
                zone = s['zone']
            if s.get('x') is not None:
                y = s.get('db_y') or 0
                send(f'!pos {s["x"]:.3f} {y:.3f} {s["z"]:.3f} {s["zone"]}')
                consumed()
            time.sleep(args.step_wait)

        move()
        before = os.path.getsize(csv) if os.path.exists(csv) else 0
        send(f'/vg audit {g} {i}')
        consumed()
        if not row_after(before):
            silent += 1
            print(f'   {g}/{i}: no audit row', flush=True)
            if silent >= 8:
                print('!! eight silent audits in a row -- stopping', flush=True)
                break
            continue
        silent = 0
        b = last_row(csv).split(',')
        if s.get('zone') is not None and len(b) > 5 and b[5] != str(s['zone']):
            # A zone load can outlast the wait: look again before moving again.
            time.sleep(10.0)
            before = os.path.getsize(csv)
            send(f'/vg audit {g} {i}')
            consumed()
            row_after(before)
            b = last_row(csv).split(',')
        if s.get('zone') is not None and len(b) > 5 and b[5] != str(s['zone']):
            print(f'   {g}/{i}: in zone {b[5]}, wanted {s["zone"]} -- retrying the move', flush=True)
            zone = None
            move(force_zone=True)
            before = os.path.getsize(csv)
            send(f'/vg audit {g} {i}')
            consumed()
            row_after(before)
            b = last_row(csv).split(',')
            if len(b) > 5 and b[5] != str(s['zone']):
                stuck += 1
                zone = None
                print(f'   {g}/{i}: still in zone {b[5]} -- skipped', flush=True)
                if stuck >= 5:
                    print('!! five moves in a row did not take -- the character is wedged, stopping', flush=True)
                    break
                continue
        stuck = 0
        for _ in range(3):
            if 'nothing loaded yet' not in last_row(csv):
                break
            time.sleep(6.0)
            before = os.path.getsize(csv)
            send(f'/vg audit {g} {i}')
            consumed()
            row_after(before)
        gm = gm_for(s, nxt)
        if gm:
            for line in gm:
                send(line)
                consumed()
            time.sleep(3.0)
            before = os.path.getsize(csv)
            send(f'/vg audit {g} {i} done')
            consumed()
            row_after(before)
        if n % 25 == 0:
            print(f'   {n}/{len(todo)} ...', flush=True)
    print('done', flush=True)


if __name__ == '__main__':
    sys.exit(main())
