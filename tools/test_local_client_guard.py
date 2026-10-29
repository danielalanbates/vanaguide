#!/usr/bin/env python3
"""Offline inventory fixtures only. Never runs a client, server, ps, lsof or command pipe.
Copyright (c) 2026 Bates LLC. All rights reserved. See LICENSE.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("local_client_guard", Path(__file__).with_name("local_client_guard.py"))
guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = guard
SPEC.loader.exec_module(guard)
P = guard.Process
GAME = Path("/fixture/game")
MAP = P(10, "/fixture/lsb/xi_map", "xi_map")
LOCAL = P(20, r".\bootloader\horizon-loader.exe", r".\bootloader\horizon-loader.exe --server 127.0.0.1 --user secret --pass private")


class LocalClientGuardTests(unittest.TestCase):
    def allow(self, processes, **kwargs):
        return guard.authorize(processes, GAME, lambda pid: GAME, **kwargs)

    def test_one_explicit_local_loader_with_bound_install(self):
        self.assertEqual(self.allow([MAP, LOCAL]), 20)

    def test_literal_loopback_only_and_one_server_option(self):
        for command in ["loader --server=127.0.0.1", 'loader --server "::1"']:
            self.assertTrue(guard.explicit_loopback(command))
        for command in ["loader", "loader --server localhost", "loader --server 127.0.0.1.evil",
                        "loader --server 127.0.0.10", "loader --server horizon.example",
                        "loader --server 127.0.0.1 --server horizon.example", "loader --server=",
                        "loader --server 127.0.0.1:54230", "loader --server 127.0.0.1 --server",
                        'loader --pass "--server 127.0.0.1"', 'loader --server "127.0.0.1']:
            self.assertFalse(guard.explicit_loopback(command), command)

    def test_hosted_or_ambiguous_clients_refused(self):
        for clients in [[], [P(20, "horizon-loader.exe", "loader --server login.example")],
                        [P(20, "horizon-loader.exe", "loader")],
                        [LOCAL, P(30, "xiloader.exe", "loader --server remote")],
                        [LOCAL, P(30, "xiloader.exe", "loader --server 127.0.0.1")],
                        [LOCAL, P(30, "Ashita-cli.exe", "Ashita-cli.exe lsb.ini")],
                        [LOCAL, P(30, "unknown-loader.exe", "unknown-loader.exe")],
                        [LOCAL, P(30, "/fixture/wine", "wine other.exe")]]:
            with self.assertRaises(guard.Refused):
                self.allow([MAP] + clients)

    def test_carried_launches_never_count_as_idle_or_bound_clients(self):
        for name in ["x87sidecar-coop", "x87sidecar_entitled", "x87sidecar"]:
            carrier = P(40, "/fixture/" + name,
                        name + " --cooperative wine horizon-loader.exe --server remote --pass private")
            for clients in [[carrier], [LOCAL, carrier]]:
                for mode in [{}, {"require_client": False}, {"require_idle": True}]:
                    with self.subTest(name=name, mode=mode), self.assertRaises(guard.Refused):
                        self.allow([MAP] + clients, **mode)

    def test_carrier_changes_between_snapshots_are_refused(self):
        for names, args in [
            ("10 /fixture/xi_map\n40 /fixture/x87sidecar-coop\n", "10 xi_map\n"),
            ("10 /fixture/xi_map\n", "10 xi_map\n40 /fixture/x87sidecar-coop --cooperative wine loader.exe\n")]:
            with patch.object(guard, "read_command", side_effect=[names, args]):
                with self.assertRaises(guard.Refused): guard.inventory()

    def test_local_map_required_even_if_loader_is_local(self):
        with self.assertRaises(guard.Refused):
            self.allow([LOCAL])

    def test_loader_cwd_must_match_exact_install(self):
        for cwd in [Path("/fixture/game-other"), Path("/fixture/other/game")]:
            with self.assertRaises(guard.Refused):
                guard.authorize([MAP, LOCAL], GAME, lambda pid: cwd)
        with self.assertRaises(guard.Refused):
            guard.authorize([MAP, LOCAL], GAME, lambda pid: (_ for _ in ()).throw(OSError("private details")))

    def test_shell_mentions_and_system_services_are_not_clients(self):
        others = [P(30, "/bin/zsh", "zsh -c echo horizon-loader.exe --server remote"),
                  P(31, "/usr/bin/grep", "grep horizon-loader.exe"),
                  P(32, r"C:\windows\system32\winedevice.exe", "winedevice.exe"),
                  P(33, "/Applications/FFXI-on-Mac.app/Contents/Resources/x87sidecar-coop", "x87sidecar-coop")]
        self.assertEqual(self.allow([MAP, LOCAL] + others), 20)

    def test_idle_rejects_duplicates_and_hosted_clients(self):
        self.assertIsNone(self.allow([MAP], require_client=False, require_idle=True))
        for client in [LOCAL, P(20, "pol.exe", "pol.exe --server remote"), P(20, "injector.exe", "injector.exe")]:
            with self.assertRaises(guard.Refused):
                self.allow([MAP, client], require_client=False, require_idle=True)

    def test_safe_database_mode_still_refuses_hosted_clients(self):
        self.assertIsNone(self.allow([MAP], require_client=False))
        self.assertEqual(self.allow([MAP, LOCAL], require_client=False), 20)
        with self.assertRaises(guard.Refused):
            self.allow([MAP, P(20, "pol.exe", "pol.exe --server remote")], require_client=False)

    def test_changed_inventory_refused_but_ps_itself_is_not_a_client(self):
        with patch.object(guard, "read_command", side_effect=[
            "10 /fixture/lsb/xi_map\n20 horizon-loader.exe\n30 /bin/ps\n",
            "10 xi_map\n20 loader --server 127.0.0.1\n31 /bin/ps -axww -o pid=,args=\n"]):
            self.assertEqual(len(guard.inventory()), 2)
        for args in ["10 xi_map\n", "10 xi_map\n20 loader --server 127.0.0.1\n40 xiloader.exe --server remote\n"]:
            with patch.object(guard, "read_command", side_effect=["10 /fixture/lsb/xi_map\n20 horizon-loader.exe\n", args]):
                with self.assertRaises(guard.Refused):
                    guard.inventory()

    def test_incomplete_process_columns_refused(self):
        for text in ["not a process", "20 loader\n20 other\n"]:
            with self.assertRaises(guard.Refused):
                guard.process_columns(text)

    def test_command_does_not_open_channel_when_check_fails(self):
        with patch.object(guard, "checked", side_effect=guard.Refused("hosted client")), patch.object(guard.os, "open") as opened:
            with self.assertRaises(guard.Refused):
                guard.send(GAME, GAME / "addons/cmdpipe/cmd.txt", "/vg talk NPC")
            opened.assert_not_called()

    def test_unapproved_channel_and_multiline_command_refused_before_write(self):
        for pipe, command in [(Path("/tmp/shared/cmd.txt"), "/shutdown"),
                              (GAME / "addons/cmdpipe/cmd.txt", "/vg status\n!pos 0 0 0"),
                              (GAME / "addons/cmdpipe/cmd.txt", "")]:
            with patch.object(guard, "checked") as checked, patch.object(guard.os, "open") as opened:
                with self.assertRaises(guard.Refused):
                    guard.send(GAME, pipe, command)
                checked.assert_not_called()
                opened.assert_not_called()

    def test_profile_requires_endpoint_in_active_command(self):
        # All writes are dummy fixture files inside this Downloads checkout, never game files.
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            game = Path(folder)
            (game / "config/boot").mkdir(parents=True)
            profile = game / "config/boot/lsb.ini"
            profile.write_text("[ashita.boot]\ncommand=bootloader/xiloader.exe\nargs=--server 127.0.0.1\n")
            guard.verify_profile(game)
            for value in ["# args=--server 127.0.0.1\ncommand=loader --server remote",
                          "command=loader # --server 127.0.0.1", "server=127.0.0.1",
                          "command=loader --server 127.0.0.1\nargs=--server remote"]:
                profile.write_text("[ashita.boot]\n" + value)
                with self.assertRaises(guard.Refused):
                    guard.verify_profile(game)
            profile.write_text("[unrelated]\nargs=--server 127.0.0.1\n")
            with self.assertRaises(guard.Refused):
                guard.verify_profile(game)

    def test_refusals_do_not_print_arguments_or_credentials(self):
        error = io.StringIO()
        with patch.object(guard, "checked", side_effect=guard.Refused("the client is ambiguous")), contextlib.redirect_stderr(error):
            self.assertEqual(guard.main(["guard", "check", str(GAME)]), 1)
        self.assertNotIn("secret", error.getvalue())
        self.assertNotIn("private", error.getvalue())
        self.assertNotIn("--pass", error.getvalue())


if __name__ == "__main__":
    unittest.main()
