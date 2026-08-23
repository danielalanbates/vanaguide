#!/usr/bin/env python3
"""Vanaguide :: tools/ledger.py

One row per quest, and the record of every time it was checked.

The sweep used to be a CSV that was appended to and read back by string matching, which was
fine until it was not: rows arrived twice, a re-check had to be spotted by "a later row wins",
and there was nowhere to put the difference between "this quest has no coordinates" and "this
quest has coordinates and nobody has stood on them yet". Both are unchecked; only one of them
is ever going to change.

So the state lives in SQLite instead, and the questions that matter are queries:

    tools/ledger.py init                 build/refresh the quest list from data/quests.lua
    tools/ledger.py ingest verify.csv    fold a sweep's rows in
    tools/ledger.py status               how far along, and what is left
    tools/ledger.py todo [--limit N]     the quests still owed a check, in sweep order
    tools/ledger.py check                structural faults: prerequisites that go nowhere
    tools/ledger.py export -o out.csv    the whole ledger, one row per quest

The database is `data/verification.sqlite3`. It is derived data -- `init` can rebuild the
quest side of it from the Lua at any time, and `ingest` is idempotent per (quest, run) -- but
it is the thing that says whether the goal is met, so it is kept, not regenerated per run.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import csv
import json
import os
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DB = os.path.join(REPO, 'data', 'verification.sqlite3')

SCHEMA = """
CREATE TABLE IF NOT EXISTS quests (
    area        TEXT NOT NULL,
    id          INTEGER NOT NULL,
    name        TEXT NOT NULL,
    npc         TEXT NOT NULL DEFAULT '',
    zone        INTEGER,
    x           REAL,
    y           REAL,
    z           REAL,
    PRIMARY KEY (area, id)
);

-- Every check ever run, not just the last one. A quest that missed at a twelve second settle
-- and was found at twenty-two is the evidence that the settle was too short, and throwing the
-- first row away throws that away too.
CREATE TABLE IF NOT EXISTS checks (
    area        TEXT NOT NULL,
    id          INTEGER NOT NULL,
    run         TEXT NOT NULL,          -- which sweep produced it
    seq         INTEGER NOT NULL,       -- order within the run
    verdict     TEXT NOT NULL,          -- found | absent | marker | unnamed | unchecked
    zone_seen   INTEGER,
    x           REAL,
    z           REAL,
    dist        REAL,
    why         TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (area, id, run, seq),
    FOREIGN KEY (area, id) REFERENCES quests(area, id)
);

CREATE INDEX IF NOT EXISTS checks_verdict ON checks(verdict);

-- Faults in the shape of the data rather than in a coordinate: a prerequisite naming a quest
-- that is not there, a zone id no zone has. Rewritten every `check`.
CREATE TABLE IF NOT EXISTS issues (
    area    TEXT NOT NULL,
    id      INTEGER NOT NULL,
    kind    TEXT NOT NULL,
    detail  TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (area, id, kind)
);

-- The current answer for each quest: the newest check, with the ones that say nothing
-- (`unchecked` -- the character never arrived) ignored, because they are the harness failing
-- rather than evidence.
CREATE VIEW IF NOT EXISTS quest_state AS
SELECT q.area, q.id, q.name, q.npc, q.zone, q.x, q.y, q.z,
       CASE
           WHEN q.zone IS NULL OR q.x IS NULL THEN 'no coordinates'
           ELSE COALESCE((SELECT c.verdict FROM checks c
                          WHERE c.area = q.area AND c.id = q.id AND c.verdict <> 'unchecked'
                          ORDER BY c.run DESC, c.seq DESC LIMIT 1), 'pending')
       END AS verdict,
       (SELECT c.dist FROM checks c
        WHERE c.area = q.area AND c.id = q.id AND c.verdict <> 'unchecked'
        ORDER BY c.run DESC, c.seq DESC LIMIT 1) AS dist,
       (SELECT c.why FROM checks c
        WHERE c.area = q.area AND c.id = q.id AND c.verdict <> 'unchecked'
        ORDER BY c.run DESC, c.seq DESC LIMIT 1) AS why,
       (SELECT COUNT(*) FROM checks c WHERE c.area = q.area AND c.id = q.id) AS attempts
