-- Vanaguide :: guides/starting_out.lua
-- The first hour, for any nation.  Deliberately written without coordinates: every step
-- here is either checked off by hand or answered by the game, and a made-up POS would send
-- the arrow somewhere wrong.  Fill coordinates in from play with /vg mark — see
-- docs/GUIDE_FORMAT.md.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local G = require('core.guide')

G.register({
    name = 'Starting out',
    author = 'Vanaguide',
    levels = '1-10',
    desc = 'What to do between stepping off the boat and level 10, in any nation.',
    steps = [[
N Welcome. Tick a step off with Done, or let the game tick it for you.|N|Steps that the server can confirm complete themselves.|
t Talk to your nation's Gate Guard and take Signet before leaving town.|N|Signet is what makes low-level fighting outside worth doing.|
t Ask a mission guard about your first national mission.|N|The opening mission and guard depend on your nation. Check the mission menu after accepting.|
C Reach level 5 in your starting job.|LV|5|
t Buy a weapon you can actually skill up, and food if you can afford it.|
C Reach level 10.|LV|10|
N Level 10 does not automatically grant an airship pass.|N|Continue your nation's missions and plan travel according to the transport access you actually have.|
N At level 18, the classic support-job quests are offered in Selbina and Mhaura.|N|Load Support jobs for Isacio in Selbina, or Support jobs - Mhaura for Vera. Choose one route.|
]],
})
