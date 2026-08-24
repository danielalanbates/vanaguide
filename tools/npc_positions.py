#!/usr/bin/env python3
"""Vanaguide :: tools/npc_positions.py

Check every quest against the server's own NPC table, without a client.

Standing on each quest in a running client is the strongest evidence there is -- it proves the
NPC is loaded, named as the database says, and within a few yalms of the coordinate. It is
also slow (about thirty seconds a quest, and a sweep dies if the character does), it cannot
say anything about the 160 quests that carry no coordinates, and it cannot tell "this server
does not spawn that NPC" apart from "that NPC is standing somewhere else entirely".

`npc_list` in the LandSandBoat database answers all three. It holds 40,000-odd NPCs with the
position the server will spawn them at, and the zone is encoded in the id:

    zone = (npcid >> 12) & 0xFFF

So for every quest with a named NPC, there is a fact available in a single query: does this
server have an NPC by that name, is it in the zone the guide says, and how far is it from the
coordinate the guide gives. That is a real check of the guide data, it covers quests that have
no coordinates at all, and it takes about a second for all 506.

It does not replace the in-client sweep -- the database says where an NPC *would* spawn, and
only the client can show that it *did*. The two together are what make a miss readable:

    server has it here, client found it there    -> the guide is right
    server has it here, client saw nothing       -> a spawn condition, not a bad coordinate
    server has it somewhere else                 -> a real data error, and here is the fix
    server does not have it                      -> nothing this server can ever prove

    tools/npc_positions.py                       # check everything, write it to the ledger
    tools/npc_positions.py --report              # print what is worth acting on

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import math
import os
import re
import subprocess
import sys

import ledger

HERE = os.path.dirname(os.path.abspath(__file__))
MARIADB = os.environ.get('VG_MARIADB', '/opt/homebrew/opt/mariadb/bin/mariadb')
DBPASS = os.environ.get('VG_DBPASS', os.path.expanduser('~/Games/lsb/.dbpass'))

SCHEMA = """
CREATE TABLE IF NOT EXISTS npcs (
    npcid   INTEGER PRIMARY KEY,
    zone    INTEGER NOT NULL,
    -- Three ways of asking for the same entity, because the guide and the server do not
    -- always spell it the same way. `name` is the display name normalized. `aname` is the
    -- same words sorted: LandSandBoat writes a door as Door:"Lion Springs" and the mission
    -- script that uses it writes `Lion Springs Door`, and eleven missions were reported as
    -- "no NPC of that name exists" over nothing but word order. `iname` is the internal
    -- name, which is what a script's own section keys use -- `Lion_Springs`, `_6s1`,
    -- `qm_maw` -- and for markers it is the only name there is.
    name    TEXT NOT NULL,
    aname   TEXT NOT NULL DEFAULT '',
    iname   TEXT NOT NULL DEFAULT '',
    x       REAL NOT NULL,
    y       REAL NOT NULL,
    z       REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS npcs_name ON npcs(name);
CREATE INDEX IF NOT EXISTS npcs_aname ON npcs(aname);
CREATE INDEX IF NOT EXISTS npcs_iname ON npcs(iname);
CREATE INDEX IF NOT EXISTS npcs_zone ON npcs(zone, name);

-- What the server data says about each quest's NPC. One row per quest, replaced wholesale
-- each run: unlike a check in a live client, this is cheap enough to redo from scratch.
CREATE TABLE IF NOT EXISTS npc_match (
    kind        TEXT NOT NULL DEFAULT 'quest',
    area        TEXT NOT NULL,
    id          INTEGER NOT NULL,
    verdict     TEXT NOT NULL,
    dist        REAL,           -- to the guide's coordinate, when there is one
    npc_zone    INTEGER,        -- where the server actually puts it
    npc_x       REAL,
    npc_y       REAL,
    npc_z       REAL,
    candidates  INTEGER NOT NULL DEFAULT 0,
    note        TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (kind, area, id)
);
"""

# Two NPCs of the same name in one zone are common (a guard on each side of a gate). Anything
# inside this radius is the guide pointing at the right one; beyond it, the guide is pointing
# somewhere the NPC is not.
NEAR = 10.0


def positioned(n):
    """An npc_list row at exactly the origin has no position; it gets one at runtime.

    Several hundred rows are (0, 0, 0) -- NPCs a script places when it spawns them, and
    markers that only exist during an event. Measuring a distance to the origin produces a
    confident number and a meaningless one, so these are reported as what they are rather
    than as the guide being wrong.
    """
    return not (n['x'] == 0.0 and n['y'] == 0.0 and n['z'] == 0.0)


# The same rule core/verify.lua uses, deliberately: a name starting `qm`, a name starting
# with an underscore, or one containing `???`. The two used to differ -- this side was
# anchored and required digits after `qm`, the client side was a loose prefix -- and they
# disagreed about four real rows (`qm_rov2_20`, `qm_cetus`), which the client marker-passed
# and this side then looked up by name and could not find.
MARKER = re.compile(r'^(?:qm|_)|\?\?\?', re.I)


def is_marker(name):
    """A `???`, a door, a dig point: a real entity, named the way the server tracks it.

    These are not people and npc_list is not a reliable witness for them -- the same `qm3`
    exists in a dozen zones and is absent from others entirely, so matching by name produces
    confident nonsense ("the guide says zone 102, the server has it in 238"). The client
    sweep is the only thing that can speak to a marker, and it does.
    """
    return bool(MARKER.search((name or '').strip()))


def normalize(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def anagram(s):
    """The same words in whatever order, as one key.

    LandSandBoat writes a door's display name as `Door:"Lion Springs"`; the mission script's
    header comment writes the same door as `Lion Springs Door`. Normalised those are
    `doorlionsprings` and `lionspringsdoor`, which do not match, and eleven missions were
    reported as "no NPC of that name exists in npc_list" -- an existence claim -- when every
    one of them has a row within 1.6 yalms in the right zone. Sorting the words settles it.

    Used only after an exact match has failed, so it can turn a miss into a hit and never the
    other way round.
    """
    return ''.join(sorted(re.findall(r'[a-z0-9]+', (s or '').lower())))


def sql(query):
    """One query, tab-separated, no headers."""
    with open(DBPASS) as fh:
        password = fh.read().strip()
    out = subprocess.run([MARIADB, '-N', '-B', '-u', 'xiuser', '-p' + password, 'xidb',
                          '-e', query], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit('mariadb: ' + (out.stderr or out.stdout).strip())
    return [line.split('\t') for line in out.stdout.splitlines() if line.strip()]


def load_npcs(db):
    """Mirror npc_list into the ledger, so every later question is a join.

    `polutils_name` is what the client displays; `name` is the internal one, and for the
    markers this project keeps tripping over (`_0id`, `qm1`) it is the only one there is.
    Both are stored, in their own columns, along with the word-sorted form of the display
    name -- the three spellings a guide might be using for one entity.
    """
    rows = sql("""
        SELECT npcid, (npcid>>12)&0xFFF, COALESCE(NULLIF(polutils_name,''), CONVERT(name USING utf8)),
               CONVERT(name USING utf8), pos_x, pos_y, pos_z
        FROM npc_list
    """)
    with db:
        db.execute('DELETE FROM npcs')
        db.executemany('INSERT OR REPLACE INTO npcs '
                       '(npcid, zone, name, aname, iname, x, y, z) '
                       'VALUES (?,?,?,?,?,?,?,?)',
                       [(int(r[0]), int(r[1]), normalize(r[2]), anagram(r[2]),
                         normalize(r[3]), float(r[4]), float(r[5]), float(r[6]))
                        for r in rows if len(r) >= 7])
    return len(rows)


def dist(ax, az, bx, bz):
    return math.hypot(ax - bx, az - bz)


def match_all(db, kind='quest'):
    quests = db.execute('SELECT * FROM quests WHERE kind = ?', (kind,)).fetchall()
    out = []
    for q in quests:
        if is_marker(q['npc']):
            out.append((kind, q['area'], q['id'], 'marker', None, q['zone'], None, None, None, 0,
                        'a ???, a door or a dig point -- only the client can check this'))
            continue

        npc = normalize(q['npc'])
        if not npc:
            out.append((kind, q['area'], q['id'], 'no npc named', None, None, None, None, None, 0,
                        'the quest script names nobody to talk to'))
            continue

        # Exact display name first, then the same words in another order, then the internal
        # name. Each fallback only runs when the one before it found nothing, so a fallback
        # can turn a miss into a hit and never change a hit into something else.
        def look(where, *args):
            rows = db.execute('SELECT * FROM npcs WHERE ' + where, args).fetchall()
            return rows
        keys = [('name = ?', npc), ('aname = ?', anagram(q['npc'])),
                ('iname = ?', npc)]
        same_zone, anywhere, matched_by = [], [], 'name'
        for cond, key in keys:
            if not key:
                continue
            anywhere = look(cond, key)
            if anywhere:
                same_zone = look(cond + ' AND zone = ?', key, q['zone']) if q['zone'] else []
                matched_by = cond.split(' ')[0]
                break

        if not anywhere:
            out.append((kind, q['area'], q['id'], 'not on this server', None, None, None, None, None,
                        0, 'no NPC of that name exists in npc_list, under its '
                        'display name, its words in any order, or its internal name'))
            continue

        placed = [n for n in same_zone if positioned(n)]
        if q['zone'] and q['x'] is not None and same_zone and not placed:
            out.append((kind, q['area'], q['id'], 'placed at runtime', None, q['zone'], None, None,
                        None, len(same_zone),
                        'the server has it in the right zone with no fixed position'))
            continue

        if q['zone'] and q['x'] is not None and placed:
            best = min(placed, key=lambda n: dist(n['x'], n['z'], q['x'], q['z']))
            d = dist(best['x'], best['z'], q['x'], q['z'])
            verdict = 'confirmed' if d <= NEAR else 'moved'
            note = ('the server puts it %.1f yalms from where the guide points' % d
                    if verdict == 'moved' else '')
            if matched_by != 'name':
                spelling = ('the same words in another order' if matched_by == 'aname'
                            else "the server's internal name for it")
                note = (note + '; matched by ' + spelling).lstrip('; ')
            out.append((kind, q['area'], q['id'], verdict, d, best['zone'], best['x'], best['y'],
                        best['z'], len(placed), note))
            continue

        if q['zone'] and not same_zone:
            zones = sorted({n['zone'] for n in anywhere})
            out.append((kind, q['area'], q['id'], 'wrong zone', None, zones[0],
                        anywhere[0]['x'], anywhere[0]['y'], anywhere[0]['z'], len(anywhere),
                        'the guide says zone %s; the server has it in %s'
                        % (q['zone'], ', '.join(str(z) for z in zones[:6]))))
            continue

        # No coordinates in the guide at all -- which is exactly what this table can fix.
        zones = sorted({n['zone'] for n in anywhere})
        first = anywhere[0]
        out.append((kind, q['area'], q['id'],
                    'position recoverable' if len(zones) == 1 else 'position ambiguous',
                    None, first['zone'], first['x'], first['y'], first['z'], len(anywhere),
                    'the guide gives no position; the server has it in zone %s'
                    % ', '.join(str(z) for z in zones[:6])))

    with db:
        db.execute('DELETE FROM npc_match WHERE kind = ?', (kind,))
        db.executemany('INSERT INTO npc_match (kind, area, id, verdict, dist, npc_zone, '
                       'npc_x, npc_y, npc_z, candidates, note) '
                       'VALUES (?,?,?,?,?,?,?,?,?,?,?)', out)
    return len(out)


def report(db, kind='quest'):
    order = ['confirmed', 'moved', 'wrong zone', 'placed at runtime', 'marker',
             'position recoverable', 'position ambiguous', 'not on this server',
             'no npc named']
    counts = {r['verdict']: r['n'] for r in db.execute(
        'SELECT verdict, COUNT(*) n FROM npc_match WHERE kind = ? GROUP BY verdict', (kind,))}
    total = sum(counts.values())
    print(f'{total} {kind}s checked against npc_list')
    for v in order:
        if counts.get(v):
            print(f'   {v:<21} {counts[v]:>4}')

    for verdict, title in (('moved', 'The guide points somewhere the NPC is not'),
                           ('wrong zone', 'The guide names the wrong zone')):
        rows = db.execute("""SELECT m.*, q.name, q.npc, q.zone, q.x, q.z
                             FROM npc_match m JOIN quests q USING (kind, area, id)
                             WHERE m.kind = ? AND m.verdict = ?
                             ORDER BY m.dist DESC, q.name""",
                          (kind, verdict)).fetchall()
        if not rows:
            continue
        print(f'\n{title} ({len(rows)})')
        for r in rows[:40]:
            where = (f'{r["dist"]:.0f} yalms off' if r['dist']
                     else f'zone {r["zone"]} -> {r["npc_zone"]}')
            print(f'   {r["area"]:<11} {r["id"]:>4}  {r["name"][:34]:<34} {r["npc"][:18]:<18} '
                  f'{where:>16}  server: ({r["npc_x"]:.1f}, {r["npc_z"]:.1f}) '
                  f'zone {r["npc_zone"]}')
        if len(rows) > 40:
            print(f'   … and {len(rows) - 40} more')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=ledger.DB)
    ap.add_argument('--report', action='store_true', help='only print, do not re-check')
    ap.add_argument('--kind', default='quest', choices=('quest', 'mission'))
    args = ap.parse_args()

    db = ledger.connect(args.db)
    # npc_match predates missions and has no `kind`. It is a derived table -- every row is
    # rebuilt from npc_list in about a second -- so it is dropped rather than migrated.
    cols = [r[1] for r in db.execute('PRAGMA table_info(npc_match)')]
    if cols and 'kind' not in cols:
        db.execute('DROP TABLE npc_match')
        db.execute('DROP VIEW IF EXISTS quest_verdict')
        db.commit()
        print('npc_match rebuilt for missions')
    # Before the schema, not after: `CREATE TABLE IF NOT EXISTS` is silent about a table that
    # already exists with an older shape, and the CREATE INDEX lines that follow are not --
    # they fail on a column the table has not got. The columns have to be asked for by name.
    ledger.add_columns(db)
    db.executescript(SCHEMA)
    ledger.connect(args.db)         # recreate the combined view against the new table
    if not args.report:
        n = load_npcs(db)
        m = match_all(db, args.kind)
        print(f'{n} NPCs mirrored, {m} {args.kind}s matched')
    report(db, args.kind)


if __name__ == '__main__':
    sys.exit(main())
