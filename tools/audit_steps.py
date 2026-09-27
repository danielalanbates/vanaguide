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
import subprocess
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


LAUNCHER = '/Applications/FFXI-on-Mac.app/Contents/MacOS/FFXI-on-Mac'
LOCAL_LOADER = 'horizon-loader.exe --server 127.0.0.1'


def fps_healthy(game, window=40, floor=2.0):
    """False when the local client has been under `floor` fps for the last `window` samples.

    After a couple of hours of zone hopping the client's footprint passes 2 GB on an 8 GB Mac,
    macOS compresses most of it, and it falls to ~0.1 fps: every check after that times out.
    """
    path = os.path.join(game, 'fps-local-server.csv')
    try:
        if time.time() - os.path.getmtime(path) > 30:
            return False
        with open(path, encoding='utf-8', errors='replace') as fh:
            rows = fh.read().strip().splitlines()[-window:]
        seq = [float(r.split(',')[2]) for r in rows if r[:1].isdigit()]
    except (OSError, ValueError, IndexError):
        return True
    if len(seq) < 10:
        return True
    # A zone load drops the rate for 10-20 s every time; stuck means the median of ~80 s and
    # every one of the last ten samples are under the floor.
    vals = sorted(seq)
    return vals[len(vals) // 2] >= floor or any(v >= floor for v in seq[-10:])


def local_client_running():
    return subprocess.run(['/usr/bin/pgrep', '-f', LOCAL_LOADER], capture_output=True).returncode == 0


def restart_client(game, log_path, before=None):
    """Log the Test character out, then start the local world again through the launcher.

    Only the local-world client, only by its --server address, and /shutdown first.
    """
    if before is not None:
        before()
    pipe = os.path.join(game, 'addons', 'cmdpipe', 'cmd.txt')
    with open(pipe, 'w') as fh:
        fh.write('/shutdown\n')
    end = time.time() + 90
    while local_client_running() and time.time() < end:
        time.sleep(3)
    if local_client_running():
        subprocess.run(['/usr/bin/pkill', '-f', LOCAL_LOADER])
        time.sleep(8)
    zones_before = open(log_path, errors='replace').read().count('IncreaseZoneCounter')
    subprocess.Popen([LAUNCHER, '--world', 'Local server', '--play'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    end = time.time() + 600
    while time.time() < end:
        time.sleep(5)
        if open(log_path, errors='replace').read().count('IncreaseZoneCounter') > zones_before:
            time.sleep(25)
            return True
    return False


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
    ap.add_argument('--zone-wait', type=float, default=10.0)
    ap.add_argument('--step-wait', type=float, default=4.0)
    ap.add_argument('--skip-zones', default='178')
    ap.add_argument('--max-restarts', type=int, default=8)
    ap.add_argument('--restart-every', type=int, default=200,
                    help='restart the client after this many audited steps (0 = never)')
    ap.add_argument('--mirror', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'audit-mirror.csv'),
                    help='append-only copy of audit.csv outside the addon folder, which the launcher replaces on every Play')
    ap.add_argument('--map-log', default=os.path.expanduser('~/Games/lsb/run/xi_map.log'))
    args = ap.parse_args()

    addon = os.path.join(args.game, 'addons', 'Vanaguide')
    cmd = os.path.join(addon, 'cmd.txt')
    csv = os.path.join(addon, 'audit.csv')
    skipz = {int(z) for z in args.skip_zones.split(',') if z.strip().isdigit()}

    last_gm = [0.0]

    def send(line):
        # Server commands sent back to back were sometimes dropped (the first !zone after a
        # !delquest / jump pair failed most of the time); keep them 1.5 s apart.
        if line.startswith('!'):
            gap = time.time() - last_gm[0]
            if gap < 1.5:
                time.sleep(1.5 - gap)
            last_gm[0] = time.time()
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
    mirror_state = {'offset': 0}

    def mirror():
        # Copy rows the addon has written since the last call; a reinstalled addon folder starts
        # a fresh audit.csv, so a shorter file means start from its beginning again.
        try:
            size = os.path.getsize(csv)
        except OSError:
            mirror_state['offset'] = 0
            return
        if size < mirror_state['offset']:
            mirror_state['offset'] = 0
        with open(csv, 'rb') as src:
            src.seek(mirror_state['offset'])
            chunk = src.read()
        if chunk:
            with open(args.mirror, 'ab') as dst:
                dst.write(chunk)
            mirror_state['offset'] += len(chunk)

    done = set()
    sources = [f for f in (args.mirror, csv) if os.path.exists(f)]
    if os.path.exists(csv):
        mirror_state['offset'] = os.path.getsize(csv)
    for path in sources:
        for line in open(path, encoding='utf-8', errors='replace'):
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
    refused = {}
    restarts = 0
    bad_checks = 0
    audited = 0
    last_restart_at = 0
    for n, s in enumerate(todo, 1):
        g, i = s['guide'], s['step']
        if s.get('zone') in skipz:
            print(f'   {g}/{i} skipped: zone {s["zone"]} is on the skip list', flush=True)
            continue
        for line in clear_for(s):
            send(line)
            consumed()
        due = args.restart_every and audited and audited % args.restart_every == 0 and audited != last_restart_at
        if n % 10 == 0:
            bad_checks = 0 if fps_healthy(args.game) else bad_checks + 1
        if bad_checks >= 2 or due:
            bad_checks = 0
            if restarts >= args.max_restarts:
                print(f'!! client needs a restart but the cap of {args.max_restarts} is used -- stopping', flush=True)
                break
            restarts += 1
            last_restart_at = audited
            print(f'   restarting the local client ({restarts}/{args.max_restarts}): '
                  + ('scheduled' if due else 'under 2 fps'), flush=True)
            if not restart_client(args.game, args.map_log, mirror):
                print('!! the client did not come back -- stopping', flush=True)
                break
            zone = None
        send(f'/vg audit {g} {i} jump')
        if not consumed():
            if restarts < args.max_restarts:
                restarts += 1
                print(f'   the client stopped reading cmd.txt -- restarting it ({restarts}/{args.max_restarts})', flush=True)
                if restart_client(args.game, args.map_log, mirror):
                    zone = None
                    send(f'/vg audit {g} {i} jump')
                    if consumed():
                        pass
                    else:
                        print('!! still not reading cmd.txt after a restart -- stopping', flush=True)
                        break
                else:
                    print('!! the client did not come back -- stopping', flush=True)
                    break
            else:
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
        audited += 1
        b = last_row(csv).split(',')
        if s.get('zone') is not None and len(b) > 5 and b[5] != str(s['zone']):
            # A zone load can outlast the wait: look again (every 4 s, up to 20 s) before moving again.
            for _ in range(5):
                time.sleep(4.0)
                before = os.path.getsize(csv)
                send(f'/vg audit {g} {i}')
                consumed()
                row_after(before)
                b = last_row(csv).split(',')
                if len(b) > 5 and b[5] == str(s['zone']):
                    break
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
                refused[s['zone']] = refused.get(s['zone'], 0) + 1
                print(f'   {g}/{i}: still in zone {b[5]} -- skipped', flush=True)
                if refused[s['zone']] >= 2:
                    skipz.add(s['zone'])
                    print(f'   zone {s["zone"]} refused twice -- skipping its remaining steps', flush=True)
                if stuck >= 12:
                    print('!! twelve moves in a row did not take -- the character is wedged, stopping', flush=True)
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
        mirror()
        if n % 25 == 0:
            print(f'   {n}/{len(todo)} ...', flush=True)
    mirror()
    print('done', flush=True)


if __name__ == '__main__':
    sys.exit(main())
