-- Vanaguide :: guides/windurst_mission_1_2.lua
-- Source-derived from the local LandSandBoat mission script and NPC SQL.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local G = require('core.guide')

G.register({
    name = 'Windurst - The Heart of the Matter',
    author = 'Vanaguide',
    levels = '1+',
    desc = 'Place six Dark Mana Orbs in Outer Horutoto Ruins and recover the glowing orbs.',
    steps = [[
A Accept The Heart of the Matter from a Windurst gate guard.|MA|windurst,1|Z|240|POS|-230.63,184.05|N|Mission 1 is offered by Janshura-Rashura in Port Windurst, Zokima-Rokima in Windurst Walls, Mokyokyo in Windurst Waters, or Rakoh Buuma in Windurst Woods. This guide uses Janshura-Rashura as its default start.|
C Speak with Apururu at the Manustery.|KI|37|Z|241|POS|-12.09,15.94|N|Apururu gives all six Dark Mana Orbs at once. This first orb condition confirms the set was awarded.|
F Travel to East Sarutabaruta and speak with Pore-Ohre.|KI|112|Z|116|POS|262.27,-459.61|N|Pore-Ohre gives the Southeastern Star Charm, allowing access to the ruins' mission objective.|
F Travel to Outer Horutoto Ruins.|Z|194|POS|466,-660|
C Place Dark Mana Orbs at the six Magical Gizmos.|FIXED||Z|194|POS|500,-700|N|Place an orb at each of the six Ancient Magical Gizmos in any order. Each interaction consumes the next orb; after each placement, use /vg next. This approximate central marker is for the gizmo cluster, not a specific one.|
C Examine Gate: Magical Gizmo after placing all six orbs.|FIXED||Z|194|POS|584,-660|N|When all six are placed, examine the gate on the east outer wall. This guide cannot read the server's mission-status counter, so confirm the six placements before advancing.|
C Retrieve the first glowing Mana Orb.|KI|59|Z|194|POS|542,-618|N|Examine any unused gizmo. The server awards glowing key items in sequence (IDs 59-64), regardless of which gizmo you use.|
C Retrieve the second glowing Mana Orb.|KI|60|Z|194|POS|500,-573|
C Retrieve the third glowing Mana Orb.|KI|61|Z|194|POS|458,-618|
C Retrieve the fourth glowing Mana Orb.|KI|62|Z|194|POS|458,-702|
C Retrieve the fifth glowing Mana Orb.|KI|63|Z|194|POS|500,-747|
C Retrieve the sixth glowing Mana Orb.|KI|64|Z|194|POS|542,-702|
F Zone into East Sarutabaruta to trigger the Cardian scene.|Z|116|N|The local mission script's expected route triggers a scene that takes the glowing orbs. If you avoid that scene, return directly to Apururu instead.|
T Return to Apururu in Windurst Woods to complete the mission.|M|windurst,1|Z|241|POS|-12.09,15.94|N|On the expected route, Apururu completes the mission after the Cardian scene. Mission completion is server-confirmed.|
]],
})