FROM quests q;
"""

# The npc_match table is written by tools/npc_positions.py, which may not have run. The view
# is created separately so the ledger still works without it.
COMBINED = """
CREATE VIEW IF NOT EXISTS quest_verdict AS
SELECT s.area, s.id, s.name, s.npc, s.zone, s.x, s.z,
       s.verdict AS client, COALESCE(m.verdict, 'not checked') AS server, s.dist,
       COALESCE(NULLIF(m.note, ''), s.why, '') AS why,
       CASE
           -- Standing on it and finding the NPC is the whole point; nothing outranks it.
           WHEN s.verdict = 'found' THEN 'verified'
           -- The server data is a real check on its own, and it is the only one available for
           -- an NPC this server will not spawn for a character with no quest flags set.
           WHEN m.verdict = 'confirmed' THEN 'server confirmed'
           WHEN m.verdict IN ('moved', 'wrong zone') THEN 'data error'
           WHEN m.verdict = 'marker' OR s.verdict IN ('marker', 'unnamed')
                THEN 'only the client can check this'
           WHEN m.verdict = 'not on this server' THEN 'not on this server'
           WHEN s.verdict = 'no coordinates' OR m.verdict = 'no npc named'
                THEN 'nothing to check'
           ELSE 'pending'
       END AS verdict
FROM quest_state s LEFT JOIN npc_match m ON m.area = s.area AND m.id = s.id;
"""

# Terminal verdicts: nothing is learned by standing on the spot a second time. `absent` is
# deliberately NOT one of them -- an NPC missing at a short settle and present at a longer one
# is the single most common false miss this sweep produces.
SETTLED = ('found', 'marker', 'unnamed')


def connect(path=DB):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    try:
        db.executescript(COMBINED)
    except sqlite3.OperationalError:
        pass            # npc_positions.py has not run yet; quest_state still works
    return db


def quest_table():
    """Ask luajit for the generated table, rather than re-parsing Lua here."""
    lua = """
package.path = 'Vanaguide/?.lua;' .. package.path
local Q = require('data.quests')
local rows = {}
for area, quests in pairs(Q.quests) do
    for id, q in pairs(quests) do
        local pre = 'null'
        if q.prereq then pre = string.format('["%s",%d]', q.prereq[1], q.prereq[2]) end
        rows[#rows+1] = string.format('{"area":"%s","id":%d,"name":%q,"zone":%s,"x":%s,"z":%s,"y":%s,"npc":%q,"prereq":%s}',
            area, id, q.name or '', tostring(q.zone or 'null'),
            tostring(q.x or 'null'), tostring(q.z or 'null'), tostring(q.y or 'null'), q.npc or '', pre)
    end
