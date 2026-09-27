-- Vanaguide :: guides/windurst_mission_1_1.lua
-- Source-derived from the local LandSandBoat mission script.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local G = require('core.guide')

G.register({
    name = 'Windurst - The Horutoto Ruins Experiment',
    author = 'Vanaguide',
    levels = '1+',
    desc = 'Accept Windurst mission 1-1 and retrieve a Cracked Mana Orb from Inner Horutoto Ruins.',
    steps = [[
A Accept The Horutoto Ruins Experiment from a Windurst gate guard.|MA|windurst,0|Z|240|POS|-230.63,184.05|NPC|Janshura-Rashura|N|Mission 0 is offered by Janshura-Rashura in Port Windurst, Zokima-Rokima in Windurst Walls, Mokyokyo in Windurst Waters, or Rakoh Buuma in Windurst Woods. This guide routes to Janshura-Rashura as the default.|
t Report to Hakkuru-Rinkuru in Port Windurst.|Z|240|POS|-111.14,102.06|NPC|Hakkuru-Rinkuru|N|His cutscene advances the local mission status.|
F Travel to Inner Horutoto Ruins via East Sarutabaruta.|Z|192|
C Examine Gate: Magical Gizmo.|Z|192|POS|419,-27|N|The gate cutscene sets the mission's randomized target gizmo.|
C Try Magical Gizmo #1 for the Cracked Mana Orb.|KI|28|Z|192|POS|464,100|N|The mission chooses one target at random. If this one is wrong, inspect it, then use /vg next to try the next marked gizmo. Once the key item is received, remaining gizmo steps auto-complete.|
C Try Magical Gizmo #2 for the Cracked Mana Orb.|KI|28|Z|192|POS|406,59|
C Try Magical Gizmo #3 for the Cracked Mana Orb.|KI|28|Z|192|POS|464,20|
C Try Magical Gizmo #4 for the Cracked Mana Orb.|KI|28|Z|192|POS|295,19|
C Try Magical Gizmo #5 for the Cracked Mana Orb.|KI|28|Z|192|POS|353,60|
C Try Magical Gizmo #6 for the Cracked Mana Orb.|KI|28|Z|192|POS|295,100|
F Return to Port Windurst.|Z|240|
T Return the Cracked Mana Orb to Hakkuru-Rinkuru.|M|windurst,0|Z|240|POS|-111,101|NPC|Hakkuru-Rinkuru|N|Mission completion is server-confirmed and consumes the Cracked Mana Orb.|
]],
})
