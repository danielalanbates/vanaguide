#!/usr/bin/env python3
"""Fail-closed authorization for the local-only test harnesses.

Process arguments are inspected in memory and never printed. There is no environment or
command-line bypass. Import the pure inventory functions for offline fixture tests.
Copyright (c) 2026 Bates LLC. All rights reserved. See LICENSE.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable


class Refused(Exception):
    pass


@dataclass(frozen=True)
class Process:
    pid: int
    executable: str
    arguments: str


LOADERS = {"horizon-loader.exe", "xiloader.exe", "gxiloader.exe", "catseye-loader.exe", "pol.exe"}
INJECTORS = {"ashita-cli.exe", "injector.exe"}
CARRIERS = {"x87sidecar-coop", "x87sidecar_entitled", "x87sidecar"}
WINE = {"wine", "wine64", "wine-preloader", "wine64-preloader"}
SYSTEM = {"services.exe", "explorer.exe", "winedevice.exe", "plugplay.exe", "svchost.exe",
          "rpcss.exe", "tabtip.exe", "conhost.exe", "start.exe", "winemenubuilder.exe",
          "regsvr32.exe", "reg.exe", "regedit.exe", "wineboot.exe"}
LOOPBACK = {"127.0.0.1", "::1"}


def basename(executable: str) -> str:
    return executable.strip().strip('"\'').replace("\\", "/").rsplit("/", 1)[-1].lower()


def explicit_loopback(arguments: str) -> bool:
    try:
        tokens = shlex.split(arguments)
    except ValueError:
        return False
    servers = []
    for index, token in enumerate(tokens):
        if token == "--server":
            servers.append(tokens[index + 1] if index + 1 < len(tokens) else "")
        elif token.startswith("--server="):
            servers.append(token.partition("=")[2])
    return len(servers) == 1 and servers[0] in LOOPBACK


def game_kind(process: Process) -> str | None:
    """Recognize executable identity, never a shell/grep merely mentioning a loader."""
    name = basename(process.executable)
    if name in CARRIERS:
        # Cooperative carriers can remain visible before a separate Wine loader appears.
        # Their embedded command is not enough evidence to bind command delivery to a client.
        if "--cooperative" in process.arguments or re.search(r"(?i)\.exe(?:[\s\"']|$)", process.arguments):
            return "ambiguous"
        return None  # standalone help/probe tools do not launch a game
    if name in LOADERS:
        return "loader"
    if name in INJECTORS:
        return "ambiguous"
    if name.endswith(".exe"):
        # A system-named executable outside Wine's system directory is ambiguous too.
        path = process.executable.replace("\\", "/").lower()
        if name in SYSTEM and (path.startswith("c:/windows/") or path == name):
            return None
        return "ambiguous"
    if name in WINE:
        programs = re.findall(r'(?i)(?:^|[\s/\\"\'])([a-z0-9_.-]+\.exe)(?=$|[\s"\'])', process.arguments)
        if len(programs) != 1:
            return "ambiguous"
        program = programs[0].lower()
        if program in SYSTEM:
            return None
        # A preloader's executable is not the game. Its endpoint/cwd cannot establish which
        # eventual child will receive commands, so wait for the actual loader process.
        return "ambiguous"
    return None


def authorize(processes: list[Process], game: Path, cwd: Callable[[int], Path], *,
              require_client: bool = True, require_idle: bool = False) -> int | None:
    """Pure policy over an injected snapshot and cwd reader. Raises only sanitized reasons."""
    if not any(basename(p.executable) == "xi_map" for p in processes):
        raise Refused("the local xi_map server is not running")
    clients = [(p, game_kind(p)) for p in processes if game_kind(p) is not None]
    if require_idle:
        if clients:
            raise Refused("a game client is already running or starting")
        return None
    if not clients and not require_client:
        return None
    if len(clients) != 1 or clients[0][1] != "loader":
        raise Refused("exactly one unambiguous local loader is required")
    client = clients[0][0]
    if not explicit_loopback(client.arguments):
        raise Refused("the game client has no single explicit loopback --server")
    try:
        bound = cwd(client.pid).resolve() == game.resolve()
    except (OSError, ValueError):
        raise Refused("the game client's install folder could not be verified") from None
    if not bound:
        raise Refused("the local loader belongs to another or an unverifiable install")
    return client.pid


def read_command(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise Refused("the process inventory could not be verified") from None
    if result.returncode:
        raise Refused("the process inventory could not be verified")
    return result.stdout


def process_columns(text: str) -> dict[int, str]:
    rows: dict[int, str] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"\s*([0-9]+)\s+(.+)", line)
        if not match or int(match[1]) in rows:
            raise Refused("the process inventory was incomplete")
        rows[int(match[1])] = match[2]
    return rows


def inventory() -> list[Process]:
    names = process_columns(read_command(["/bin/ps", "-axww", "-o", "pid=,comm="]))
    args = process_columns(read_command(["/bin/ps", "-axww", "-o", "pid=,args="]))
    result = []
    for pid, name in names.items():
        # A loader/injector that vanished between the two snapshots is uncertainty, not idle.
        if pid not in args and (basename(name).endswith(".exe") or basename(name) in WINE | CARRIERS):
            raise Refused("a game process changed during verification")
        if pid in args:
            result.append(Process(pid, name, args[pid]))
    # A newly started process is equally unsafe. Let a subsequent explicit invocation retry.
    if any(pid not in names and re.search(r"(?i)\.exe(?:\s|$)|(?:^|/)(?:wine(?:64)?|x87sidecar(?:-coop|_entitled)?)(?:\s|$)", arguments)
           for pid, arguments in args.items()):
        raise Refused("a process started during verification; try again when idle")
    return result


def process_cwd(pid: int) -> Path:
    records = read_command(["/usr/sbin/lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"])
    paths = [line[1:] for line in records.splitlines() if line.startswith("n")]
    if len(paths) != 1:
        raise Refused("the game client's install folder could not be verified")
    return Path(paths[0])


def verify_profile(game: Path) -> None:
    try:
        text = (game / "config/boot/lsb.ini").read_text()
    except (OSError, UnicodeError):
        raise Refused("the local boot profile could not be verified") from None
    # Ignore commented lines and unrelated settings. The loader's command/args must carry the
    # endpoint; a comment saying 'local' or a separately named server field is not evidence.
    commands = []
    section = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip().lower()
            continue
        if section != "ashita.boot" or not stripped or stripped.startswith(("#", ";")) or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip().lower() in {"command", "args", "arguments"}:
            commands.append(value.split("#", 1)[0].split(";", 1)[0].strip())
    if not explicit_loopback(" ".join(commands)):
        raise Refused("lsb.ini must explicitly name one loopback --server")


def checked(game: Path, mode: str = "check") -> int | None:
    if not game.is_dir():
        raise Refused("the requested game install is missing")
    pid = authorize(inventory(), game, process_cwd,
                    require_client=mode not in {"safe", "idle", "start"},
                    require_idle=mode in {"idle", "start"})
    if mode == "start":
        verify_profile(game)
    return pid


def send(game: Path, pipe: Path, command: str) -> None:
    # Only the two documented cmdpipe locations in this install. An addon symlink leading
    # outside the install is refused; copy test addons into an isolated local install instead.
    allowed = {game / "addons/cmdpipe/cmd.txt", game / "addons/Vanaguide/cmd.txt"}
    if pipe not in allowed or not pipe.resolve().is_relative_to(game.resolve()):
        raise Refused("the command channel is outside the verified install")
    if not command or len(command) > 4096 or "\n" in command or "\r" in command:
        raise Refused("the test command must be one nonempty line")
    checked(game)  # Immediately before opening/writing the command channel.
    try:
        fd = os.open(pipe, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(command + "\n")
    except OSError:
        raise Refused("the verified command channel could not be written") from None


def main(argv: list[str]) -> int:
    try:
        if len(argv) < 3 or argv[1] not in {"check", "pid", "safe", "idle", "start", "send"}:
            raise Refused("usage: local_client_guard.py check|pid|safe|idle|start <game> or send <game> <pipe> <command>")
        mode, game = argv[1], Path(argv[2]).absolute()
        if mode == "send":
            if len(argv) != 5:
                raise Refused("a command channel and single-line command are required")
            send(game, Path(argv[3]).absolute(), argv[4])
        else:
            pid = checked(game, "check" if mode == "pid" else mode)
            if mode == "pid":
                print(pid)
        return 0
    except Refused as refusal:
        print(f"Local test refused: {refusal}.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
