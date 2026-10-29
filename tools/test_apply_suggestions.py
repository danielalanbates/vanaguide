#!/usr/bin/env python3
"""Vanaguide :: tools/test_apply_suggestions.py -- fills blanks only, never overwrites, idempotent.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import apply_suggestions as A

DATA = """Q.quests = {
    sandoria = {
        [0] = { name = 'A Sentry\\'s Peril', zone = 230, x = -122.0, z = 15.0, y = -2.0, npc = 'Glenne' },
        [1] = { name = 'No Location Yet' },
    },
}
"""
GOOD = """-- quests.sandoria — Southern San d'Oria
[1] = { name = 'No Location Yet', zone = 230, npc = 'Some_One' },
"""


class SuggestionTests(unittest.TestCase):
    def apply(self, files, data=DATA, kind='quests'):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'suggested-changes'
            folder.mkdir()
            for name, text in files.items():
                (folder / name).write_text(text, encoding='utf-8')
            target = root / (kind + '.lua')
            target.write_text(data, encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                wanted = A.suggestions(str(folder))
                added = A.apply(str(target), kind, wanted)
                once = target.read_bytes()
                again = A.apply(str(target), kind, wanted)
            self.assertEqual(target.read_bytes(), once, 'second pass must be byte-identical')
            self.assertEqual(again, [])
            return once.decode('utf-8'), added

    def test_fill_blank_and_keep_known_location(self):
        text, added = self.apply({'a.lua': GOOD + "[0] = { name = 'A Sentry\\'s Peril', zone = 231, npc = 'Wrong' },\n"})
        self.assertIn("'No Location Yet', zone = 230, npc = 'Some_One'", text)
        self.assertIn("npc = 'Glenne'", text)
        self.assertNotIn('Wrong', text)
        self.assertEqual(added, ['quests.sandoria 1'])

    def test_existing_partial_locations_and_spacing_are_preserved(self):
        for field in ['zone=230', 'npc="Glenne"', 'zone\t=\t230', "npc = 'Glenne'"]:
            with self.subTest(field=field):
                data = DATA.replace("'No Location Yet'", "'No Location Yet', " + field)
                self.assertEqual(self.apply({'a.lua': GOOD}, data), (data, []))

    def test_stale_title_cannot_target_a_different_quest(self):
        self.assertEqual(self.apply({'a.lua': GOOD.replace('No Location Yet', 'Another Quest')}), (DATA, []))

    def test_missing_title_is_rejected(self):
        self.assertEqual(self.apply({'a.lua': GOOD.replace("name = 'No Location Yet', ", '')}), (DATA, []))

    def test_invalid_zone_and_npc_are_rejected(self):
        for value in [GOOD.replace('230', '0'), GOOD.replace('230', '99999'),
                      GOOD.replace('230', '230+1'), GOOD.replace('Some_One', 'Bad;Code'),
                      GOOD.replace('Some_One', r'Bad\nName')]:
            with self.subTest(value=value):
                self.assertEqual(self.apply({'a.lua': value}), (DATA, []))

    def test_apostrophes_round_trip_as_lua_strings(self):
        text, added = self.apply({'a.lua': GOOD.replace('Some_One', "O\\'Brien")})
        self.assertIn("npc = 'O\\'Brien'", text)
        self.assertEqual(len(added), 1)

    def test_conflicting_suggestions_require_review(self):
        self.assertEqual(self.apply({'a.lua': GOOD, 'b.lua': GOOD.replace('Some_One', 'Different')}), (DATA, []))

    def test_identical_duplicates_are_idempotent(self):
        text, added = self.apply({'a.lua': GOOD, 'b.lua': GOOD})
        self.assertEqual(len(added), 1)
        self.assertEqual(text.count("npc = 'Some_One'"), 1)

    def test_field_text_inside_a_title_is_not_existing_data(self):
        title = 'A title with zone = 230'
        text, added = self.apply({'a.lua': GOOD.replace('No Location Yet', title)}, DATA.replace('No Location Yet', title))
        self.assertEqual(len(added), 1)
        self.assertIn("npc = 'Some_One'", text)

    def test_field_text_inside_a_suggestion_title_is_ignored(self):
        title = "A title with zone = 99, npc = \\'Wrong\\'"
        text, added = self.apply({'a.lua': GOOD.replace('No Location Yet', title)}, DATA.replace('No Location Yet', title))
        self.assertEqual(len(added), 1)
        self.assertIn("zone = 230, npc = 'Some_One'", text)

    def test_missions_use_their_own_namespace(self):
        data = DATA.replace('Q.quests', 'M.missions').replace('sandoria', 'cop')
        suggestion = GOOD.replace('quests.sandoria', 'missions.cop')
        self.assertEqual(self.apply({'a.lua': GOOD}, data, 'missions'), (data, []))
        self.assertEqual(self.apply({'a.lua': suggestion}, data, 'missions')[1], ['missions.cop 1'])

    def test_lua_is_never_executed_and_heading_is_required(self):
        self.assertEqual(self.apply({'a.lua': GOOD.split('\n', 1)[1]}), (DATA, []))
        text, added = self.apply({'a.lua': "error('suggestions must never execute')\n" + GOOD})
        self.assertEqual(len(added), 1)
        self.assertNotIn('error(', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
