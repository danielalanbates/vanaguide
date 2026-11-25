-- Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
-- Authored completion answers; keep separate from generated quest_steps.lua.
-- Sources and availability limits: docs/COMPLETE-QUEST-SOLUTIONS.md.
local T = {}
T.quests = {
    ahturhgan = {
        [5] = { scripted = 'full', source = 'https://horizonffxi.wiki/An_Empty_Vessel', steps = {
            'Requires a server with Blue Mage enabled, main-job level 30+, access to Aht Urhgan Whitegate and at least 1,000 gil.',
            'Speak to Waoud in Aht Urhgan Whitegate J-10 and agree to the divination. Use the following ten answers, matching each question topic.',
            'Answer 1 - destiny: choose that you create your own fate.',
            'Answer 2 - goals and sacrifice: agree completely that sacrifice is necessary.',
            'Answer 3 - forbidden scroll: choose to destroy it by burning.',
            'Answer 4 - your life to save many: offer yourself immediately, without reluctance.',
            'Answer 5 - the life you want: choose the chaotic, turbulent life.',
            'Answer 6 - survive as a beast: accept living in beast form.',
            'Answer 7 - a companion betrays you: choose to kill the betrayer.',
            'Answer 8 - a suffering loved one asks for death: agree to their request.',
            'Answer 9 - a dying enemy was your friend: choose to end the suffering.',
            'Answer 10 - an unjust order: act according to your own justice instead of obeying the order.',
            'A perfect reading reveals all five serpents; accept the offer. Wait for the next Vana\'diel day and change zones. If you failed the quiz, the reading costs 1,000 gil and the same day-change plus zoning is needed before another attempt.',
            'Return to Waoud after the wait, complete his next interaction, then speak again to learn which one item he wants. Obtain only the requested item, using the matching clue below.',
            'Golden beach sand means Valkurm Sunsand: buy it at the Auction House, or examine the ??? on the shipwreck at Valkurm Dunes H-9 during dust-storm weather.',
            'A blue river jewel means Siren\'s Tear: examine the moving ??? by the North Gustaberg river at J-8/J-9 with weapon and shield unequipped. If collecting another Tear, speak to Carmelo in Port Bastok first. Barehand fighting can require zoning before collection works.',
            'A red geyser-country stone means Dangruf Stone: examine the ??? on the I-5/J-5 border in Dangruf Wadi during clear weather with no weather effect. It cannot be bought on the Auction House.',
            'Trade the requested item to Waoud to show it to him. He returns it; keep it in your inventory for the final location.',
            'Leave Whitegate through its H-7 gate to Bhaflau Thickets, then enter Aydeewa Subterrane at Bhaflau I-7. Prepare Sneak and Invisible as appropriate for the monsters on the way.',
            'In Aydeewa Subterrane, go to the pool at H-9 and stand in its center while carrying the requested item. When prompted, take his hand and accept. Refusing can cancel the quest.',
            'You return to Whitegate with Blue Mage unlocked and the Mark of Zahak. Speak to Waoud again for the follow-up required by later BLU quests, then change to BLU at a Mog House.'
        } },
    },
}
T.missions = {}
return T