end
print('[' .. table.concat(rows, ',') .. ']')
"""
    out = subprocess.run(['luajit', '-e', lua], cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit('could not read the quest table: ' + out.stderr.strip())
    return json.loads(out.stdout)


def classify(verdict_col, npc, why):
    """Turn one CSV row into a verdict.

    The CSV says only ok/MISS, and the three kinds of miss are not equally interesting: a
    marker quest whose "NPC" is a door, an NPC this server never spawns, and a genuinely wrong
    coordinate all read as MISS. See docs/QUEST_VERIFICATION.md.
    """
    if verdict_col == 'ok':
        return 'found'
    if 'standing in' in why:
        return 'unchecked'          # the character never arrived; says nothing about the data
    if npc.startswith('qm') or npc.startswith('_') or '???' in npc:
        return 'marker'
    if not npc:
        return 'unnamed'
    return 'absent'


def cmd_init(args):
    db = connect(args.db)
    rows = quest_table()
    with db:
        db.executemany(
            """INSERT INTO quests (area, id, name, npc, zone, x, y, z)
               VALUES (:area, :id, :name, :npc, :zone, :x, :y, :z)
               ON CONFLICT(area, id) DO UPDATE SET
                   name=excluded.name, npc=excluded.npc, zone=excluded.zone,
                   x=excluded.x, y=excluded.y, z=excluded.z""",
            [{k: r.get(k) for k in ('area', 'id', 'name', 'npc', 'zone', 'x', 'y', 'z')}
             for r in rows])
    # A quest that has left data/quests.lua should leave the ledger too, or its last verdict
    # sits in the totals forever claiming to be about something that exists.
    live = {(r['area'], r['id']) for r in rows}
    with db:
        gone = [k for k in db.execute('SELECT area, id FROM quests')
                if (k['area'], k['id']) not in live]
        for k in gone:
            db.execute('DELETE FROM quests WHERE area = ? AND id = ?', (k['area'], k['id']))
            db.execute('DELETE FROM checks WHERE area = ? AND id = ?', (k['area'], k['id']))
    if gone:
        print(f'{len(gone)} quests no longer in data/quests.lua, dropped')

    n = db.execute('SELECT COUNT(*) FROM quests').fetchone()[0]
    c = db.execute('SELECT COUNT(*) FROM quests WHERE zone IS NOT NULL AND x IS NOT NULL')\
          .fetchone()[0]
    print(f'{n} quests, {c} with coordinates -> {args.db}')


def cmd_ingest(args):
    db = connect(args.db)
    cols = ['area', 'id', 'ok', 'name', 'npc', 'want_zone', 'want_x', 'want_z',
            'zone', 'x', 'z', 'dist', 'why']
    known = {(r['area'], r['id']) for r in db.execute('SELECT area, id FROM quests')}
    added = skipped = 0
    seq = db.execute('SELECT COALESCE(MAX(seq), 0) FROM checks WHERE run = ?',
                     (args.run,)).fetchone()[0]
    with db, open(args.csv, newline='', encoding='utf-8', errors='replace') as fh:
        for row in csv.DictReader(fh, fieldnames=cols):
            if not row['area'] or not (row['id'] or '').strip().isdigit():
                continue
            key = (row['area'], int(row['id']))
            if key not in known:
                skipped += 1        # a quest that has since left data/quests.lua
                continue
            seq += 1
            def num(v):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return None
            db.execute(
                """INSERT OR REPLACE INTO checks
                   (area, id, run, seq, verdict, zone_seen, x, z, dist, why)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (key[0], key[1], args.run, seq,
                 classify(row['ok'], row['npc'] or '', row['why'] or ''),
                 int(num(row['zone']) or 0) or None, num(row['x']), num(row['z']),
                 num(row['dist']), row['why'] or ''))
            added += 1
    print(f'{added} checks recorded as run "{args.run}"'
          + (f', {skipped} rows for quests not in the database' if skipped else ''))
    cmd_status(args)


def counts(db):
    return {r['verdict']: r['n'] for r in db.execute(
        'SELECT verdict, COUNT(*) AS n FROM quest_state GROUP BY verdict')}


def cmd_status(args):
    db = connect(args.db)
    try:
        rows = list(db.execute('SELECT verdict, COUNT(*) n FROM quest_verdict '
                               'GROUP BY verdict ORDER BY n DESC'))
        total = sum(r['n'] for r in rows)
        print(f'{total} quests, by strongest evidence available:')
        for r in rows:
            print(f'   {r["verdict"]:<22} {r["n"]:>4}')
        good = sum(r['n'] for r in rows
                   if r['verdict'] in ('verified', 'server confirmed'))
        print(f'{good}/{total} confirmed correct '
              f'({good * 100 // max(total, 1)}%)\n')
    except sqlite3.OperationalError:
        pass

    c = counts(db)
    total = sum(c.values())
    checkable = total - c.get('no coordinates', 0)
    settled = sum(c.get(v, 0) for v in SETTLED)
    print(f'{total} quests: {checkable} can be checked by standing on them, '
          f'{c.get("no coordinates", 0)} have no coordinates at all')
    for v in ('found', 'absent', 'marker', 'unnamed', 'pending'):
        if c.get(v):
            print(f'   {v:<10} {c[v]:>4}')
    done = settled + c.get('absent', 0)
    print(f'{done}/{checkable} checked '
          f'({done * 100 // max(checkable, 1)}%), {c.get("pending", 0)} still owed a check')


