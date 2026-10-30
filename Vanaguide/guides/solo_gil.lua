-- Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
-- Built from the user Horizon starter-gil spreadsheet and standard LSB quest facts.
local G = require("core.guide")
G.register({
    name = "Solo Gil - HorizonXI - Bastok",
    desc = "Horizon-specific errands, costs and rewards. Choose your home nation; manually skip unsuitable errands.",
    levels = "Early quests",
    steps = [[
t Choose profitable errands before spending gil.|N|HorizonXI spreadsheet route. Skip unaffordable or unsafe quests. Reward is gross, not profit: subtract materials, food, travel and Auction House fees. Gear rewards are not guaranteed cash. Check current prices; no gil/hour promise.|
t Breaking Stones — check requirements and profit first.|N|Start: Markets. Fame: 2.0. Prerequisite: none listed. Needs: Dangruf Stone. Spreadsheet reward: 400.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Requires Bastok fame 2.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Horatius in Bastok Markets and accept the quest (first option).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Dangruf Stone (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the Dangruf Stone (exactly 1) to Horatius in Bastok Markets.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 400 gil and 30 Bastok fame. Repeatable: trade another Dangruf Stone to Horatius.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Breaking Stones and verify the reward.|Q|bastok,10||Z|235||POS|-158.000,-117.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Gourmet — check requirements and profit first.|N|Start: Markets. Fame: 1.0. Prerequisite: none listed. Needs: Sleepshroom, T. Bulb, Wild Onion. Spreadsheet reward: 100-350. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Talk to Salimah in Bastok Markets to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Sleepshroom, 1 Treant Bulb, or 1 Wild Onion (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade one of them to Salimah at the right Vana'diel time: Sleepshroom from 18:00 to 06:00, Treant Bulb from 06:00 to 12:00, Wild Onion from 12:00 to 18:00.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t The right item at the right time pays 200 gil (Sleepshroom or Treant Bulb) or 350 gil (Wild Onion). Any listed item at the wrong time pays 100 gil.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: the gil above, Bastok fame, and the title Mommy's Helper. Repeatable: leave the area and come back before each new trade.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Gourmet and verify the reward.|Q|bastok,12||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Elvaan Goldsmith — check requirements and profit first.|N|Start: Markets. Fame: 1.0. Prerequisite: none listed. Needs: Copper Ingot. Spreadsheet reward: 180.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Talk to Michea in Bastok Markets to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain a Copper Ingot (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade 1 Copper Ingot to Michea in Bastok Markets.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Repeatable: while your Bastok fame is level 1, zone out and back, then trade another Copper Ingot to Michea.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 180 gil and Bastok fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Elvaan Goldsmith and verify the reward.|Q|bastok,13||Z|235||POS|-298.000,-157.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Father Figure — check requirements and profit first.|N|Start: Markets. Fame: 1.0. Prerequisite: The Elvaan Golds. Needs: Silver Ingot. Spreadsheet reward: 2200.0. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires Bastok fame level 2. Finish the quest The Elvaan Goldsmith first.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Michea in Bastok Markets to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Silver Ingot (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the Silver Ingot to Michea in Bastok Markets.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 2,200 gil and Bastok fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Father Figure and verify the reward.|Q|bastok,29||Z|235||POS|-298.000,-157.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t A Flash In the Pan — check requirements and profit first.|N|Start: Markets. Fame: 1.0. Prerequisite: none listed. Needs: 4 Flint Stone. Spreadsheet reward: 100.0. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Aquillina in Bastok Markets to start the quest. You can also skip this and trade straight away.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 4 Flint Stones (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the 4 Flint Stones to Aquillina to finish. After any trade she will not accept another for 15 minutes.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 100 gil and Bastok fame +10. Repeatable: trade 4 more Flint Stones after her 15-minute cooldown.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish A Flash In the Pan and verify the reward.|Q|bastok,14||Z|235||POS|-97.000,-81.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Mom, The Adventurer — check requirements and profit first.|N|Start: Markets. Fame: 1.0. Prerequisite: none listed. Needs: Copper Ring. Spreadsheet reward: 100.0. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Nbu Latteh in Bastok Markets to accept the quest; she gives you a Fire Crystal.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain a Copper Ring (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to Bastok Mines and trade 1 Copper Ring to Roh Latteh; you receive the key item Letter from Roh Latteh.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Nbu Latteh in Bastok Markets and talk to her. Tip: if you have not opened the letter in your key item list yet, she pays 200 gil instead of 100.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Repeatable: while your Bastok fame is level 1, zone out and back, then talk to Nbu Latteh again to repeat the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 200 gil (unread letter) or 100 gil, Bastok fame, and the title Ringbearer.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Mom, The Adventurer and verify the reward.|Q|bastok,21||Z|235||POS|-114.800,-113.300,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Signpost Marks The Spot — check requirements and profit first.|N|Start: Markets. Fame: 2.0. Prerequisite: Mom, The Adven. Needs: Running. Spreadsheet reward: Linen Robe. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires Bastok fame 2; finish Mom, the Adventurer? first and change zones after finishing it.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Nbu Latteh in Bastok Markets and pick the first (accept) option.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to Konschtat Highlands and examine the signpost (third signpost, near !pos -183 65 599) to receive the key item Painting of a Windmill.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Bastok Mines and talk to Roh Latteh while holding the Painting of a Windmill.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Linen Robe, Bastok fame, title Treasure Scavenger.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Signpost Marks The Spot and verify the reward.|Q|bastok,22||Z|235||POS|-114.800,-113.300,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Bare Bones — check requirements and profit first.|N|Start: Markets. Fame: 1.0. Prerequisite: none listed. Needs: 1 Bone Chip. Spreadsheet reward: Dangruf Map. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Degenhard in Bastok Markets to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain a Bone Chip (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Optional: talk to Biggorf in Bastok Markets for a cutscene.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade 1 Bone Chip to Degenhard in Bastok Markets.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: key item Map of the Dangruf Wadi, 2,000 experience points, and Bastok fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Bare Bones and verify the reward.|Q|bastok,38||Z|235||POS|-175.000,-135.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Buckets of Gold — check requirements and profit first.|N|Start: Markets. Fame: 1.0. Prerequisite: none listed. Needs: 5 Rusty Buckets. Spreadsheet reward: 300.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Talk to Foss in Bastok Markets and accept the quest (first option).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 5 Rusty Buckets (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade all 5 Rusty Buckets at once to Foss in Bastok Markets.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 300 gil, the title Bucket Fisher, and 10 Bastok fame. Repeatable: trade another 5 buckets.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Buckets of Gold and verify the reward.|Q|bastok,41||Z|235||POS|-283.000,-37.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Siren's Tear — check requirements and profit first.|N|Start: Mines. Fame: 1.0. Prerequisite: none listed. Needs: Running. Spreadsheet reward: 150.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Talk to Wahid in Bastok Mines to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Optional: talk to Otto and Carmelo in Port Bastok for hints.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to North Gustaberg and find the ??? (it moves between spots; one is near !pos 309.6 2.6 324).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Unequip your main and sub weapons, examine the ??? and pick the first option to get a Siren's Tear (needs a free inventory slot).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the 1 Siren's Tear to Wahid in Bastok Mines. He also accepts another tear after the quest is done.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 150 gil, Bastok fame, title Tearjerker.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Siren's Tear and verify the reward.|Q|bastok,0||Z|234||POS|26.300,-66.400,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Hearts Of Mythril — check requirements and profit first.|N|Start: Mines. Fame: 1.0. Prerequisite: none listed. Needs: Running. Spreadsheet reward: Sitabaki. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Elki in Bastok Mines and accept the quest (first option). You receive the key item Bouquet for the Pioneers.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to the Monument in North Gustaberg and examine it. Pick the first option to leave the bouquet.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Elki in Bastok Mines to finish the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Sitabaki, Bastok fame, and the title Pursuer of the Past.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Hearts Of Mythril and verify the reward.|Q|bastok,6||Z|234||POS|-17.100,52.700,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Eleventh's Hour — check requirements and profit first.|N|Start: Mines. Fame: 3.0. Prerequisite: Hearts Of Mythril. Needs: Running. Spreadsheet reward: Small Sword. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires Bastok fame level 3; finish the quest Hearts of Mythril first.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Elki in Bastok Mines and pick the option that accepts the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to Palborough Mines and examine the Old Toolbox; pick the first option to take the key item Old Toolbox.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Elki in Bastok Mines and talk to him.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Babenn in Bastok Mines to finish.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Small Sword, Bastok fame, and the title Pursuer of the Truth.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Eleventh's Hour and verify the reward.|Q|bastok,7||Z|234||POS|73.000,34.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Fallen Comrades — check requirements and profit first.|N|Start: Mines. Fame: 2.0. Prerequisite: none listed. Needs: Silver Name Tag. Spreadsheet reward: 550.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Requires Bastok fame level 2.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Pavvke in Bastok Mines to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Silver Name Tag (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the Silver Name Tag to Pavvke in Bastok Mines.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 550 gil and Bastok fame. Repeatable: trade him another Silver Name Tag at any time, and repeats give extra Bastok fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Fallen Comrades and verify the reward.|Q|bastok,19||Z|234||POS|16.600,-14.800,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Drachenfall — check requirements and profit first.|N|Start: Mines. Fame: 2.0. Prerequisite: none listed. Needs: Running. Spreadsheet reward: 2000.0. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires Bastok fame level 2.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Black Mud in Bastok Mines to accept the quest; he gives you a Brass Canteen.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to North Gustaberg and trade the Brass Canteen to the Waterfall Base to receive a Canteen of Drachenfall Water.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t If you lose the canteen before filling it, talk to Black Mud again and he gives you another Brass Canteen.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Black Mud in Bastok Mines and trade him the Canteen of Drachenfall Water.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 2,000 gil, Bastok fame, and the title Drachenfall Ascetic.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Drachenfall and verify the reward.|Q|bastok,31||Z|234||POS|63.500,-1.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Vengeful Wrath — check requirements and profit first.|N|Start: Mines. Fame: 3.0. Prerequisite: none listed. Needs: Quadav Helm. Spreadsheet reward: 900.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Requires Bastok fame 3.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Goraow in Bastok Mines to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Quadav Helm (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the 1 Quadav Helm to Goraow in Bastok Mines. He still accepts the trade after the quest is done.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 900 gil, Bastok fame, title Avenger.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Vengeful Wrath and verify the reward.|Q|bastok,32||Z|234||POS|38.000,14.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Minesweeper — check requirements and profit first.|N|Start: Mines. Fame: 1.0. Prerequisite: none listed. Needs: 3 Zeruhn Soot. Spreadsheet reward: 150.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Talk to Gerbaum in Bastok Mines to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 3 Pinches of Zeruhn Soot (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade all 3 Pinches of Zeruhn Soot to Gerbaum in Bastok Mines at once.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 150 gil, Bastok fame, and the title Zeruhn Sweeper. Repeatable: trade another 3 Pinches of Zeruhn Soot at any time.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Minesweeper and verify the reward.|Q|bastok,39||Z|234||POS|-119.900,-74.700,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Beauty And the Galka — check requirements and profit first.|N|Start: Port Bastok. Fame: 1.0. Prerequisite: none listed. Needs: Zinc Ore. Spreadsheet reward: Bronze Knife. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Talib in Port Bastok and accept (if you decline, you can still start it by talking to Parraggoh in Bastok Mines and agreeing).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Chunk of Zinc Ore (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the Chunk of Zinc Ore (exactly 1) to Talib in Port Bastok to get the key item Palborough Mines Logs.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Take the logs to Parraggoh in Bastok Mines and talk to him to finish.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Bronze Knife and 30 Norg fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Beauty And the Galka and verify the reward.|Q|bastok,1||Z|236||POS|-101.100,28.800,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Shady Business — check requirements and profit first.|N|Start: Port Bastok. Fame: 1.0. Prerequisite: Beauty And The G. Needs: 4 Zinc Ore. Spreadsheet reward: 350.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Requires finishing the quest Beauty and the Galka first.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Talib in Port Bastok to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 4 Chunks of Zinc Ore (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade 4 Chunks of Zinc Ore to Talib in Port Bastok.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Repeatable: trade 4 more Chunks of Zinc Ore to Talib any time for the reward again.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 350 gil and Norg fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Shady Business and verify the reward.|Q|bastok,8||Z|236||POS|-101.100,28.800,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Welcome To Bastok — check requirements and profit first.|N|Start: Port Bastok. Fame: 1.0. Prerequisite: none listed. Needs: Shell Shield Equipped. Spreadsheet reward: Spatha. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Powhatan in Port Bastok and pick the first (accept) option.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain a Shell Shield (this quest's script does not say where) and equip it in your sub (shield) slot.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t With the Shell Shield equipped, talk to Bartolomeo in Port Bastok.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Powhatan in Port Bastok and talk to him.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Spatha, Bastok fame, title Bastok Welcoming Committee.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Welcome To Bastok and verify the reward.|Q|bastok,2||Z|236||POS|-152.100,19.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Quadav's Curse — check requirements and profit first.|N|Start: Port Bastok. Fame: 1.0. Prerequisite: none listed. Needs: Quadav Backplate. Spreadsheet reward: Bronze Subl. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Corann in Port Bastok to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Quadav Backplate (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the 1 Quadav Backplate to Corann in Port Bastok.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Bronze Subligar and Bastok fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Quadav's Curse and verify the reward.|Q|bastok,4||Z|236||POS|90.900,32.600,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Forever To Hold — check requirements and profit first.|N|Start: Port Bastok. Fame: 2.0. Prerequisite: none listed. Needs: Brass Hairpin. Spreadsheet reward: 300.0. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires Bastok fame level 2.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Qiji in Port Bastok to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Brass Hairpin (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the Brass Hairpin to Romilda, who stands next to Qiji in Port Bastok. Trading it to Qiji does nothing.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Qiji again to finish the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 300 gil, Bastok fame, and the title Qiji's Friend.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Forever To Hold and verify the reward.|Q|bastok,17||Z|236||POS|4.300,-18.900,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Till Death Do Us Part — check requirements and profit first.|N|Start: Port Bastok. Fame: 3.0. Prerequisite: Forever To Hold. Needs: Cotton Gloves. Spreadsheet reward: 2000.0. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires Bastok fame 3; finish Forever to Hold first.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Romilda in Port Bastok to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 pair of Cotton Gloves (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the 1 pair of Cotton Gloves to Romilda in Port Bastok.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 2,000 gil, Bastok fame, title Qiji's Rival.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Till Death Do Us Part and verify the reward.|Q|bastok,18||Z|236||POS|5.400,-18.700,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Past Perfect — check requirements and profit first.|N|Start: Port Bastok. Fame: 2.0. Prerequisite: none listed. Needs: Running. Spreadsheet reward: Scale Mail. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires Bastok fame level 2.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Evi in Port Bastok to see a cutscene, then talk to Evi again to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to Konschtat Highlands and examine the ??? there to get the key item Tattered Mission Orders.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Evi in Port Bastok and talk to him.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Scale Mail and Bastok fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Past Perfect and verify the reward.|Q|bastok,23||Z|236||POS|-4.700,1.700,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Wisdom Of Elders — check requirements and profit first.|N|Start: Port Bastok. Fame: 1.0. Prerequisite: none listed. Needs: Bomb Ash. Spreadsheet reward: Traveler's Hat. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Benita in Port Bastok to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Optional: talk to Tete in Port Bastok for more dialogue.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Pinch of Bomb Ash (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the 1 Pinch of Bomb Ash to Benita in Port Bastok.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Traveler's Hat and Bastok fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Wisdom Of Elders and verify the reward.|Q|bastok,36||Z|236||POS|49.700,36.200,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Bite The Dust — check requirements and profit first.|N|Start: Port Bastok. Fame: 2.0. Prerequisite: none listed. Needs: Sand Bat Fang. Spreadsheet reward: 350.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Requires Bastok fame 2.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Yazan in Port Bastok to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Sand Bat Fang (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the Sand Bat Fang (exactly 1) to Yazan in Port Bastok.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 350 gil, the title Sand Blaster, and 10 Bastok fame. Repeatable: trade another fang to Yazan any time.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Bite The Dust and verify the reward.|Q|bastok,46||Z|236||POS|-20.100,24.500,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
]],
})
G.register({
    name = "Solo Gil - HorizonXI - San d'Oria",
    desc = "Horizon-specific errands, costs and rewards. Choose your home nation; manually skip unsuitable errands.",
    levels = "Early quests",
    steps = [[
t Choose profitable errands before spending gil.|N|HorizonXI spreadsheet route. Skip unaffordable or unsafe quests. Reward is gross, not profit: subtract materials, food, travel and Auction House fees. Gear rewards are not guaranteed cash. Check current prices; no gil/hour promise.|
t Waters of Cheval — check requirements and profit first.|N|Start: North. Fame: 1.0. Prerequisite: none listed. Needs: Running. Spreadsheet reward: Wing Pendant. Repeatable: N. Horizon values may differ from standard LSB details.|
t Verify Waters of Cheval on the Horizon wiki before proceeding.|N|No matching standard quest record found. Use the spreadsheet requirements above; no invented NPC or arrow.|
t The Vicasque's Sermon — check requirements and profit first.|N|Start: North. Fame: 2.0. Prerequisite: Waters of Cheval. Needs: 70g. Spreadsheet reward: Brass Ring. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires Waters of the Cheval completed.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Abioleget in Northern San d'Oria to start the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade 70 gil to Abioleget to receive a Pod of Blue Peas.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to East Ronfaure and trade the Pod of Blue Peas to Andelain.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Abioleget in Northern San d'Oria and talk to him.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Brass Ring, San d'Oria fame, title The Benevolent One.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Vicasque's Sermon and verify the reward.|Q|sandoria,9||Z|231||POS|128.800,118.500,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Trader in the Forest — check requirements and profit first.|N|Start: North. Fame: 1.0. Prerequisite: none listed. Needs: Running. Spreadsheet reward: Robe. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Abeaule in Northern San d'Oria and accept (first option); you receive a Supplies Order.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to West Ronfaure and trade the Supplies Order to Phairet to receive a Clump of Batagreens (Phairet also sells Batagreens for 50 gil).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Northern San d'Oria and trade the Clump of Batagreens to Abeaule.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Robe, San d'Oria fame, title Green Grocer.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Trader in the Forest and verify the reward.|Q|sandoria,7||Z|231||POS|-136.000,56.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Gates To Paradise — check requirements and profit first.|N|Start: North. Fame: 2.0. Prerequisite: none listed. Needs: Running. Spreadsheet reward: Cotton Cape. Repeatable: N. Horizon values may differ from standard LSB details.|
t Verify Gates To Paradise on the Horizon wiki before proceeding.|N|No matching standard quest record found. Use the spreadsheet requirements above; no invented NPC or arrow.|
t Undying Flames — check requirements and profit first.|N|Start: North. Fame: 2.0. Prerequisite: none listed. Needs: 2 Beeswax. Spreadsheet reward: Friar's Rope. Repeatable: N. Horizon values may differ from standard LSB details.|
t Verify Undying Flames on the Horizon wiki before proceeding.|N|No matching standard quest record found. Use the spreadsheet requirements above; no invented NPC or arrow.|
t Fear of the Dark — check requirements and profit first.|N|Start: North. Fame: ?. Prerequisite: none listed. Needs: 2 Bat Wings. Spreadsheet reward: 200.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Talk to Secodiand in Northern San d'Oria and choose to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 2 Bat Wings (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the 2 Bat Wings to Secodiand.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 200 gil and 10 San d'Oria fame. Repeatable: trade 2 more Bat Wings anytime for the same reward.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Fear of the Dark and verify the reward.|Q|sandoria,78||Z|231||POS|-160.000,137.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Pickpocket — check requirements and profit first.|N|Start: Port S. Fame: 1.0. Prerequisite: none listed. Needs: . Spreadsheet reward: Light Axe. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Miene, the little girl in Port San d'Oria, to watch a thief rob the guard Altiret.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Altiret in Port San d'Oria; he asks you to recover his wife's glasses (quest starts).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Miene again (keep an inventory slot free) to receive an Eagle Button.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to West Ronfaure, (F-6), and find Esca in the tower; trade her the Eagle Button to receive the Gilt Glasses.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Port San d'Oria and trade the Gilt Glasses to Altiret.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Light Axe, San d'Oria fame, title Pickpocket Pincher.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Pickpocket and verify the reward.|Q|sandoria,3||Z|232||POS|0.000,-81.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t A Taste For Meat — check requirements and profit first.|N|Start: Port S. Fame: 1.0. Prerequisite: none listed. Needs: 5 Hare Meat. Spreadsheet reward: 120, Grilled Hare. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Talk to Antreneau in Port San d'Oria.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Thierride, who stands next to Antreneau in Port San d'Oria.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 5 Slices of Hare Meat (this quest's script does not say where). Trade all 5 to Thierride to accept and complete the quest in one step.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 150 gil, title Rabbiter and San d'Oria fame. Afterward, talk to Antreneau to receive a Slice of Grilled Hare.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish A Taste For Meat and verify the reward.|Q|sandoria,100||Z|232||POS|-71.000,-39.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Dismayed Customer — check requirements and profit first.|N|Start: Port S. Fame: 1.0. Prerequisite: A Taste For Meat. Needs: . Spreadsheet reward: 560.0. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires A Taste for Meat completed.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Gulemont in Port San d'Oria and accept (first option).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to West Ronfaure and check the three ??? spots; only one (chosen at random when you accepted) gives the key item Gulemont's Document.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Gulemont in Port San d'Oria and talk to him.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 560 gil, San d'Oria fame, title Lost & Found Officer.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Dismayed Customer and verify the reward.|Q|sandoria,6||Z|232||POS|-69.000,-38.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Brugaire Consortium — check requirements and profit first.|N|Start: Port S. Fame: 1.0. Prerequisite: none listed. Needs: Running. Spreadsheet reward: Lauan Shield. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Fontoumant in Port San d'Oria and accept (first option); you receive a Parcel for the Magic Shop.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the Parcel for the Magic Shop to Regine in Port San d'Oria.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Fontoumant again to receive a Parcel for the Auction House, then trade it to Apstaule in Port San d'Oria.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Fontoumant again to receive a Parcel for the Pub, then trade it to Thierride in Port San d'Oria.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Fontoumant once more to finish. (If a parcel is lost, trade Fontoumant 100 gil to continue.)|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Lauan Shield, San d'Oria fame, title Courier Extraordinaire.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Brugaire Consortium and verify the reward.|Q|sandoria,12||Z|232||POS|-10.000,-122.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Lufet's Lake Salt — check requirements and profit first.|N|Start: Port S. Fame: 1.0. Prerequisite: none listed. Needs: 3 Lufet Salt. Spreadsheet reward: 600.0. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Nogelle in Port San d'Oria and choose to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 3 Chunks of Lufet Salt (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the 3 Chunks of Lufet Salt to Nogelle.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 600 gil, 10 San d'Oria fame, title Bean Cuisine Salter.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Lufet's Lake Salt and verify the reward.|Q|sandoria,81||Z|232||POS|-70.000,-33.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Thick Shells — check requirements and profit first.|N|Start: Port S. Fame: 2.0. Prerequisite: none listed. Needs: 5 Beetle Shells. Spreadsheet reward: 750.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Verify Thick Shells on the Horizon wiki before proceeding.|N|No matching standard quest record found. Use the spreadsheet requirements above; no invented NPC or arrow.|
t A Sentry's Peril — check requirements and profit first.|N|Start: Southern. Fame: 1.0. Prerequisite: none listed. Needs: Running. Spreadsheet reward: Bronze Subl. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Glenne in Southern San d'Oria and accept. She gives you a Dose of Ointment, and she gives you another if you lose it.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to West Ronfaure and find the guard Aaveleon on the road to Ghelsba Outpost (G-6).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Make sure you have a free inventory slot, then trade the Dose of Ointment to Aaveleon. He gives you an Ointment Case, and he gives you another if you lose it.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Glenne in Southern San d'Oria and trade her the Ointment Case.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Bronze Subligar, title Ronfaurian Rescuer and San d'Oria fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish A Sentry's Peril and verify the reward.|Q|sandoria,0||Z|230||POS|-122.000,15.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Rosel The Armorer — check requirements and profit first.|N|Start: Southern. Fame: 1.0. Prerequisite: none listed. Needs: Running. Spreadsheet reward: 100-200. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Rosel in Southern San d'Oria and accept; you receive key item Receipt for the Prince. Note which prince (Pieuje or Trion) she names.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to Guilerme in Northern San d'Oria, talk to him, and choose the prince Rosel named.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Rosel in Southern San d'Oria and talk to her to finish.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 200 gil and 20 San d'Oria fame if you named the right prince (100 gil and 10 fame if not), plus title Entrance Denied.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Rosel The Armorer and verify the reward.|Q|sandoria,2||Z|230||POS|69.900,41.100,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Seamstress — check requirements and profit first.|N|Start: Southern. Fame: 1.0. Prerequisite: none listed. Needs: 3 Sheepskin. Spreadsheet reward: Leather Gloves. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Talk to Hanaa Punaa in Southern San d'Oria and accept (first option).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 3 Sheepskins (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade exactly 3 Sheepskins to Hanaa Punaa.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Leather Gloves, San d'Oria fame, title Silencer of the Lambs. Repeatable: trade 3 more Sheepskins any time for another pair.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Seamstress and verify the reward.|Q|sandoria,5||Z|230||POS|-179.700,27.600,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Lizard Skins — check requirements and profit first.|N|Start: Southern. Fame: 2.0. Prerequisite: The Seemstress. Needs: 3 Lizard Skins. Spreadsheet reward: Lizard Gloves. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Requires San d'Oria fame 2; finish The Seamstress first.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Hanaa Punaa in Southern San d'Oria and choose to accept the quest (if you decline, talk to her again to accept).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 3 Lizard Skins (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade exactly 3 Lizard Skins to Hanaa Punaa.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Lizard Gloves, 10 San d'Oria fame, title Lizard Skinner. Repeatable: trade 3 more Lizard Skins anytime for another pair and 10 fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Lizard Skins and verify the reward.|Q|sandoria,15||Z|230||POS|-179.700,27.600,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Black Tiger Skins — check requirements and profit first.|N|Start: Southern. Fame: 3.0. Prerequisite: Lizard Skins. Needs: 3 Black Tiger Hides. Spreadsheet reward: Tiger Stole. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires San d'Oria fame 3 and Lizard Skins completed.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Hanaa Punaa in Southern San d'Oria and accept (choose the first option).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 3 Tiger Hides (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade all 3 Tiger Hides to Hanaa Punaa.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Tiger Stole, title Cat Skinner and San d'Oria fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Black Tiger Skins and verify the reward.|Q|sandoria,31||Z|230||POS|-179.700,27.600,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Tiger's Teeth — check requirements and profit first.|N|Start: Southern. Fame: 3.0. Prerequisite: none listed. Needs: 3 Black Tiger Fang. Spreadsheet reward: 2100.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Requires San d'Oria fame level 3.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Taumila in Southern San d'Oria and accept the request (first choice in the cutscene).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 3 Black Tiger Fangs (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade exactly 3 Black Tiger Fangs to Taumila in Southern San d'Oria.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 2,100 gil, title Fang Finder, San d'Oria fame. Repeatable: trade 3 more Black Tiger Fangs to Taumila any time for 2,100 gil and more fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Tiger's Teeth and verify the reward.|Q|sandoria,23||Z|230||POS|-140.000,-8.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Sweetest Things — check requirements and profit first.|N|Start: Southern. Fame: 2.0. Prerequisite: none listed. Needs: 5 Honey. Spreadsheet reward: 400.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Requires San d'Oria fame 2.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Raimbroy in Southern San d'Oria, then talk to him again and accept (first option).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 5 Pots of Honey (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade exactly 5 Pots of Honey to Raimbroy.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 400 gil, San d'Oria fame, title Apiarist. Repeatable: trade 5 more Pots of Honey any time for the same reward.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Sweetest Things and verify the reward.|Q|sandoria,8||Z|230||POS|-141.000,34.600,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Grave Concerns — check requirements and profit first.|N|Start: Southern. Fame: 1.0. Prerequisite: none listed. Needs: Running. Spreadsheet reward: 560.0. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires San d'Oria fame 1.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Andecia in Southern San d'Oria to hear her story, then talk to her again and accept; she gives you a Skin of Well Water.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Travel to King Ranperres Tomb and find the upper tombstone (Tombstone_Upper); trade it the Skin of Well Water to change the water and receive a Tomb Guard's Waterskin.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Andecia in Southern San d'Oria and trade her the Tomb Guard's Waterskin to finish.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t If you lose the Skin of Well Water: talk to Andecia, examine the tombstone to take its waterskin, trade it to the Well in Southern San d'Oria to refill it, then go back to the tombstone.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 560 gil, 20 San d'Oria fame, title Royal Grave Keeper.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Grave Concerns and verify the reward.|Q|sandoria,11||Z|230||POS|167.000,45.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Grimy Signposts — check requirements and profit first.|N|Start: Southern. Fame: 2.0. Prerequisite: none listed. Needs: Running. Spreadsheet reward: 1500.0. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires San d'Oria fame 2.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Maugie in Southern San d'Oria and choose to accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Go to Jugner Forest and examine each of the 4 Signposts, choosing to clean each one (they are spread across the zone).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Return to Maugie in Southern San d'Oria and talk to him to finish.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 1500 gil and 20 San d'Oria fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Grimy Signposts and verify the reward.|Q|sandoria,66||Z|230||POS|105.000,-16.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t The Merchant's Bidding — check requirements and profit first.|N|Start: Southern. Fame: 1.0. Prerequisite: none listed. Needs: 3 Rabbit Hides. Spreadsheet reward: 120.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Talk to Parvipon in Southern San d'Oria and accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 3 Rabbit Hides (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the 3 Rabbit Hides to Parvipon.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 120 gil and San d'Oria fame. Repeatable: trade 3 more Rabbit Hides any time for 120 gil.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish The Merchant's Bidding and verify the reward.|Q|sandoria,69||Z|230||POS|-169.000,13.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Starting a Flame — check requirements and profit first.|N|Start: Southern. Fame: 1.0. Prerequisite: none listed. Needs: 4 Flint Stones. Spreadsheet reward: 100.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Talk to Legata in Southern San d'Oria and accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 4 Flint Stones (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the 4 Flint Stones to Legata.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 100 gil and San d'Oria fame. Repeatable: trade 4 more Flint Stones to Legata any time for the same reward.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Starting a Flame and verify the reward.|Q|sandoria,77||Z|230||POS|82.000,116.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
]],
})
G.register({
    name = "Solo Gil - HorizonXI - Windurst",
    desc = "Horizon-specific errands, costs and rewards. Choose your home nation; manually skip unsuitable errands.",
    levels = "Early quests",
    steps = [[
t Choose profitable errands before spending gil.|N|HorizonXI spreadsheet route. Skip unaffordable or unsafe quests. Reward is gross, not profit: subtract materials, food, travel and Auction House fees. Gear rewards are not guaranteed cash. Check current prices; no gil/hour promise.|
t Teacher's Pet — check requirements and profit first.|N|Start: Waters. Fame: 1.0. Prerequisite: none listed. Needs: Bird Feather Two-Leaf Mandy Bud. Spreadsheet reward: 250.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Talk to Moreno-Toeno in Windurst Waters, then talk to him again and accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Bird Feather and 1 Two-Leaf Mandragora Bud (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the Bird Feather and the Two-Leaf Mandragora Bud together to Moreno-Toeno to finish and receive 250 gil.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 250 gil and Windurst fame +10. You can keep trading the same pair afterwards for another 250 gil each time.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Teacher's Pet and verify the reward.|Q|windurst,28||Z|238||POS|169.000,159.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t In A Pickle — check requirements and profit first.|N|Start: Waters. Fame: 1.0. Prerequisite: none listed. Needs: Smooth Stone. Spreadsheet reward: 200 Bone Hairpin. Repeatable: N. Horizon values may differ from standard LSB details.|
t Verify In A Pickle on the Horizon wiki before proceeding.|N|No matching standard quest record found. Use the spreadsheet requirements above; no invented NPC or arrow.|
t Truth Justice and the Onion Way — check requirements and profit first.|N|Start: Port Windy. Fame: 1.0. Prerequisite: none listed. Needs: Rarab Tail. Spreadsheet reward: Justice Badge. Repeatable: N. Horizon values may differ from standard LSB details.|
t Talk to Kohlo-Lakolo in Port Windurst and accept the quest in the cutscene.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Rarab Tail (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the 1 Rarab Tail to Kohlo-Lakolo in Port Windurst to finish the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Justice Badge, title Star Onion Brigade Member, Windurst fame +20. Zone out before starting Know One's Onions.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Truth Justice and the Onion Way and verify the reward.|Q|windurst,36||Z|240||POS|-26.800,190.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Making Amends — check requirements and profit first.|N|Start: Port Windy. Fame: ?. Prerequisite: none listed. Needs: Animal Glue. Spreadsheet reward: 1500.0. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires Windurst fame 2.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t In Port Windurst, talk to Hakkuru-Rinkuru and accept his request for animal glue.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Block of Animal Glue (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the Block of Animal Glue to Hakkuru-Rinkuru.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 1,500 gil, Windurst fame, and the title Quick Fixer.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Making Amends and verify the reward.|Q|windurst,3||Z|240||POS|-111.000,101.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Something Fishy — check requirements and profit first.|N|Start: Port Windy. Fame: 1.0. Prerequisite: none listed. Needs: Bastore Sardine. Spreadsheet reward: 70.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Verify Something Fishy on the Horizon wiki before proceeding.|N|No matching standard quest record found. Use the spreadsheet requirements above; no invented NPC or arrow.|
t Curses, Foiled Again! — check requirements and profit first.|N|Start: Walls. Fame: 1.0. Prerequisite: none listed. Needs: 2 Bone Chips, 1 Bomb Ash. Spreadsheet reward: Brass Rod. Repeatable: N. Horizon values may differ from standard LSB details.|
t Verify Curses, Foiled Again! on the Horizon wiki before proceeding.|N|No matching standard quest record found. Use the spreadsheet requirements above; no invented NPC or arrow.|
t Mandragora Mad — check requirements and profit first.|N|Start: Walls. Fame: 1.0. Prerequisite: none listed. Needs: Cornette,4Leaf,Snobby,3Leaf, Y. Sulfer. Spreadsheet reward: 120-5500. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Verify Mandragora Mad on the Horizon wiki before proceeding.|N|No matching standard quest record found. Use the spreadsheet requirements above; no invented NPC or arrow.|
t Star Struck — check requirements and profit first.|N|Start: Walls. Fame: 1.0. Prerequisite: none listed. Needs: Torn Epistle, Meteorite. Spreadsheet reward: Comp. Eye Circ. Repeatable: N. Horizon values may differ from standard LSB details.|
t Requires a Torn Epistle in your inventory (this quest's script does not say where to get it).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Talk to Koru-Moru in Windurst Walls and accept the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Optional: trade the Torn Epistle to Koru-Moru for 50 gil.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 1 Meteorite (this quest's script does not say where).|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Trade the Meteorite to Koru-Moru in Windurst Walls to finish.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: Compound Eye Circlet and Windurst fame +20.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Star Struck and verify the reward.|Q|windurst,10||Z|239||POS|-120.000,124.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Postman Always KO's Twice — check requirements and profit first.|N|Start: Walls. Fame: 1.0. Prerequisite: none listed. Needs: Damp, Muddy, Odd, Torn. Spreadsheet reward: 50-500. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Verify Postman Always KO's Twice on the Horizon wiki before proceeding.|N|No matching standard quest record found. Use the spreadsheet requirements above; no invented NPC or arrow.|
t The All New C-2000 — check requirements and profit first.|N|Start: Woods. Fame: 1.0. Prerequisite: none listed. Needs: Rabbit Hide, 2Leaf, Insect Wing. Spreadsheet reward: 200.0. Repeatable: N. Horizon values may differ from standard LSB details.|
t Verify The All New C-2000 on the Horizon wiki before proceeding.|N|No matching standard quest record found. Use the spreadsheet requirements above; no invented NPC or arrow.|
t Creepy Crawlies — check requirements and profit first.|N|Start: Woods. Fame: 1.0. Prerequisite: none listed. Needs: 3 Silk OR 3 Crawler Calc. Spreadsheet reward: 600.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Verify Creepy Crawlies on the Horizon wiki before proceeding.|N|No matching standard quest record found. Use the spreadsheet requirements above; no invented NPC or arrow.|
t Mihgo's Amigo — check requirements and profit first.|N|Start: Woods. Fame: 1.0. Prerequisite: none listed. Needs: 4 Yag Necks. Spreadsheet reward: 200.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t You cannot start this while The Tenshodo Showdown or As Thick as Thieves is in progress.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t In Windurst Woods, talk to Nanaa Mihgo to start the quest.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Optional: Bopa Greso and Cha Lebagta in Windurst Woods give hints.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Obtain 4 Yagudo Bead Necklaces (this quest's script does not say where) and trade all 4 to Nanaa Mihgo.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
t Reward: 200 gil, Norg fame, and the title Cat Burglar Groupie. Repeatable: trade 4 more necklaces any time for 200 gil and a little Norg fame.|N|Standard LSB procedure; confirm Horizon-specific differences before spending or travelling.|
C Finish Mihgo's Amigo and verify the reward.|Q|windurst,25||Z|241||POS|62.000,240.000,8||N|Quest completion can be checked from the client. Repeating an already completed quest needs manual tracking; do not assume the first-completion flag proves another payment.|
t Paying Lip Service — check requirements and profit first.|N|Start: Woods. Fame: 1.0. Prerequisite: none listed. Needs: 3 Beehive Chip or 2 Remi Shell. Spreadsheet reward: 150.0. Repeatable: Y. Horizon values may differ from standard LSB details.|
t Verify Paying Lip Service on the Horizon wiki before proceeding.|N|No matching standard quest record found. Use the spreadsheet requirements above; no invented NPC or arrow.|
]],
})
