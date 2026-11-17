#!/usr/bin/env python3
"""Focused offline fixtures for quest-source extraction."""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_quests


class QuestHeaderLocationTests(unittest.TestCase):
    def test_preserves_all_locations_without_relabeling_objectives_as_givers(self):
        source = """-- Fixture quest
-- Source NPC : !pos -1 2 3 230
-- Objective marker : !pos 10 20 30 231
local quest = Quest:new(xi.questLog.sandoria, xi.quest.id.sandoria.FIXTURE_QUEST)
"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as handle:
            handle.write(source)
            path = handle.name
        try:
            quest = gen_quests.parse_quest(
                path, {"sandoria": {"FIXTURE_QUEST": 250}}, {}, {})
        finally:
            os.unlink(path)

        self.assertEqual(quest["npc"]["name"], "Source NPC")
        self.assertEqual(len(quest["locations"]), 2)
        self.assertEqual(quest["locations"][0]["zone"], 230)
        self.assertEqual(quest["locations"][1]["name"], "Objective marker")
        self.assertEqual(quest["locations"][1]["zone"], 231)

    def test_generator_serializes_locations(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "scripts/globals"))
            os.makedirs(os.path.join(root, "scripts/enum"))
            os.makedirs(os.path.join(root, "scripts/quests/sandoria"))
            pathlib.Path(root, "scripts/globals/quests.lua").write_text(
                "[xi.quest.area[xi.questLog.sandoria]] = {\n FIXTURE_QUEST = 250\n}\n",
                encoding="utf-8")
            pathlib.Path(root, "scripts/enum/key_item.lua").write_text("", encoding="utf-8")
            pathlib.Path(root, "scripts/enum/item.lua").write_text("", encoding="utf-8")
            pathlib.Path(root, "scripts/quests/sandoria/fixture.lua").write_text(
                "-- Fixture quest\n-- Source NPC : !pos -1 2 3 230\n"
                "-- Objective marker : !pos 10 20 30 231\n"
                "local quest = Quest:new(xi.questLog.sandoria, "
                "xi.quest.id.sandoria.FIXTURE_QUEST)\n", encoding="utf-8")
            out = os.path.join(root, "quests.lua")
            subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "gen_quests.py"),
                            root, "-o", out], check=True, capture_output=True, text=True)
            generated = pathlib.Path(out).read_text(encoding="utf-8")
        self.assertIn("npc = 'Source NPC'", generated)
        self.assertIn("locations = { { name = 'Source NPC'", generated)
        self.assertIn("{ name = 'Objective marker', zone = 231", generated)


if __name__ == "__main__":
    unittest.main()
