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
import csv as csvmod
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


HOSTS_LINES = ('127.0.0.1 ffxi00.pol.com', '127.0.0.1 pp000.pol.com', '127.0.0.1 macbookpro.lan')


def ensure_hosts(game):
    """Point FFXI's hard-coded POL names at the local machine in the prefix's hosts file.

    Wine resets that file to its default when it updates the prefix during a relaunch, and each
    missing name then costs a 30-90 s DNS timeout at login.
    """
    path = os.path.join(os.path.dirname(os.path.dirname(game)), 'drive_c', 'windows', 'system32',
                        'drivers', 'etc', 'hosts')
    if not os.path.isdir(os.path.dirname(path)):
        path = os.path.join(os.path.dirname(game), 'windows', 'system32', 'drivers', 'etc', 'hosts')
    try:
        text = open(path, encoding='utf-8', errors='replace').read() if os.path.exists(path) else ''
        missing = [l for l in HOSTS_LINES if l not in text]
        if missing:
            with open(path, 'a') as fh:
                fh.write(('' if text.endswith('\n') or not text else '\n') + '\n'.join(missing) + '\n')
    except OSError:
        pass


def wait_zone_in(game, log_path, zones_before, timeout=900):
    end = time.time() + timeout
    fixed_at = (time.time() + 30, time.time() + 90)
    while time.time() < end:
        time.sleep(5)
        if any(abs(time.time() - t) < 5 for t in fixed_at):
            ensure_hosts(game)
        try:
            count = open(log_path, errors='replace').read().count('IncreaseZoneCounter')
        except OSError:
            count = 0
        if count > zones_before or count < zones_before:
            if count > 0 and count != zones_before:
                time.sleep(25)
                return True
    return False


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
    ensure_hosts(game)
    zones_before = open(log_path, errors='replace').read().count('IncreaseZoneCounter')
    subprocess.Popen([LAUNCHER, '--world', 'Local server', '--play'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wait_zone_in(game, log_path, zones_before)


def event_locked(game):
    """True when the client answered the last server command with 'A command error occurred.'

    That is what it says while the character is held in an event -- a zone-in cutscene, which the
    audit's own mission changes keep triggering -- and every !zone/!pos after it fails the same way.
    """
    path = os.path.join(game, 'addons', 'cmdpipe', 'chat.txt')
    try:
        with open(path, 'rb') as fh:
            fh.seek(max(0, os.path.getsize(path) - 6000))
            tail = fh.read().decode('utf-8', 'replace').splitlines()
    except OSError:
        return False
    # The answer to the most recent server command: audit lines may follow it, so look at what
    # came after the last "!" command rather than at the last few lines.
    last = max((i for i, line in enumerate(tail) if '>> /say !' in line or ' : !' in line), default=None)
    if last is None:
        return False
    return any('A command error occurred' in line for line in tail[last + 1:last + 4])


def character_dead(game):
    """True when the client answered a recent command with "You cannot use that command while
    unconscious."  In the 2026-09-27 recheck the Davoi Mush killed Test on 5/10 and every
    !zone after it got that answer: 44/41 .. 11/4 (ten steps) never moved, and zones 159, 175
    and 176 went on the skip list as "refused" though nothing had refused them."""
    path = os.path.join(game, 'addons', 'cmdpipe', 'chat.txt')
    try:
        with open(path, 'rb') as fh:
            fh.seek(max(0, os.path.getsize(path) - 3000))
            tail = fh.read().decode('utf-8', 'replace').splitlines()
    except OSError:
        return False
    return any('while unconscious' in line for line in tail[-12:])


def hard_reset(game, log_path, db_pass, before=None):
    """Free a character stuck in an event: close the local client, move Test to Southern
    San d'Oria in the database (the local server is ours), start it again."""
    if before is not None:
        before()
    # /shutdown first; a client held in an event or frozen will not act on it, so pkill after 30 s.
    try:
        with open(os.path.join(game, 'addons', 'cmdpipe', 'cmd.txt'), 'w') as fh:
            fh.write('/shutdown\n')
    except OSError:
        pass
    end = time.time() + 30
    while local_client_running() and time.time() < end:
        time.sleep(2)
    subprocess.run(['/usr/bin/pkill', '-f', LOCAL_LOADER])
    end = time.time() + 30
    while local_client_running() and time.time() < end:
        time.sleep(2)
    sql = ("UPDATE chars SET pos_zone=230, pos_prevzone=230, pos_x=-100, pos_y=0, pos_z=-50 "
           "WHERE charname='Test'; DELETE FROM accounts_sessions WHERE charid="
           "(SELECT charid FROM chars WHERE charname='Test');")
    subprocess.run(['/opt/homebrew/opt/mariadb/bin/mariadb', '-uxiuser', f'-p{db_pass}', 'xidb', '-e', sql],
                   capture_output=True)
    ensure_hosts(game)
    zones_before = open(log_path, errors='replace').read().count('IncreaseZoneCounter')
    subprocess.Popen([LAUNCHER, '--world', 'Local server', '--play'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wait_zone_in(game, log_path, zones_before)


def npc_indexes(steps, db_pass):
    """(guide, step) -> the server's target index for the step's NPC: the spawned npc_list row with
    that name in the step's zone, nearest the marker."""
    import re as _re
    if not db_pass:
        return {}
    out = subprocess.run(['/opt/homebrew/opt/mariadb/bin/mariadb', '-N', '-B', '-uxiuser', f'-p{db_pass}', 'xidb', '-e',
                          'SELECT (npcid>>12)&0xFFF, npcid&0xFFF, polutils_name, name, pos_x, pos_z, status FROM npc_list'],
                         capture_output=True, text=True, errors='replace').stdout
    norm = lambda x: _re.sub(r'[^a-z0-9]', '', (x or '').lower())
    rows = {}
    for line in out.splitlines():
        p = line.split('\t')
        if len(p) < 7 or not p[0].isdigit():
            continue
        for n in {norm(p[2]), norm(p[3])}:
            if n:
                rows.setdefault((int(p[0]), n), []).append((int(p[1]), float(p[4]), float(p[5]), p[6]))
    found = {}
    # Markers ("???", qm*, _xyz) normalise to '' or to a name the step does not carry, so they
    # never got an index and fell back to "any named entity within 10 yalms" -- which fails
    # where this client's DAT names that index nothing or something else (44/35: qm_cetus,
    # zone 89 #878, sits exactly on the marker; the nearest *named* entity was 13 yalms off).
    # Take the spawned marker-like row within 3 yalms of the marker instead.
    markers = {}
    for line in out.splitlines():
        p = line.split('\t')
        if len(p) < 7 or not p[0].isdigit():
            continue
        if p[6] == '0' and (p[2] == '???' or p[3].startswith('qm') or p[3].startswith('_')):
            markers.setdefault(int(p[0]), []).append((int(p[1]), float(p[4]), float(p[5])))
    for s in steps:
        if s.get('zone') is None or s.get('x') is None or not s.get('npc'):
            continue
        npc = s['npc']
        if npc == '???' or npc.startswith('qm') or npc.startswith('_'):
            near = [c for c in markers.get(s['zone'], [])
                    if (c[1] - s['x']) ** 2 + (c[2] - s['z']) ** 2 <= 9.0]
            if near:
                best = min(near, key=lambda c: (c[1] - s['x']) ** 2 + (c[2] - s['z']) ** 2)
                found[(s['guide'], s['step'])] = best[0]
            continue
        cands = [c for c in rows.get((s['zone'], norm(s['npc'])), []) if c[3] == '0'] or rows.get((s['zone'], norm(s['npc'])), [])
        if cands:
            best = min(cands, key=lambda c: (c[1] - s['x']) ** 2 + (c[2] - s['z']) ** 2)
            found[(s['guide'], s['step'])] = best[0]
    return found


def clear_for(s):
    """Undo the step's condition first, so the 'pre' row can show it open."""
    c, area, i = s['cond'], s.get('area'), s.get('id')
    if c in ('Q', 'QA') and area in QUEST_LOG: return [f'!delquest {QUEST_LOG[area]} {i}']
    # `M`: clear the bit only.  X is made current by arm_for() once the character stands on
    # the step: with X current, LandSandBoat's mission scripts start a cutscene on zone-in or
    # on entering a trigger area (cop/2_1_An_Invitation_West.lua onZoneIn 110,
    # wotg/05_While_the_Cat_is_Away.lua onZoneIn 7, toau/08_A_Mercenary_Life.lua trigger
    # area 3 -> 3050), and the client then refuses GM commands ("A command error occurred").
    if c == 'M' and area in MISSION_LOG and area not in NOT_SENT:
        return [f'!delmission {MISSION_LOG[area]} {i}']
    if c == 'MA' and area in MISSION_LOG: return [f'!delmission {MISSION_LOG[area]} {i}']
    if c == 'KI' and s.get('ki') is not None: return [f'!delkeyitem {s["ki"]}']
    # `!delitem` removes one (scripts/commands/delitem.lua).  Without it every IT step left its
    # item behind: the 30-slot bag filled and `!additem 609` (12/5) got "You cannot obtain the
    # item. Come back after sorting your inventory." (additem.lua, getFreeSlotsCount() == 0).
    if c == 'IT' and s.get('item') is not None: return [f'!delitem {s["item"]}'] * (s.get('item_n') or 1)
    return []


def cleanup_for(s):
    """Sent after the 'done' rows: take back what gm_for() handed out that takes up room."""
    if s['cond'] == 'IT' and s.get('item') is not None:
        return [f'!delitem {s["item"]}'] * (s.get('item_n') or 1)
    return []


# LandSandBoat sends a character only its *own* nation's current mission (0x056_mission.cpp:
# NationMission = m_missionLog[profile.nation].current).  Test is San d'Oria (chars.nation = 0),
# so `!addmission BASTOK 0` was answered "Added Bastok mission 0 to Test." and the client never
# heard of it: 10/1 11/1 12/1 13/1 14/1 stayed open.  Completed bits cover all three nations
# (page 0x00D0), so `M` steps pass either way; `MA` needs the home nation switched for the step.
# setNation sends nothing by itself; the step's own !delmission/!addmission pushes 0xFFFF.
NATION_ID = {'sandoria': 0, 'bastok': 1, 'windurst': 2}
HOME_NATION = 0     # the Test character's own nation, put back after every switched step


def nation_for(s):
    """The home nation the step needs, or None when the character's own will do."""
    if s['cond'] == 'MA' and NATION_ID.get(s.get('area'), HOME_NATION) != HOME_NATION:
        return NATION_ID[s['area']]
    return None


def arm_for(s):
    """Sent once the character is on the step: make X current, so a current number left
    past X by an earlier step does not read as done.  Zone-in and trigger-area scripts fire
    on arrival only, so arming after arrival does not start them."""
    c, area, i = s['cond'], s.get('area'), s.get('id')
    if c == 'M' and area in MISSION_LOG and area not in NOT_SENT:
        return [f'!addmission {MISSION_LOG[area]} {i}']
    return []


# LandSandBoat's own answer to each command (scripts/commands/*.lua printToPlayer); a tuple
# lists every answer that means the command was handled.  `!additem` has none to wait for: it
# answers only with messageSpecial text ids, which this client's zone DATs number differently.
REPLY = {
    'completequest': 'Quest with ID {id} for', 'addquest': 'quest {id} to', 'delquest': 'quest {id} from',
    'completemission': 'Mission with ID {id} for', 'addmission': 'mission {id} to',
    'delmission': 'mission {id} from',
    'addkeyitem': ('Key item {id} was given to', 'already has key item {id}.'),
    'delkeyitem': ('Key item {id} deleted from', 'does not have key item {id}.'),
    'delitem': ('Item {id} was deleted from', 'does not have item {id}.'),
    'setplayernation': ('home nation to',),
    'immortal': ('is now immortal!', 'is mortal again.'),
}


def chat_path(game):
    return os.path.join(game, 'addons', 'cmdpipe', 'chat.txt')


def chat_size(game):
    try:
        return os.path.getsize(chat_path(game))
    except OSError:
        return 0


def wait_reply(game, line, since, timeout=20.0):
    """'ok' when the server's answer to `line` is in chat.txt after byte `since`; 'refused'
    when the client answered `>> /say <line>` with "A command error occurred"; 'silent' when
    nothing came.  cmd.txt being emptied only proves the addon queued the line."""
    verb, _, rest = line[1:].partition(' ')
    want = REPLY.get(verb)
    if want is None:
        time.sleep(3.0)
        return 'ok'
    arg = rest.split()[-1] if rest.split() else ''
    wants = [w.format(id=arg) for w in (want if isinstance(want, tuple) else (want,))]
    end = time.time() + timeout
    while time.time() < end:
        try:
            if os.path.getsize(chat_path(game)) < since:
                since = 0           # the client restarted and began a fresh chat.txt
            with open(chat_path(game), 'rb') as fh:
                fh.seek(since)
                tail = fh.read().decode('utf-8', 'replace').splitlines()
        except OSError:
            tail = []
        if any(w in l for l in tail for w in wants):
            return 'ok'
        for n, l in enumerate(tail):
            if l.rstrip().endswith(f'>> /say {line}') and any('A command error occurred' in m for m in tail[n + 1:n + 3]):
                return 'refused'
        time.sleep(0.5)
    return 'silent'


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
    ap.add_argument('--only', help='file of guide/step pairs to (re)audit, one per line; ignores earlier rows')
    ap.add_argument('--db-pass', default=os.environ.get('XI_DB_PASS', ''))
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

    def gm(line, tries=3):
        """Send one server command and wait for the server's own answer; resend after a
        refusal or silence (24/13, 24/19, 24/26, 24/41 echoed `!completequest` and never got
        "Completed ... Quest"; 49/3 and 49/25 wrote 'done' before the answer arrived)."""
        for _ in range(tries):
            since = chat_size(args.game)
            send(line)
            consumed()
            if wait_reply(args.game, line, since) == 'ok':
                return True
            time.sleep(5.0)
        print(f'   {line}: no answer from the server after {tries} tries', flush=True)
        return False

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

    def audit_cmd(g, i, mode='pre'):
        idx = index_of.get((g, i))
        return f'/vg audit {g} {i} {mode}' + (f' {idx}' if idx is not None else '')

    def fsize():
        try:
            return os.path.getsize(csv)
        except OSError:
            return 0

    def row_after(before, timeout=10.0):
        end = time.time() + timeout
        while time.time() < end:
            if fsize() > before:
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
    if args.only:
        want = {tuple(l.strip().split('/')) for l in open(args.only) if '/' in l}
        todo = [s for s in steps if (str(s['guide']), str(s['step'])) in want]
    index_of = npc_indexes(steps, args.db_pass)
    # Zone order: a zone load costs ~20 s and there are far fewer zones than steps.
    todo.sort(key=lambda s: (s.get('zone') is None, s.get('zone') or 0, s['guide'], s['step']))
    if args.limit:
        todo = todo[:args.limit]
    print(f'{len(steps)} steps, {len(todo)} left to audit', flush=True)

    def immortal():
        """`!immortal` toggles (scripts/commands/immortal.lua, setUnkillable, kept across logins
        by the 'Immortal' char var), so send it and send it again if it answered 'mortal'."""
        for _ in range(2):
            since = chat_size(args.game)
            if not gm('!immortal'):
                return False
            try:
                with open(chat_path(args.game), 'rb') as fh:
                    fh.seek(since)
                    tail = fh.read().decode('utf-8', 'replace')
            except OSError:
                tail = ''
            if 'is now immortal!' in tail:
                return True
        return False

    if not immortal():
        print('   !immortal did not take -- aggressive monsters can still kill Test', flush=True)

    zone = None
    nation_now = [HOME_NATION]
    silent = 0
    stuck = 0
    refused = {}
    restarts = 0
    bad_checks = 0
    audited = 0
    last_restart_at = 0
    for n, s in enumerate(todo, 1):
        mirror()
        g, i = s['guide'], s['step']
        if s.get('zone') in skipz:
            print(f'   {g}/{i} skipped: zone {s["zone"]} is on the skip list', flush=True)
            continue
        # Every step runs as the nation it needs and every other step as Test's own, so a step
        # that `continue`s part-way cannot leave the rest of the run on a foreign nation.
        want_nation = nation_for(s)
        want_nation = HOME_NATION if want_nation is None else want_nation
        if want_nation != nation_now[0]:
            if gm(f'!setplayernation {want_nation}'):
                nation_now[0] = want_nation
            else:
                print(f'   {g}/{i}: !setplayernation {want_nation} got no answer', flush=True)
        for line in clear_for(s):
            gm(line)
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
            if not (hard_reset(args.game, args.map_log, args.db_pass, mirror) if args.db_pass else restart_client(args.game, args.map_log, mirror)):
                print('!! the client did not come back -- stopping', flush=True)
                break
            zone = None
        send(f'/vg audit {g} {i} jump')
        if not consumed():
            if restarts < args.max_restarts:
                restarts += 1
                print(f'   the client stopped reading cmd.txt -- restarting it ({restarts}/{args.max_restarts})', flush=True)
                if (hard_reset(args.game, args.map_log, args.db_pass, mirror) if args.db_pass else restart_client(args.game, args.map_log, mirror)):
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
        def zone_ins():
            try:
                return open(args.map_log, errors='replace').read().count('IncreaseZoneCounter')
            except OSError:
                return 0

        def pos_to():
            # No zone argument. With one, LandSandBoat's setPos re-zones even into the zone the
            # character already stands in (src/map/lua/lua_base_entity.cpp setPos: Disappear +
            # requestedZoneChange): the row is taken from the old spot before the zone-in lands,
            # and the zone-in cutscene answers the next command with 'A command error occurred.'
            # Without it the server only sends the new position (GP_SERV_COMMAND_WPOS).
            y = s.get('db_y') or 0
            send(f'!pos {s["x"]:.3f} {y:.3f} {s["z"]:.3f}')
            consumed()

        def move(force_zone=False):
            nonlocal zone
            if s.get('zone') is None:
                time.sleep(1.0)
                for line in arm_for(s):
                    gm(line)
                return
            # A cross-zone `!pos` is sometimes refused (the character stays put and every later
            # row is taken from the wrong zone); `!zone` is not. So change zone first.
            if s['zone'] != zone or force_zone:
                seen = zone_ins()
                send(f'!zone {s["zone"]}')
                consumed()
                # A !pos that reaches the server while the character is still zoning is lost
                # (setPos on Status::Disappear), so wait for the zone-in before the settle.
                end = time.time() + 90
                while zone_ins() == seen and time.time() < end:
                    time.sleep(1.0)
                time.sleep(args.zone_wait)
                zone = s['zone']
                # A zone-in cutscene can hold the character while GM commands still answer
                # (event_locked() never sees it).  39/3's gm_for leaves SoA 5 current and
                # soa/1_4 Heartwings onZoneIn returns csid 2 in Western Adoulin; 16/10 .. 39/99
                # then found no NPC near markers their NPC stands on.  !release ends a
                # server-side event (lua_base_entity.cpp release -> endCurrentEvent) and says
                # "Event skipped" only when there was one, which shows in chat.txt.
                send('!release')
                consumed()
            if s.get('x') is not None:
                pos_to()
            time.sleep(args.step_wait)
            for line in arm_for(s):
                gm(line)

        move()
        before = fsize()
        send(audit_cmd(g, i))
        consumed()
        # Right after a zone-in or a client restart the addon can answer late, and that row then
        # stood as the step's last 'pre' row (24/40: 827 yalms off, 179 frames).  Wait once
        # more, so the landing check below can move the character again instead of skipping.
        if not row_after(before) and not row_after(before, 20.0):
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
                before = fsize()
                send(audit_cmd(g, i))
                consumed()
                row_after(before)
                b = last_row(csv).split(',')
                if len(b) > 5 and b[5] == str(s['zone']):
                    break
        if (s.get('zone') is not None and len(b) > 5 and b[5] != str(s['zone'])
                and event_locked(args.game) and restarts < args.max_restarts):
            restarts += 1
            print(f'   {g}/{i}: the character is held in an event -- freeing it ({restarts}/{args.max_restarts})', flush=True)
            if not hard_reset(args.game, args.map_log, args.db_pass, mirror):
                print('!! the client did not come back -- stopping', flush=True)
                break
            zone = None
            move()
            before = fsize()
            send(audit_cmd(g, i))
            consumed()
            row_after(before)
            b = last_row(csv).split(',') if os.path.exists(csv) else b
        if s.get('zone') is not None and len(b) > 5 and b[5] != str(s['zone']):
            print(f'   {g}/{i}: in zone {b[5]}, wanted {s["zone"]} -- retrying the move', flush=True)
            zone = None
            move(force_zone=True)
            before = fsize()
            send(audit_cmd(g, i))
            consumed()
            row_after(before)
            b = last_row(csv).split(',')
            if len(b) > 5 and b[5] != str(s['zone']):
                stuck += 1
                zone = None
                if character_dead(args.game):
                    print(f'   {g}/{i}: Test is unconscious ("You cannot use that command while '
                          'unconscious.") -- stopping; raise or home-point it and rerun --only', flush=True)
                    break
                if not event_locked(args.game):
                    refused[s['zone']] = refused.get(s['zone'], 0) + 1
                print(f'   {g}/{i}: still in zone {b[5]} -- skipped', flush=True)
                if refused.get(s['zone'], 0) >= 2:
                    skipz.add(s['zone'])
                    print(f'   zone {s["zone"]} refused twice -- skipping its remaining steps', flush=True)
                if stuck >= 12:
                    print('!! twelve moves in a row did not take -- the character is wedged, stopping', flush=True)
                    break
                continue
        stuck = 0
        # The row proves the move, not the command: a !pos swallowed by an event lock leaves the
        # character on the previous step's spot, and every check in the row is about that spot.
        for _ in range(3):
            b = last_row(csv).split(',')
            try:
                off = s.get('x') is not None and float(b[7]) > float(b[8])
            except (IndexError, ValueError):
                off = False
            if not off:
                break
            print(f'   {g}/{i}: {b[7]} yalms from the marker -- moving again', flush=True)
            pos_to()
            time.sleep(args.step_wait)
            before = fsize()
            send(audit_cmd(g, i))
            consumed()
            row_after(before)
        for _ in range(4):
            r_ = next(csvmod.reader([last_row(csv)]), [])
            absent = len(r_) > 11 and r_[10] != '' and r_[11] == 'absent'
            if 'nothing loaded yet' not in last_row(csv) and not absent:
                break
            time.sleep(6.0)
            before = fsize()
            send(audit_cmd(g, i))
            consumed()
            row_after(before)
        cmds = gm_for(s, nxt)
        if cmds:
            answered = all([gm(line) for line in cmds])
            # The 0x056 can trail the chat line on a slow client: audit 'done' until it reads
            # done, up to five times.
            for _ in range(5 if answered else 1):
                before = fsize()
                send(audit_cmd(g, i, 'done'))
                consumed()
                row_after(before)
                row = next(csvmod.reader([last_row(csv)]), [])
                if len(row) > 14 and row[2] == 'done' and row[14] == 'done':
                    break
                time.sleep(3.0)
        for line in cleanup_for(s):
            gm(line)
        mirror()
        if n % 25 == 0:
            print(f'   {n}/{len(todo)} ...', flush=True)
    if nation_now[0] != HOME_NATION:
        gm(f'!setplayernation {HOME_NATION}')
    mirror()
    print('done', flush=True)


if __name__ == '__main__':
    sys.exit(main())
