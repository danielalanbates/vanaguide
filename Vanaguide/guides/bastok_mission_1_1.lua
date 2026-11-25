-- Vanaguide :: guides/bastok_mission_1_1.lua
-- Source-derived from the local LandSandBoat mission script.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local G = require('core.guide')

G.register({
    name = 'Bastok - The Zeruhn Report',
    author = 'Vanaguide',
    levels = '1+',
    desc = 'Accept Bastok mission 1-1, get the Zeruhn Report, and deliver it to Naji.',
    steps = [[
A Accept The Zeruhn Report from a Bastok gate guard.|MA|bastok,0|Z|235|POS|-361.9,-169.13|N|Mission 0 is offered by Cleades in Bastok Markets, Rashid in Bastok Mines, Malduc in Metalworks, or Argus in Port Bastok. This guide routes to Cleades as the default.|
F Travel to Zeruhn Mines.|Z|172|
C Speak with Makarim to receive the Zeruhn Report.|KI|1|Z|172|POS|-60.92,-333.29|N|Makarim's local LSB event 121 grants key item 1 directly. If it does not trigger, speak with Rasmus at x=-11.7, z=70.8, then return here and try Makarim again.|
F Return to Metalworks.|Z|237|
T Deliver the Zeruhn Report to Naji.|M|bastok,0|Z|237|POS|66.9,-4.6|N|Mission completion is server-confirmed and consumes the Zeruhn Report key item.|
]],
})
