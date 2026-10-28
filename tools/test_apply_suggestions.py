#!/usr/bin/env python3
"""Vanaguide :: tools/test_apply_suggestions.py -- fills blanks only, never overwrites, idempotent.

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apply_suggestions as A  # noqa: E402

DATA = """Q.quests = {
    sandoria = {
        [0] = { name = 'A Sentry\\'s Peril', zone = 230, x = -122.0, z = 15.0, y = -2.0, npc = 'Glenne' },
        [1] = { name = 'No Location Yet' },
    },
}
"""
SUGGEST = """-- quests.sandoria — Southern San d'Oria
[0] = { name = 'A Sentry\\'s Peril', zone = 231, npc = 'Wrong' },
[1] = { name = 'No Location Yet', zone = 230, npc = 'Some_One' },
[2] = { name = 'Bad', zone = 99999, npc = 'X' },
"""

with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, 's'))
    open(os.path.join(d, 's', 'a.lua'), 'w').write(SUGGEST)
    open(os.path.join(d, 'quests.lua'), 'w').write(DATA)
    open(os.path.join(d, 'missions.lua'), 'w').write('M.missions = {\n}\n')
    A.main(os.path.join(d, 's'), d)
    once = open(os.path.join(d, 'quests.lua')).read()
    A.main(os.path.join(d, 's'), d)
    twice = open(os.path.join(d, 'quests.lua')).read()
checks = [
    ("a blank entry gets the suggested zone and giver", "'No Location Yet', zone = 230, npc = 'Some_One'" in once),
    ("a known location is never overwritten", "npc = 'Glenne'" in once and 'Wrong' not in once),
    ("an impossible zone is skipped", 'Bad' not in once),
    ("running again changes nothing", once == twice),
]
for name, ok in checks:
    print(('PASS ' if ok else 'FAIL ') + name)
sys.exit(0 if all(ok for _, ok in checks) else 1)
