#!/usr/bin/env python3
"""Offline shell fixtures: no Wine, database, process inventory, sleeps or game commands.

Copyright (c) 2026 Bates LLC. All rights reserved. See LICENSE.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.directory.cleanup)
        self.game = Path(self.directory.name) / "prefix/drive_c/Local World"
        self.game.mkdir(parents=True)

    def run_fixture(self, body, *, game=None, port="3306"):
        environment = dict(os.environ, VG_DBPORT=port, VG_GAME=str(game or self.game),
                           VG_CLIENT_SCRIPT=str(Path(__file__).with_name("client.sh").resolve()))
        return subprocess.run(["/bin/zsh", "-fc", '''
source "$VG_CLIENT_SCRIPT"
guard(){ :; }
stop(){ :; }
sleep(){ :; }
send(){ print -r -- "SENT:$1"; }
start(){ print -r -- STARTED; }
''' + body], env=environment, text=True, capture_output=True, timeout=5)

    def test_private_database_port_is_validated_before_actions(self):
        for port in ["1", "3306", "47949", "65535"]:
            result = self.run_fixture('print -r -- "$DB_PORT"', port=port)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), port)
        for port in ["0", "65536", "-1", "remote", "3306;touch nope", "999999999999999999999"]:
            result = self.run_fixture('print UNEXPECTED', port=port)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("UNEXPECTED", result.stdout)
            self.assertIn("database port", result.stderr)

    def test_sql_passes_private_port_to_loopback_client(self):
        password = Path(self.directory.name) / "fixture-password"
        password.write_text("fixture-only")
        result = self.run_fixture('''
DB_PASS_FILE="${VG_GAME:h:h:h}/fixture-password"
function /opt/homebrew/opt/mariadb/bin/mariadb() {
    printf '%s\\n' "$@"
}
sql 'select 1;'
''', port="47949")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--host=127.0.0.1", result.stdout.splitlines())
        self.assertIn("--port=47949", result.stdout.splitlines())
        self.assertNotIn("fixture-only", result.stdout)

    def test_isolated_install_paths_follow_game_folder(self):
        result = self.run_fixture('printf "%s\\n" "$PIVOT" "$POINTERS" "$WINDOWS_GAME"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [str(self.game / "config/pivot"),
                         str(self.game / "config/ashita/custom.pointers.ini"), r"C:\Local World"])

    def test_non_drive_c_install_refused_before_actions(self):
        result = self.run_fixture('print UNEXPECTED', game=Path(self.directory.name) / "other")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("UNEXPECTED", result.stdout)

    def test_existing_hide_state_is_not_toggled(self):
        result = self.run_fixture('sql(){ print 1; }; ensure_hidden')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("SENT:", result.stdout)

    def test_unset_hide_state_is_toggled_once(self):
        for value in ["0", ""]:
            with self.subTest(value=value):
                result = self.run_fixture('sql(){ print -r -- "' + value + '"; }; ensure_hidden')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines(), ["SENT:!hide"])

    def test_failed_or_unrecognized_hide_query_never_toggles(self):
        for implementation in ['return 9', 'print unexpected']:
            with self.subTest(implementation=implementation):
                result = self.run_fixture('sql(){ ' + implementation + '; }; ensure_hidden')
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("SENT:", result.stdout)

    def test_failed_session_query_never_updates_or_restarts(self):
        result = self.run_fixture('''
sql(){ if [[ "$1" == select* ]]; then return 9; fi; print UPDATED; }
rescue
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("UPDATED", result.stdout)
        self.assertNotIn("STARTED", result.stdout)

    def test_active_session_never_updates_or_restarts(self):
        result = self.run_fixture('''
sql(){ if [[ "$1" == select* ]]; then print 1; else print UPDATED; fi; }
rescue
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("UPDATED", result.stdout)
        self.assertNotIn("STARTED", result.stdout)

    def test_idle_session_updates_before_single_restart(self):
        result = self.run_fixture('''
sql(){ if [[ "$1" == select* ]]; then return 0; fi; print UPDATED; }
rescue
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("UPDATED"), 2)
        self.assertEqual(result.stdout.count("STARTED"), 1)
        self.assertLess(result.stdout.rfind("UPDATED"), result.stdout.index("STARTED"))

    def test_failed_update_never_restarts(self):
        result = self.run_fixture('''
sql(){ if [[ "$1" == select* ]]; then return 0; fi; print FAILED_UPDATE; return 9; }
rescue
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.count("FAILED_UPDATE"), 1)
        self.assertNotIn("STARTED", result.stdout)


if __name__ == "__main__":
    unittest.main()
