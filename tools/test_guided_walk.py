#!/usr/bin/env python3
"""Bounded shell argument fixtures; Python guard calls and sleeps are replaced in-process.

No process inventory, client, server, command channel or screenshot is accessed.
Copyright (c) 2026 Bates LLC. All rights reserved. See LICENSE.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class GuidedWalkArguments(unittest.TestCase):
    def run_fixture(self, guide="40", steps="2", **settings):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root = Path(folder)
            output = root / "results"
            calls = root / "calls"
            environment = dict(os.environ, VG_GAME=str(root / "missing-game"),
                               VG_NARR=str(root / "dialogue.jsonl"), WALK_STRICT="0", WALK_TIMEOUT="420",
                               VG_WALK_SCRIPT=str(Path(__file__).with_name("guided_walk.sh").resolve()),
                               VG_FIXTURE_CALLS=str(calls))
            environment.update(settings)
            result = subprocess.run(["/bin/zsh", "-fc", '''
python3(){ print -r -- "$*" >> "$VG_FIXTURE_CALLS"; return 0; }
sleep(){ :; }
source "$VG_WALK_SCRIPT" "$@"
''', "fixture", guide, steps, str(output)], env=environment, capture_output=True, text=True, timeout=5)
            return result, calls.exists(), output.exists()

    def test_zero_or_negative_steps_do_not_claim_success(self):
        for steps in ["0", "-1"]:
            with self.subTest(steps=steps):
                result, calls, output = self.run_fixture(steps=steps)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Done.", result.stdout)
                self.assertFalse(calls, "invalid counts must be refused before guard/command delivery")
                self.assertFalse(output, "invalid counts must not create an evidence report")

    def test_invalid_guide_count_mode_and_timeout_refused_before_actions(self):
        for arguments in [dict(guide=""), dict(guide="nope"), dict(guide="0"),
                          dict(steps="1+1"), dict(steps="100000000000000000000"),
                          dict(WALK_STRICT="yes"), dict(WALK_TIMEOUT="0"),
                          dict(WALK_TIMEOUT="-1"), dict(WALK_TIMEOUT="invalid")]:
            with self.subTest(arguments=arguments):
                result, calls, output = self.run_fixture(**arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(calls)
                self.assertFalse(output)

    def test_valid_arguments_reach_fake_runtime_guard(self):
        result, calls, output = self.run_fixture(steps="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(calls)
        self.assertTrue(output)


if __name__ == "__main__":
    unittest.main()
