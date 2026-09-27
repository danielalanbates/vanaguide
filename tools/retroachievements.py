#!/usr/bin/env python3
"""Read-only RetroAchievements progress snapshot for Vanaguide and its companion.

Writes the same file the HorizonXI-on-Mac launcher writes, in the same shape, so the addon
and the companion can be exercised without the launcher:

    <Ashita install>/config/addons/Vanaguide/retroachievements.json

    { "source": "RetroAchievements", "user": "<name>", "fetched_at": <unix seconds>,
      "games": [ { "game_id": 28275, "title": "...", "earned": N, "total": M,
                   "achievements": { "<id>": { "earned_at": "<iso or null>",
                                               "earned_hardcore_at": "<iso or null>" } } } ] }

    RETROACHIEVEMENTS_API_KEY=... python3 tools/retroachievements.py USER --out PATH
    python3 tools/retroachievements.py USER --fixture tools/fixtures/ra     (offline)

The key comes from the environment or the Keychain (see tools/ra_api.py), never a file.
Nothing here runs inside the game: the addon only ever reads the file this writes.

Copyright (c) 2026 Bates LLC. All rights reserved.
"""

import argparse
import json
import os
import sys
import time

import ra_api


def summarize(game, game_id):
    """One entry of the snapshot's `games` list from a GetGameInfoAndUserProgress response."""
    achievements = {}
    earned = 0
    for item in ra_api.achievements_of(game):
        soft = ra_api.iso_utc(item.get("DateEarned"))
        hard = ra_api.iso_utc(item.get("DateEarnedHardcore"))
        if soft or hard:
            earned += 1
        achievements[str(item["ID"])] = {"earned_at": soft, "earned_hardcore_at": hard}
    return {
        "game_id": int(game.get("ID", game_id)),
        "title": game.get("Title", ""),
        "earned": int(game.get("NumAwardedToUser", earned) or 0),
        "total": int(game.get("NumAchievements", len(achievements)) or 0),
        "achievements": dict(sorted(achievements.items(), key=lambda kv: int(kv[0]))),
    }


def snapshot(source, username, game_ids, now=None):
    return {
        "source": "RetroAchievements",
        "user": username,
        "fetched_at": int(time.time() if now is None else now),
        "games": [summarize(source.progress(username, g), g) for g in game_ids],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("username", nargs="?", default=os.environ.get(ra_api.USER_ENV),
                        help=f"RetroAchievements username or ULID (default: ${ra_api.USER_ENV})")
    parser.add_argument("--game-id", type=int, action="append", dest="game_ids",
                        help="RetroAchievements FFXI game id; repeat for several (default: every HorizonXI set)")
    parser.add_argument("--fixture", metavar="DIR", help="read saved responses from DIR instead of the network")
    parser.add_argument("--save", metavar="DIR", help="also save each raw response into DIR")
    parser.add_argument("--out", metavar="PATH", help="write the snapshot here (atomically) instead of stdout")
    parser.add_argument("--now", type=int, help=argparse.SUPPRESS)   # tests pin fetched_at
    args = parser.parse_args(argv)
    if not args.username:
        parser.error(f"give a username or set {ra_api.USER_ENV}")
    try:
        key = None if args.fixture else ra_api.api_key()
        source = ra_api.Source(fixture_dir=args.fixture, key=key, save_dir=args.save)
        snap = snapshot(source, args.username, args.game_ids or ra_api.DEFAULT_GAME_IDS, args.now)
    except (ra_api.RAError, OSError, ValueError, KeyError, TypeError) as exc:
        message = str(exc) if isinstance(exc, ra_api.RAError) else type(exc).__name__
        print(f"RetroAchievements export failed: {message}", file=sys.stderr)
        return 1
    text = json.dumps(snap, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        ra_api.write_atomically(args.out, text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
