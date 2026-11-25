#!/usr/bin/env python3
"""Generate Vanaguide/data/achievements.lua from the RetroAchievements FFXI sets.

    RETROACHIEVEMENTS_API_KEY=... python3 tools/gen_achievements.py            (live, every set)
    python3 tools/gen_achievements.py --fixture tools/fixtures/ra --out /tmp/a.lua   (offline)
    python3 tools/gen_achievements.py --placeholder         (the empty file shipped until a key exists)

For every set it writes each achievement's id, title, description, points, type, badge,
display order and game (and set) id, plus a best-effort mapping onto something the guide can
point at or check: a quest or mission (from data/quests.lua and data/missions.lua), a job or
main level, a nation rank, an item, a notorious monster (data/nm.lua), or a zone.  Each
mapping carries a confidence between 0 and 1 and the rule that produced it; below
COMPLETE_AT the guide uses it only as a place to go, never as a completion condition.
Achievements nothing matches keep only their description.

Output is deterministic: sets in the order given, achievements by display order then id,
fields in a fixed order.  Hand corrections go in tools/achievement_overrides.json
({"<achievement id>": {"kind": "key_item", "ki": 123}, ...}) and win with confidence 1.0.

Copyright (c) 2026 Bates LLC. All rights reserved.
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import ra_api

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "Vanaguide" / "data"
DEFAULT_OUT = DATA / "achievements.lua"
DEFAULT_OVERRIDES = Path(__file__).resolve().parent / "achievement_overrides.json"

# At or above this the guide step gets the mapping's completion tag; below it, only its place.
COMPLETE_AT = 0.75
# Below this a match is noise and is dropped.
KEEP_AT = 0.5

JOBS = {
    "warrior": 1, "war": 1, "monk": 2, "mnk": 2, "white mage": 3, "whm": 3, "black mage": 4, "blm": 4,
    "red mage": 5, "rdm": 5, "thief": 6, "thf": 6, "paladin": 7, "pld": 7, "dark knight": 8, "drk": 8,
    "beastmaster": 9, "bst": 9, "bard": 10, "brd": 10, "ranger": 11, "rng": 11, "samurai": 12, "sam": 12,
    "ninja": 13, "nin": 13, "dragoon": 14, "drg": 14, "summoner": 15, "smn": 15, "blue mage": 16, "blu": 16,
    "corsair": 17, "cor": 17, "puppetmaster": 18, "pup": 18, "dancer": 19, "dnc": 19, "scholar": 20,
    "sch": 20, "geomancer": 21, "geo": 21, "rune fencer": 22, "run": 22,
}
NATIONS = {"san doria": "sandoria", "sandoria": "sandoria", "bastok": "bastok", "windurst": "windurst"}
NATION_LABEL = {"sandoria": "San d'Oria", "bastok": "Bastok", "windurst": "Windurst"}
KIND_ORDER = {"override": 0, "mission": 1, "quest": 2, "job": 3, "level": 4, "rank": 5,
              "key_item": 6, "item": 7, "nm": 8, "zone": 9}


# ---- a reader for the literal tables in the generated data files ----------------------------

class LuaTableReader:
    """Parses one Lua table constructor of literals: strings, numbers, booleans, nil, nested
    tables, `[n] =` and `name =` keys.  That is all the generated data files contain."""

    _token = re.compile(r"""
        (?P<ws>\s+|--[^\n]*) |
        (?P<num>-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?) |
        (?P<name>[A-Za-z_][A-Za-z0-9_]*) |
        (?P<str>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*") |
        (?P<sym>[{}\[\]=,;])
    """, re.X | re.S)

    def __init__(self, text, pos):
        self.tokens = []
        while pos < len(text):
            m = self._token.match(text, pos)
            if m is None:
                break
            pos = m.end()
            kind = m.lastgroup
            if kind == "ws":
                continue
            self.tokens.append((kind, m.group(kind)))
            if kind == "sym" and m.group(kind) == "}" and self._closed():
                break
        self.i = 0

    def _closed(self):
        depth = 0
        for kind, value in self.tokens:
            if kind == "sym" and value == "{":
                depth += 1
            elif kind == "sym" and value == "}":
                depth -= 1
        return depth == 0

    def _next(self):
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def _peek(self, offset=0):
        j = self.i + offset
        return self.tokens[j] if j < len(self.tokens) else (None, None)

    @staticmethod
    def _unquote(s):
        body = s[1:-1]
        return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), body)

    def value(self):
        kind, tok = self._next()
        if kind == "num":
            return float(tok) if any(c in tok for c in ".eE") else int(tok)
        if kind == "str":
            return self._unquote(tok)
        if kind == "name":
            return {"true": True, "false": False, "nil": None}.get(tok, tok)
        if tok == "{":
            return self._table()
        raise ValueError(f"unexpected token {tok!r}")

    def _table(self):
        array, mapping = [], {}
        while True:
            kind, tok = self._peek()
            if tok == "}":
                self._next()
                break
            if tok == "[":
                self._next()
                key = self.value()
                self._next()      # ]
                self._next()      # =
                mapping[key] = self.value()
            elif kind == "name" and self._peek(1)[1] == "=":
                self._next()
                self._next()
                mapping[tok] = self.value()
            else:
                array.append(self.value())
            if self._peek()[1] in (",", ";"):
                self._next()
        if mapping and array:
            mapping.update({i + 1: v for i, v in enumerate(array)})
            return mapping
        return mapping if mapping else array


def read_table(path, assignment):
    """The table assigned by `<assignment> = {` in a data file, as Python dicts and lists."""
    text = Path(path).read_text(encoding="utf-8")
    m = re.search(r"^" + re.escape(assignment) + r"\s*=\s*(?=\{)", text, re.M)
    if m is None:
        raise ValueError(f"{path}: no '{assignment} = {{'")
    return LuaTableReader(text, m.end()).value()


# ---- text ---------------------------------------------------------------------------------

def ascii_text(s):
    """What FFXI's and ImGui's fonts can draw: accents dropped, typographic marks made plain."""
    if s is None:
        return ""
    s = str(s)
    for a, b in (("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'),
                 ("\u2013", "-"), ("\u2014", "-"), ("\u2026", "..."), ("\u00a0", " ")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    """Lower case, apostrophes dropped (the data files spell "Morganas" and "Morgana's"
    both ways), everything else that is not a letter or digit a single space."""
    s = ascii_text(s).lower().replace("'", "").replace("`", "")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def contains_phrase(haystack_norm, needle_norm):
    return bool(needle_norm) and f" {needle_norm} " in f" {haystack_norm} "


def quoted_phrases(text):
    text = ascii_text(text)
    out = re.findall(r'"([^"]{3,80})"', text)
    out += re.findall(r"(?<![A-Za-z])'([^']{3,80}?)'(?![A-Za-z])", text)
    return [norm(p) for p in out]


# ---- the game data the achievements are matched against ------------------------------------

class GameData:
    def __init__(self, data_dir=DATA):
        data_dir = Path(data_dir)
        quests = read_table(data_dir / "quests.lua", "Q.quests")
        missions = read_table(data_dir / "missions.lua", "M.missions")
        nms = read_table(data_dir / "nm.lua", "N.list")
        zones = read_table(data_dir / "zone_names.lua", "Z.name")
        gear = read_table(data_dir / "gear.lua", "G.items")
        drops = read_table(data_dir / "drops.lua", "D.sources")
        vendors = read_table(data_dir / "vendors.lua", "V.sold_by")

        self.quests = {}      # norm name -> [target]
        for area in sorted(quests):
            for qid in sorted(quests[area]):
                q = quests[area][qid]
                self._add(self.quests, q.get("name"), dict(
                    kind="quest", area=area, id=qid, name=q.get("name"),
                    zone=q.get("zone"), x=q.get("x"), z=q.get("z")))
        self.missions = {}
        self.mission_labels = {}   # (nation, a, b) -> target
        for area in sorted(missions):
            for mid in sorted(missions[area]):
                m = missions[area][mid]
                target = dict(kind="mission", area=area, id=mid, name=m.get("name"),
                              zone=m.get("zone"), x=m.get("x"), z=m.get("z"))
                self._add(self.missions, m.get("name"), target)
                lab = re.match(r"(.+?) M(\d+)-(\d+)", ascii_text(m.get("label") or ""))
                if lab and norm(lab.group(1)) in NATIONS:
                    key = (NATIONS[norm(lab.group(1))], int(lab.group(2)), int(lab.group(3)))
                    # A numbered mission can be several ids (2-3 is one per route and part).
                    # The place is where the first one starts; the id is the last one, because
                    # `M` completes when the current mission passes it and every route ends
                    # before the next number begins.
                    first = self.mission_labels.setdefault(key, dict(target))
                    first["id"] = max(first["id"], mid)
                    if first["id"] != mid or first.get("routes"):
                        # Several ids share this number (2-3 has one per route): which one a
                        # player finishes depends on their route, so no single id can tick it.
                        first["routes"] = True
        self.nms = {}
        for n in nms:
            self._add(self.nms, n.get("name"), dict(kind="nm", name=n.get("name"), zone=n.get("zone"),
                                                    x=n.get("x"), z=n.get("z")))
        self.zones = {}
        for zid in sorted(zones):
            name = zones[zid]
            if zid and len(norm(name)) >= 5 and name != "unknown":
                self._add(self.zones, name, dict(kind="zone", zone=zid, name=name))
        self.items = {}
        for iid in sorted(gear):
            row = gear[iid]
            name = row[1] if isinstance(row, dict) else row[0]
            target = dict(kind="item", item=iid, name=name)
            place = self._item_place(iid, drops, vendors)
            if place:
                target.update(place)
            self._add(self.items, name, target)

    @staticmethod
    def _add(index, name, target):
        key = norm(name)
        if key:
            index.setdefault(key, []).append(target)

    @staticmethod
    def _item_place(iid, drops, vendors):
        for src in drops.get(iid, []):
            row = [src[k] for k in sorted(src)] if isinstance(src, dict) else src
            if len(row) >= 6 and (row[4], row[5]) != (0.0, 0.0):
                return dict(zone=row[1], x=row[4], z=row[5], source=row[0])
        for src in vendors.get(iid, []):
            row = [src[k] for k in sorted(src)] if isinstance(src, dict) else src
            if len(row) >= 5 and (row[3], row[4]) != (0.0, 0.0):
                return dict(zone=row[1], x=row[3], z=row[4], source=row[0])
        return None


# ---- matching -----------------------------------------------------------------------------

def _pick(targets):
    """One target from a same-name list, and whether the name was ambiguous.  Entries that are
    the same place (a notorious monster listed once per spawn) are not ambiguity."""
    places = {(t.get("kind"), t.get("area"), t.get("zone")) for t in targets}
    ambiguous = len(places) > 1
    ranked = sorted(targets, key=lambda t: (t.get("x") is None, str(t.get("area")), t.get("zone") or 0,
                                            t.get("id") or 0))
    return ranked[0], ambiguous


def candidates(ach, data):
    title, desc = ach["title"], ach["description"]
    t_norm, d_norm = norm(title), norm(desc)
    both = f"{t_norm} {d_norm}"
    quoted = quoted_phrases(desc) + quoted_phrases(title)
    says_quest = " quest" in f" {d_norm}"
    says_mission = " mission" in f" {d_norm}"
    says_kill = any(w in f" {d_norm} " for w in (" defeat ", " kill ", " slay ", " vanquish ", " defeating "))
    says_get = any(w in f" {d_norm} " for w in (" obtain ", " acquire ", " receive ", " equip ", " get "))
    out = []

    def add(conf, method, target, name_len=0):
        if conf >= KEEP_AT:
            out.append((round(conf, 2), method, target, name_len))

    # Nation missions by number: "Complete Bastok Mission 2-3".
    for m in re.finditer(r"\b(san doria|sandoria|bastok|windurst) (?:mission |m)(\d{1,2}) (\d{1,2})\b", d_norm):
        key = (NATIONS[m.group(1)], int(m.group(2)), int(m.group(3)))
        target = data.mission_labels.get(key)
        if target:
            # A number shared by several route-dependent ids stays a hint (below 0.75): no
            # single id can tick it for every route.
            add(0.6 if target.get("routes") else 0.9, "nation-mission-number", target, 99)

    # Job and level: "Reach level 30 as a Paladin", "Get Warrior to level 75", "Reach level 75".
    job_names = "|".join(sorted((re.escape(j) for j in JOBS), key=len, reverse=True))
    m = (re.search(rf"level (\d{{1,2}}) (?:as |on |with )?(?:an? )?({job_names})\b", d_norm)
         or re.search(rf"\b({job_names}) (?:to |at |reaches |reach )?level (\d{{1,2}})", d_norm))
    if m:
        lvl, job = (m.group(1), m.group(2)) if m.group(1).isdigit() else (m.group(2), m.group(1))
        add(0.85, "job-level", dict(kind="job", job=JOBS[job], level=int(lvl)), 99)
    else:
        m = re.search(r"\b(?:reach|attain|hit|get to) (?:character |main job )?level (\d{1,2})\b", d_norm)
        if m:
            add(0.85, "level", dict(kind="level", level=int(m.group(1))), 99)
    m = re.search(r"\b(?:reach|attain|obtain|achieve) (?:nation |national )?rank (\d{1,2})\b", d_norm)
    if m:
        add(0.85, "rank", dict(kind="rank", rank=int(m.group(1))), 99)

    # Named quests, missions, monsters and items.
    for index, kind in ((data.missions, "mission"), (data.quests, "quest"), (data.nms, "nm"), (data.items, "item")):
        keyword = {"mission": says_mission, "quest": says_quest, "nm": says_kill, "item": says_get}[kind]
        for name, targets in index.items():
            target, ambiguous = _pick(targets)
            penalty = 0.15 if ambiguous else 0.0
            words = len(name.split())
            if name in quoted:
                conf, method = (0.9 if keyword or kind in ("quest", "mission") else 0.8), "quoted-name"
            elif name == t_norm and words >= 2:
                conf, method = (0.85 if keyword else 0.7), "title-is-name"
            elif contains_phrase(d_norm, name) and (words >= 2 and len(name) >= 8):
                conf, method = (0.8 if keyword else 0.6), "name-in-description"
            elif contains_phrase(d_norm, name) and keyword and len(name) >= 5:
                conf, method = 0.6, "short-name-in-description"
            else:
                continue
            if kind == "item" and not keyword:
                conf -= 0.1
            add(conf - penalty, method + ("-ambiguous" if ambiguous else ""), target, len(name))

    # A zone, as a place to go only.
    for name, targets in data.zones.items():
        if contains_phrase(both, name) and len(name) >= 6:
            add(0.5, "zone-named", targets[0], len(name))
    return out


def best_mapping(ach, data, overrides):
    override = overrides.get(str(ach["id"]))
    if override:
        return dict(override, confidence=1.0, method="override")
    found = candidates(ach, data)
    if not found:
        return None

    def key(c):
        conf, method, target, name_len = c
        return (-conf, -name_len, KIND_ORDER.get(target["kind"], 99), str(target.get("area", "")),
                target.get("id") or target.get("zone") or 0)
    found.sort(key=key)
    conf, method, target, _ = found[0]
    # Two different things at the top score: the description names both, and neither is
    # clearly the achievement.  Keep the first as a place, not as a condition.
    rivals = {(c[2]["kind"], c[2].get("area"), c[2].get("id"), c[2].get("name"), c[2].get("zone"),
               c[2].get("job"), c[2].get("level"), c[2].get("rank"), c[2].get("item"))
              for c in found if c[0] == conf}
    if len(rivals) > 1:
        conf = min(conf, COMPLETE_AT - 0.05)
        method += "-rival"
    mapping = {k: v for k, v in target.items() if v is not None and k != "source"}
    mapping.update(confidence=round(conf, 2), method=method)
    return mapping


# ---- building the data --------------------------------------------------------------------

def subset_name(title):
    m = re.search(r"\[Subset\s*-\s*(.+?)\]", title)
    return m.group(1).strip() if m else title


def build_sets(source, game_ids, data, overrides):
    sets = []
    for game_id in game_ids:
        try:
            game = source.game_extended(game_id)
        except ra_api.RAError as err:
            # One retired or renumbered set must not cost the others: say so and carry on.
            print(f"skipping game {game_id}: {err}", file=sys.stderr)
            continue
        if not isinstance(game, dict) or game.get("ID") is None:
            print(f"skipping game {game_id}: RetroAchievements returned no game", file=sys.stderr)
            continue
        title = ascii_text(game.get("Title") or f"Game {game_id}")
        achievements = []
        for a in ra_api.achievements_of(game):
            ach = {
                "id": int(a["ID"]),
                "title": ascii_text(a.get("Title")),
                "description": ascii_text(a.get("Description")),
                "points": int(a.get("Points") or 0),
                "type": a.get("type") or None,
                "badge": str(a.get("BadgeName") or ""),
                "order": int(a.get("DisplayOrder") or 0),
                "game_id": int(game.get("ID", game_id)),
            }
            ach["map"] = best_mapping(ach, data, overrides)
            achievements.append(ach)
        achievements.sort(key=lambda a: (a["order"], a["id"]))
        sets.append({
            "game_id": int(game.get("ID", game_id)),
            "set_id": ra_api.KNOWN_SET_IDS.get(int(game.get("ID", game_id))),
            "parent_id": game.get("ParentGameID"),
            "title": title,
            "name": subset_name(title),
            "points": sum(a["points"] for a in achievements),
            "achievements": achievements,
        })
    return sets


# ---- writing Lua --------------------------------------------------------------------------

def lua(v):
    if v is None:
        return "nil"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return f"{v:.1f}" if abs(v - round(v, 1)) < 1e-9 else repr(round(v, 3))
    s = str(v).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
    return f"'{s}'"


MAP_FIELDS = ("kind", "area", "id", "name", "job", "level", "rank", "ki", "item", "count",
              "zone", "x", "z", "confidence", "method")
ACH_FIELDS = ("id", "title", "description", "points", "type", "badge", "order", "game_id")


def fields(obj, order):
    return ", ".join(f"{k} = {lua(obj[k])}" for k in order if obj.get(k) is not None)


def render(sets, origin):
    lines = [
        "-- Vanaguide :: data/achievements.lua",
        "-- GENERATED by tools/gen_achievements.py from the RetroAchievements FFXI sets.  Do not hand-edit;",
        "-- correct a mapping in tools/achievement_overrides.json and regenerate.",
        f"-- Source: {origin}",
        "--",
        "-- One entry per set, in guide order.  Per achievement: id, title, description, points, type",
        "-- (progression / win_condition / missable, or nil), badge, order (RetroAchievements display",
        "-- order), game_id, and `map` when the description names something the guide knows:",
        "--   kind        quest | mission | job | level | rank | key_item | item | nm | zone",
        "--   area, id    quest or mission key;  job, level;  rank;  ki;  item, count;  name",
        "--   zone, x, z  where to go, when known",
        "--   confidence  0..1; guides/achievements.lua turns it into a completion tag only at >= "
        f"{COMPLETE_AT}",
        "--   method      the rule that matched",
        "--",
        "-- Achievement text is RetroAchievements' own; progress is never stored here (the launcher",
        "-- writes config/addons/Vanaguide/retroachievements.json).  See docs/RETROACHIEVEMENTS.md.",
        "--",
        "-- Copyright (c) 2026 Bates LLC. All rights reserved.",
        "",
        "local A = {}",
        "",
        f"A.complete_at = {COMPLETE_AT}",
        "",
        "A.sets = {",
    ]
    for s in sets:
        head = fields(s, ("game_id", "set_id", "parent_id", "title", "name", "points"))
        lines.append(f"    {{ {head}, achievements = {{")
        for a in s["achievements"]:
            body = fields(a, ACH_FIELDS)
            if a.get("map"):
                body += f", map = {{ {fields(a['map'], MAP_FIELDS)} }}"
            lines.append(f"        {{ {body} }},")
        lines.append("    } },")
    lines += [
        "}",
        "",
        "A.by_id = {}",
        "for _, set in ipairs(A.sets) do",
        "    for _, a in ipairs(set.achievements) do A.by_id[a.id] = a end",
        "end",
        "",
        "--- One achievement by its RetroAchievements id, or nil.",
        "function A.get(id) return A.by_id[tonumber(id)] end",
        "",
        "return A",
        "",
    ]
    return "\n".join(lines)


def load_overrides(path):
    path = Path(path)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): v for k, v in data.items() if not str(k).startswith("_")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--game-id", type=int, action="append", dest="game_ids",
                        help="RetroAchievements game id; repeat (default: every HorizonXI set)")
    parser.add_argument("--fixture", metavar="DIR", help="read game-extended-<id>.json files from DIR")
    parser.add_argument("--save", metavar="DIR", help="also save each raw response into DIR")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="where to write (default: %(default)s)")
    parser.add_argument("--data", default=str(DATA), help="the addon's data directory to match against")
    parser.add_argument("--overrides", default=str(DEFAULT_OVERRIDES), help="hand mappings (JSON)")
    parser.add_argument("--placeholder", action="store_true",
                        help="write the empty file shipped before any set has been fetched")
    args = parser.parse_args(argv)

    if args.placeholder:
        text = render([], "nothing yet - no RetroAchievements web API key has been used to generate this file")
        ra_api.write_atomically(args.out, text)
        return 0
    game_ids = args.game_ids or list(ra_api.DEFAULT_GAME_IDS)
    try:
        key = None if args.fixture else ra_api.api_key()
        source = ra_api.Source(fixture_dir=args.fixture, key=key, save_dir=args.save)
        data = GameData(args.data)
        sets = build_sets(source, game_ids, data, load_overrides(args.overrides))
    except (ra_api.RAError, OSError, ValueError, KeyError, TypeError) as exc:
        message = str(exc) if isinstance(exc, (ra_api.RAError, ValueError)) else type(exc).__name__
        print(f"gen_achievements failed: {message}", file=sys.stderr)
        return 1
    origin = ("fixtures in " + Path(args.fixture).name + " (NOT RetroAchievements data)") if args.fixture \
        else "RetroAchievements web API, API_GetGameExtended, games " + ", ".join(map(str, game_ids))
    ra_api.write_atomically(args.out, render(sets, origin))
    total = sum(len(s["achievements"]) for s in sets)
    mapped = sum(1 for s in sets for a in s["achievements"] if a["map"])
    sure = sum(1 for s in sets for a in s["achievements"] if a["map"] and a["map"]["confidence"] >= COMPLETE_AT)
    print(f"{len(sets)} sets, {total} achievements, {mapped} mapped ({sure} at >= {COMPLETE_AT}) -> {args.out}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
