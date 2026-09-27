-- Vanaguide :: guides/bastok_mission_1_2.lua
-- Source-derived from local LandSandBoat mission and zone scripts.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local G = require('core.guide')

G.register({
    name = 'Bastok - A Geological Survey',
    author = 'Vanaguide',
    levels = '1+',
    desc = 'Collect acidity-test results at Dangruf Wadi and return them to Cid.',
    steps = [[
A Accept A Geological Survey from a Bastok gate guard.|MA|bastok,1|Z|235|POS|-361.9,-169.13|N|This mission is offered by Cleades, Rashid, Malduc, or Argus. The guide routes to Cleades as its default.|
C Get the Blue Acidity Tester from Cid.|KI|3|Z|237|POS|-12.6,2.43|N|The local LSB mission awards key item 3 when Cid begins the test.|
F Travel to Dangruf Wadi.|Z|191|
C Use the I-8 geyser to collect the Red Acidity Tester.|KI|4|Z|191|POS|-133,133|N|Local LSB tests confirm this trigger at x=-133, y=3, z=133. If it does not activate, use /vg next to try the H-8 geyser (-213,94) or J-3 geyser (-67,533).|
C Use the H-8 geyser to collect the Red Acidity Tester.|KI|4|Z|191|POS|-213,94|
C Use the J-3 geyser to collect the Red Acidity Tester.|KI|4|Z|191|POS|-67,533|
F Return to Metalworks.|Z|237|
T Give the Red Acidity Tester to Cid.|M|bastok,1|Z|237|POS|-12.6,2.43|N|Mission completion is server-confirmed when Cid accepts the test result.|
]],
})
