-- Vanaguide :: guides/knight_trial.lua
-- Source-derived from the local LandSandBoat quest script. Positions follow its `!pos`
-- comments and quest data; they remain unverified by a player walking to each marker.
--
-- Copyright (c) 2026 Bates LLC. All rights reserved.

local G = require('core.guide')

G.register({
    name = "San d'Oria - A Knight's Test",
    author = 'Vanaguide',
    levels = '30+',
    desc = 'Follow Balasiel’s Paladin trial from its prerequisites through Davoi and turn-in.',
    steps = [[
L Reach level 30.|LV|30|
C Complete A Squire's Test II.|Q|sandoria,19|Z|230|POS|-138.33,65.76|N|Balasiel gives this next trial only after the earlier quest is complete.|
A Accept A Knight's Test from Balasiel.|QA|sandoria,29|Z|230|POS|-138.33,65.76|NPC|Balasiel|
C Receive the Book of Tasks from Balasiel.|KI|143|Z|230|POS|-138.33,65.76|NPC|Balasiel|N|The local LSB acceptance event grants this key item; the guide waits for it before sending you to the two book NPCs.|
t Speak with Baunise in Southern San d'Oria.|Z|230|POS|-55,-32|NPC|Baunise|N|She gives the Book of the West while the quest is active.|
C Obtain the Book of the West.|KI|145|Z|230|POS|-55,-32|
t Speak with Cahaurme in Southern San d'Oria.|Z|230|POS|55.749,-29.354|NPC|Cahaurme|N|He gives the Book of the East while the quest is active.|
C Obtain the Book of the East.|KI|144|Z|230|POS|55.749,-29.354|
F Travel to Davoi.|Z|149|
C Search the Disused Well for the Knight's Soul.|KI|146|Z|149|POS|-221,-293|
F Return to Southern San d'Oria.|Z|230|
T Report the Knight's Soul to Balasiel.|Q|sandoria,29|Z|230|POS|-138.33,65.76|NPC|Balasiel|N|The server completes the quest and unlocks Paladin when the turn-in event finishes.|
]],
})