def todo_rows(db, retry_absent=False, limit=0):
    """Quests still owed a check, in the order a sweep should walk them.

    Zone first, because every zone change costs a load and there are far fewer zones than
    quests; then by coordinate, so the quests that share a place end up next to each other and
    can be checked from one stop.
    """
    wanted = ['pending'] + (['absent'] if retry_absent else [])
    q = ('SELECT * FROM quest_state WHERE verdict IN (%s) ORDER BY zone, x, z, id'
         % ','.join('?' * len(wanted)))
    rows = db.execute(q, wanted).fetchall()
    return rows[:limit] if limit else rows


def cmd_todo(args):
    db = connect(args.db)
    rows = todo_rows(db, args.retry_absent, args.limit)
    if args.json:
        print(json.dumps([dict(r) for r in rows]))
        return
    for r in rows:
        print(f'{r["area"]:<12} {r["id"]:>4}  zone {r["zone"]:>3}  {r["name"]} ({r["npc"]})')
    print(f'{len(rows)} to check', file=sys.stderr)


def cmd_check(args):
    """Faults in the shape of the data, which no amount of standing on a spot would find.

    A guide that requires a quest the database does not contain sends the player to look for
    something that is not there. Most of these were one bug -- a quest states its own area as
    a directory name (`crystalWar`) and its prerequisite's as a questLog constant
    (`CRYSTAL_WAR`), and only one of the two was being normalized, so 44 cross-referenced
    prerequisites pointed at areas that do not exist. What is left is honest: LandSandBoat
    has no script for those quests, so nothing on this server can require them.
    """
    db = connect(args.db)
    quests = {(r['area'], r['id']): r for r in db.execute('SELECT * FROM quests')}
    rows = quest_table()
    found = []
    for r in rows:
        pre = r.get('prereq')
        if pre and (pre[0], pre[1]) not in quests:
            found.append((r['area'], r['id'], 'prerequisite missing',
                          'requires %s %s, which is not in the database -- this server has '
                          'no script for it' % (pre[0], pre[1])))
    with db:
        db.execute('DELETE FROM issues')
        db.executemany('INSERT OR REPLACE INTO issues VALUES (?,?,?,?)', found)
    print(f'{len(found)} structural issues')
    for a, i, kind, detail in found:
        print(f'   {a:<11} {i:>4}  {kind}: {detail}')


def cmd_export(args):
    db = connect(args.db)
    rows = db.execute('SELECT * FROM quest_state ORDER BY area, id').fetchall()
    out = open(args.out, 'w', newline='', encoding='utf-8') if args.out else sys.stdout
    w = csv.writer(out)
    w.writerow(rows[0].keys() if rows else [])
    for r in rows:
        w.writerow(list(r))
    if args.out:
        out.close()
        print(f'{len(rows)} quests -> {args.out}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[2])
    ap.add_argument('--db', default=DB)
    sub = ap.add_subparsers(dest='cmd', required=True)

    sub.add_parser('init').set_defaults(fn=cmd_init)

    p = sub.add_parser('ingest')
    p.add_argument('csv')
    p.add_argument('--run', default='sweep', help='a name for this sweep')
    p.set_defaults(fn=cmd_ingest)

    sub.add_parser('status').set_defaults(fn=cmd_status)
    sub.add_parser('check').set_defaults(fn=cmd_check)

    p = sub.add_parser('todo')
    p.add_argument('--limit', type=int, default=0)
    p.add_argument('--retry-absent', action='store_true',
                   help='include the ones no NPC answered for -- a short settle looks like this')
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_todo)

    p = sub.add_parser('export')
    p.add_argument('-o', '--out', default='')
    p.set_defaults(fn=cmd_export)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == '__main__':
    sys.exit(main())
