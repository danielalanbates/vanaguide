"""Shared RetroAchievements web API access for the Vanaguide tools.

Everything that talks to retroachievements.org lives here, so the rules are in one place:

* The web API key comes from the environment (RETROACHIEVEMENTS_API_KEY) or the macOS
  Keychain, never from a file in a repository.  It is never printed, and an error that could
  echo the request URL (which carries the key as `y=`) is replaced by a fixed message.
* Every tool can run offline from a fixture directory of saved responses, shaped exactly like
  the documented HTTP responses (PascalCase fields, `Achievements` keyed by id).
* The tools only read.  Nothing here unlocks, submits, or inspects the game.

Copyright (c) 2026 Bates LLC. All rights reserved.
"""

import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://retroachievements.org/API/"
USER_AGENT = "Vanaguide/0.2 (help@batesai.org)"

# The HorizonXI sets on RetroAchievements, in the order their guides are listed.  Game ids,
# from the approved HorizonXI addon RetroAch and hub 25633.  Subsets carry their achievement
# set id too where it is known.
DEFAULT_GAME_IDS = (28275, 28317, 28359, 28303, 28547)
KNOWN_SET_IDS = {28303: 9299, 28547: 9347}

KEY_ENV = "RETROACHIEVEMENTS_API_KEY"
USER_ENV = "RETROACHIEVEMENTS_USER"
# Keychain item: a generic password with this service name (any account).  Override with
# RETROACHIEVEMENTS_KEYCHAIN_SERVICE when the launcher stores it under another name.
KEYCHAIN_SERVICE_ENV = "RETROACHIEVEMENTS_KEYCHAIN_SERVICE"
DEFAULT_KEYCHAIN_SERVICE = "retroachievements.org"


class RAError(Exception):
    """A failure that is safe to print: it never contains the key or the request URL."""


def api_key():
    """The web API key from the environment, else the Keychain, else None."""
    key = os.environ.get(KEY_ENV, "").strip()
    if key:
        return key
    service = os.environ.get(KEYCHAIN_SERVICE_ENV, DEFAULT_KEYCHAIN_SERVICE)
    try:
        out = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-s", service, "-w"],
            capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    key = out.stdout.strip() if out.returncode == 0 else ""
    return key or None


def _get(endpoint, params):
    request = Request(BASE + endpoint + "?" + urlencode(params), headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    except Exception as exc:  # noqa: BLE001 - every failure is reported without the URL
        status = getattr(exc, "code", None)
        if status == 401:
            raise RAError("RetroAchievements answered 401: the web API key is missing or wrong") from None
        detail = f"HTTP {status}" if status else type(exc).__name__
        raise RAError(f"RetroAchievements request to {endpoint} failed ({detail})") from None


class Source:
    """Where responses come from: the live API (needs a key) or a fixture directory.

    Fixture file names:  game-extended-<id>.json  and  progress-<id>.json
    """

    def __init__(self, fixture_dir=None, key=None, save_dir=None):
        self.fixture_dir = Path(fixture_dir) if fixture_dir else None
        self.save_dir = Path(save_dir) if save_dir else None
        self.key = key
        if self.fixture_dir is None and not self.key:
            raise RAError(f"no web API key: set {KEY_ENV} or add it to the Keychain "
                          f"(service '{os.environ.get(KEYCHAIN_SERVICE_ENV, DEFAULT_KEYCHAIN_SERVICE)}')")

    def _load(self, name, endpoint, params):
        if self.fixture_dir is not None:
            path = self.fixture_dir / name
            if not path.exists():
                raise RAError(f"fixture {path} does not exist")
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = _get(endpoint, dict(params, y=self.key))
        if self.save_dir is not None:
            # Responses hold no key, only public set data or the named user's own progress.
            self.save_dir.mkdir(parents=True, exist_ok=True)
            with (self.save_dir / name).open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
                f.write("\n")
        if not isinstance(data, dict):
            raise RAError(f"{name}: expected a JSON object")
        return data

    def game_extended(self, game_id):
        """API_GetGameExtended: the set's full achievement list (official achievements, f=3)."""
        return self._load(f"game-extended-{game_id}.json", "API_GetGameExtended.php",
                          {"i": game_id, "f": 3})

    def progress(self, username, game_id):
        """API_GetGameInfoAndUserProgress: the set plus this user's earned dates."""
        return self._load(f"progress-{game_id}.json", "API_GetGameInfoAndUserProgress.php",
                          {"u": username, "g": game_id})


def achievements_of(game):
    """The Achievements map as a list.  PHP encodes an empty map as [], so accept both."""
    items = game.get("Achievements") or {}
    if isinstance(items, dict):
        return [a for a in items.values() if isinstance(a, dict)]
    if isinstance(items, list):
        return [a for a in items if isinstance(a, dict)]
    return []


def iso_utc(stamp):
    """RetroAchievements writes 'YYYY-MM-DD HH:MM:SS' in UTC; return ISO 8601 with Z, or None."""
    if not stamp or not isinstance(stamp, str):
        return None
    stamp = stamp.strip()
    if len(stamp) == 19 and stamp[10] == " ":
        return stamp.replace(" ", "T") + "Z"
    return stamp


def write_atomically(path, text):
    """Write the whole file or nothing: a reader polling it must never see half of it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)
