#!/usr/bin/env python3
"""Read-only RetroAchievements progress export for the Vanaguide companion.

Copyright (c) 2026 Bates LLC. All rights reserved.
"""

import argparse
import json
import os
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API = "https://retroachievements.org/API/API_GetGameInfoAndUserProgress.php"
DEFAULT_GAME_IDS = (28275,)


def fetch_progress(username, api_key, game_id):
    query = urlencode({"y": api_key, "u": username, "g": game_id})
    request = Request(f"{API}?{query}", headers={"User-Agent": "Vanaguide/0.2 (help@batesai.org)"})
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def summarize(game):
    achievements = []
    for item in game.get("Achievements", {}).values():
        achievements.append({
            "id": item["ID"],
            "title": item["Title"],
            "description": item.get("Description", ""),
            "points": item.get("Points", 0),
            "type": item.get("type"),
            "earned_at": item.get("DateEarned"),
            "earned_hardcore_at": item.get("DateEarnedHardcore"),
        })
    achievements.sort(key=lambda item: (item["earned_at"] is not None, item["title"].casefold()))
    return {
        "game_id": game["ID"],
        "title": game["Title"],
        "earned": game.get("NumAwardedToUser", 0),
        "total": game.get("NumAchievements", len(achievements)),
        "achievements": achievements,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username", help="RetroAchievements username or ULID")
    parser.add_argument("--game-id", type=int, action="append", dest="game_ids",
                        help="RetroAchievements FFXI set ID; repeat for expansion sets")
    args = parser.parse_args()
    api_key = os.environ.get("RETROACHIEVEMENTS_API_KEY")
    if not api_key:
        parser.error("set RETROACHIEVEMENTS_API_KEY in the environment")
    try:
        games = [summarize(fetch_progress(args.username, api_key, game_id))
                 for game_id in (args.game_ids or DEFAULT_GAME_IDS)]
    except (OSError, ValueError, KeyError):
        # Some URL errors include the full request URL, which contains the API key.
        print("RetroAchievements request failed; check network, account, key, and game ID", file=sys.stderr)
        return 1
    json.dump({"source": "RetroAchievements", "user": args.username, "games": games}, sys.stdout,
              ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
