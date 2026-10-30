#!/usr/bin/env python3
"""Build the unified Horizon solo itinerary from reviewed Horizon wiki facts.
Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
https://batesai.org · help@batesai.org
"""
from pathlib import Path
from urllib.parse import quote

steps = []
def step(title, note, page, zone=None, home=None, start=False, level=None, quest=None):
    tags = []
    if start: tags += ['START', home]
    if home: tags += ['HOME', home]
    if zone is not None: tags += ['Z', str(zone)]
    if level is not None: tags += ['LV', str(level)]
    if quest: tags += ['Q', quest]
    tags += ['SRC', 'https://horizonffxi.wiki/' + quote(page.replace(' ', '_'), safe=':_')]
    if note.startswith('EXP: '):
        exp, remainder = note[5:].split(' GIL: ', 1)
        gil, _, note = remainder.partition('. ')
        tags += ['EXP', exp, 'GIL', gil.rstrip('.') + '.']
    origin = home or 'All starting cities'
    tags += ['N', f'Starting location: {origin}. {note}']
    steps.append('C ' + title + '.|' + '|'.join(tags) + '|')

for home in ['Windurst', "San d'Oria", 'Bastok']:
    step('Start in ' + home, 'This is a leveling route that pays its way with drops, quest turn-ins and optional NM camps. Keep Signet, food, spells and equipment current. Choose Easy Prey you can beat reliably; leave unsafe pulls. Compare Auction House sale proceeds after fees with quest and NPC payouts. Rare drops are opportunities, not guaranteed income. Other city branches are skipped automatically.', 'A_solo_guide_to_leveling', home=home, start=True)
    if home == 'Windurst':
        step('Levels 1-3: Tiny Mandragora and Bumblebee', 'EXP: level-1 Tiny Mandragora near the Windurst exits in East Sarutabaruta. GIL: Bumblebee for Honey and Insect Wing; keep materials for sale rather than dropping them. Stay close to the city while learning your job.', 'East_Sarutabaruta', 116, home, level=3)
        step('Levels 4-6: Mandragora and Crawler', 'EXP: Mandragora (3-6), selecting weaker individuals in East Sarutabaruta. GIL: Crawler (3-6) for Silk Thread and Crawler Calculus. Keep Cornettes from Mandragora for the next turn-in; avoid linked crawler pulls.', 'East_Sarutabaruta', 116, home, level=6)
        step('Quest detour: turn found Cornettes into gil', 'Mandragora-Mad: talk to Yoran-Oran in Windurst Walls E-5. At Windurst fame 1, trade one Cornette for 200 gil; repeat without zoning. Trade one item at a time. Sell valuable alternatives if they pay more. Buying Cornettes from Harmodios costs more than the 200-gil reward, so buying them is a fame expense rather than a profit method.', 'Mandragora-Mad', 239, home, quest='windurst,34')
        step('Levels 7-10: Crawler silk and calculus', 'EXP: Crawler in East Sarutabaruta (3-6) or West Sarutabaruta (3-8), choosing Easy Prey. GIL: Crawler for Silk Thread; retain Crawler Calculus for the next quest. Sell silk stacks when their net sale price beats the turn-in value.', 'Crawler', 116, home, level=10)
        step('Quest detour: Creepy Crawlies', 'Talk to Illu Bohjaa at the Dhalmel Farm, Windurst Woods I-6 (fame 1). Trade three Crawler Calculi for 600 gil. Three Silk Threads also pay 600 gil, but do not surrender them if their net market value is higher. This quest is repeatable.', 'Creepy_Crawlies', 241, home, quest='windurst,39')
    elif home == "San d'Oria":
        step('Levels 1-3: Wild Rabbit outside the gates', 'EXP: Wild Rabbit (1) in West Ronfaure. GIL: Wild Rabbit for Rabbit Hide and Hare Meat; keep saleable stacks while staying near the city exits.', 'Category:Rabbits', 100, home, level=3)
        step('Levels 4-6: Forest Hare and bat wings', 'EXP: weaker Forest Hare in West Ronfaure (the family listing spans 1-5). GIL: Ding Bats and Mouse Bats for Bat Wings; take nighttime bat opportunities without walking into stronger groups. Save pairs for Secodiand.', 'Fear_of_the_Dark', 100, home, level=6)
        step("Quest detour: Lufet's Lake Salt", 'Speak to Nogelle, Port San d\'Oria G-7 (fame 1). Kill River Crabs at Knightwell in West Ronfaure for three Lufet Salts, then trade the three to Nogelle for 600 gil. The salt is Exclusive and cannot be bought; this quest is not repeatable.', "Lufet's_Lake_Salt", 232, home, quest='sandoria,81')
        step('Levels 7-10: finish the Ronfaure material circuit', 'EXP: Forest Hare in West Ronfaure, selecting individuals that still give EXP. GIL: Ding Bats or Mouse Bats for Bat Wings. Rabbit Hide and Hare Meat remain extra sale items; move on at level 10 instead of grinding Too Weak prey.', 'Category:Rabbits', 100, home, level=10)
        step('Quest detour: Fear of the Dark', 'Talk to Secodiand, Northern San d\'Oria F-6 (fame 1), then trade two Bat Wings for 200 gil. Further pairs can repeat the quest. Compare 200 gil per pair with the net Auction House price before trading all your wings.', 'Fear_of_the_Dark', 231, home, quest='sandoria,78')
    else:
        step('Levels 1-3: Huge Hornet outside Bastok', 'EXP: level-1 Huge Hornet in South Gustaberg. GIL: the same Huge Hornets for Honey and Insect Wing. Keep saleable materials and stay near a city exit.', 'South_Gustaberg', 107, home, level=3)
        step('Levels 4-6: Stone Eater ore circuit', 'EXP: weaker Stone Eaters in South Gustaberg (1-5). GIL: Stone Eater for Zinc Ore, Flint Stone and possible Silver Ore. Keep ore for sale; do not assume every worm drops every listed item.', 'South_Gustaberg', 107, home, level=6)
        step("Quest detour: The Siren's Tear", 'Talk to Wahid, Bastok Mines I-8 (fame 1). Find the moving ??? beside the river in eastern North Gustaberg J-8/J-9. Unequip weapon and shield before examining it; trade the Tear to Wahid for 150 gil. For another Tear, talk to Carmelo in Port Bastok first. Monk can fail to pick it up even unarmed; fighting barehanded also requires zoning before trying again. Skip the detour if this interferes with your current job.', "The_Siren's_Tear", 234, home, quest='bastok,0')
        step('Levels 7-10: Rock Lizard and Wild Onion', 'EXP: Rock Lizard (3-8) in South Gustaberg. GIL: weaker Goblin Thugs for Wild Onion, then compare sale value with the Gourmet turn-in. Goblins aggro and link; pull isolated Easy Prey. The next Bastok NM option returns to the lizards at F-8.', 'South_Gustaberg', 107, home, level=10)
        step('Quest detour: Gourmet at the profitable time', 'Speak to Salimah, Bastok Markets L-8 (fame 1). A Wild Onion pays 350 gil at 12:00-17:59 Vana\'diel time. Treant Bulb at 06:00-11:59 or Sleepshroom at 18:00-05:59 pays 200; wrong-time items pay only 100. Change areas before repeating. Use found materials only when the payout beats selling them.', 'Gourmet', 235, home, quest='bastok,12')

camps = [
 (11,15,'Canyon Rarab',117,'Tahrongi Canyon','Canyon Rarab (7-10)','Crawler in East/West Sarutabaruta','Silk Thread; keep Calculus for Creepy Crawlies','Category:Rabbits','The gil target is a return trip to the starter area, not a mob in this Tahrongi camp.'),
 (16,20,'Wild Dhalmel',117,'Tahrongi Canyon','Wild Dhalmel (14-16)','Wild Dhalmel','Dhalmel Hide and Dhalmel Meat','Category:Dhalmels','Pull one at a time: dhalmels link. Use the weaker starter prey if these are not manageable yet.'),
 (21,25,'Wild Dhalmel',117,'Tahrongi Canyon','Wild Dhalmel (14-16)','Wild Dhalmel','Dhalmel Hide and Dhalmel Meat','A_solo_guide_to_leveling','This follows the Horizon solo author\'s level-20-25 farming approach; favor kill speed over difficult pulls.'),
 (26,30,'Bull Dhalmel',118,'Buburimu Peninsula','Bull Dhalmel (20-24)','Carnivorous Crawler (20-23), or Bull Dhalmel','Silk Thread from crawlers; hides and meat from dhalmels','Buburimu_Peninsula','Both families link. Keep saleable materials as stacks and avoid Goblin paths.'),
 (31,35,'Cape Dhalmel',118,'Buburimu Peninsula','Cape Dhalmel (24-26)','Cape Dhalmel','Dhalmel Hide and Dhalmel Meat','Cape_Dhalmel','This is an actual Horizon custom monster. There are fewer spawns than the Bull Dhalmel circuit, so return to bulls if contested.'),
 (36,40,'Giant Spider',114,'Eastern Altepa Desert','Giant Spider (30-34)','Giant Spider','Spider Web for clothcraft buyers','Giant_Spider','Spiders link and Sickle Slash can spike damage. Webs are a scarce drop, so this is a material opportunity rather than steady guaranteed cash.'),
 (41,45,'Desert Dhalmel',114,'Eastern Altepa Desert','Desert Dhalmel (38-44), choosing Easy Prey','Desert Dhalmel','Dhalmel Hide and Dhalmel Meat','Eastern_Altepa_Desert','Ignore higher-level individuals until your job can handle them; avoid linked pulls and nearby Antica.'),
 (46,50,'Royal Leech',176,'Sea Serpent Grotto, first map','Royal Leech (35-38)','Royal Leech','Leech Saliva','Royal_Leech','Check vendor value against the market. Do not budget Carbuncle\'s Ruby as gil: it is an unlock item. Leeches link.'),
 (51,55,'Master Coeurl',121,"The Sanctuary of Zi'Tah",'Master Coeurl (44-47)','Master Coeurl','Coeurl Meat, Coeurl Hide and Coeurl Whisker',"The_Sanctuary_of_Zi'Tah",'These coeurls aggro by sight. Keep a safe pull position and a way home.'),
 (56,60,'Rime Lynx',111,"Beaucedine Glacier near Fei'Yin",'Rime Lynx (51-53)','Rime Lynx','Coeurl Meat, Coeurl Hide and Coeurl Whisker','Rime_Lynx','This Horizon custom mob uses a lynx appearance but does not drop Lynx Hide. It aggros and links; separate your pulls.'),
 (61,65,'Variable Hare',5,'Uleguerand Range','Variable Hare (58-61)','Rime Lynx in Beaucedine Glacier, or Variable Hare locally','Coeurl materials on the return trip; Hare Meat and Rabbit Hide locally','Variable_Hare','Choose the local option for continuous EXP or the lynx return trip for coeurl materials. Bring suitable travel protection.'),
 (66,70,'Buffalo',5,'Uleguerand Range','Buffalo (62-65)','Buffalo','Buffalo Hide, Buffalo Meat and Uleguerand Milk','Uleguerand_Range','Buffalo are aggressive. Identify Buffalo carefully rather than pulling higher-level King Buffalo.'),
 (71,75,'Polar Hare',5,'Uleguerand Range','Polar Hare (65-68)','Buffalo (62-65)','Buffalo Hide and Buffalo Meat','Uleguerand_Range','The gil target is the lower-level Buffalo population. Use safe pulls instead of chasing a costly death at the final levels.'),
]
for lo,hi,mob,zone,place,exp,gil,loot,page,hazard in camps:
    if lo >= 51:
        previous=lo-1
        title={50:'In Defiant Challenge',55:'Atop the Highest Mountains',60:'Whence Blows the Wind',65:'Riding on the Clouds',70:'Shattering Stars'}[previous]
        step(f'Level {previous} cap: {title}', f'Before earning toward {hi}, clear the appropriate limit break if this character is still capped at {previous}. Maat is in Ru\'Lude Gardens H-5. Horizon raises the cap in five-level stages to 75. The 70-to-75 fight depends on your job; use that job\'s walkthrough and arrange help for earlier dangerous objectives when needed.', 'Limit_Break', 243)
    step(f'Levels {lo}-{hi}: {mob}', f'EXP: {exp} — {place}. GIL: {gil} — {loot}. {hazard} Continue until level {hi}; if prey becomes Too Weak, move to the next appropriate camp rather than farming it for EXP.', page, zone, level=hi)
    if lo == 11:
        step('Optional NM at 12+: Spiny Spipi', 'Return to East Sarutabaruta I-7/J-7 and kill the Crawler placeholder while farming Silk Thread. Spiny Spipi is level 9-10; its notable drop is Mist Silk Cape. Most jobs can solo it around level 10+, but your setup determines safety. Leave if competition or waiting costs more than ordinary farming.', 'Spiny_Spipi', 116, home='Windurst')
        step('Optional NM at 12+: Jaggedy-Eared Jack', 'Farm Forest Hare around West Ronfaure G-9/H-9 while camping the level-9-10 Jack lottery. The notable drop is Rabbit Charm. Keep Rabbit Hides and Hare Meat while waiting; check the current Charm price before choosing a long camp.', 'Category:Rabbits', 100, home="San d'Oria")
        step('Optional NM at 12+: Leaping Lizzy', 'Farm Rock Lizard around the central rock pillar at South Gustaberg F-8. Lizzy is level 10-11 and drops the sellable Leaping Boots on Horizon; the Exclusive Bounding Boots are a BCNM reward instead. Her spawn is a lottery, so do not treat a long wait as guaranteed income. Pull without lizard links.', 'Leaping_Lizzy', 107, home='Bastok')
    if lo == 31:
        step('Optional NM at 35+: Valkurm Emperor', 'Travel detour to Valkurm Dunes D-8/F-8. Kill the Damselfly placeholder and retain ordinary drops while waiting for the level-29-30 Emperor. Horizon awards the sellable Emperor Hairpin, not the Exclusive Empress Hairpin. The window begins 60 minutes after the previous kill; the lottery may still take hours. Flies link. Skip this if your job cannot safely solo the encounter.', 'Valkurm_Emperor', 103)
    if lo == 51:
        step("Optional cash detour: Tiger's Teeth", 'If San d\'Oria fame is at least 3, farm Forest Tiger in Jugner Forest (22-25) or Sabertooth Tiger in Batallia Downs (28-32) for Black Tiger Fangs. Trade sets of three to Taumila in Southern San d\'Oria E-9 for 2,100 gil. This is a repeatable cash detour, not the EXP camp; sell the fangs instead when net market proceeds are higher.', 'Reputation-guide', 230)
    if lo == 61:
        step('Optional NM at 62+: Dune Widow', 'Return to Eastern Altepa Desert G-8. Kill Giant Spiders as placeholders and keep Spider Webs while camping Dune Widow (45-47). Spider Torque is the notable sale candidate. The monster page reports soloability for any job at 62+; still prepare for heavy damage. The window opens about an hour after the last kill, with lottery uncertainty afterward.', 'Dune_Widow', 114)
    if lo == 71:
        step('Optional NM at 75: Bonnacon', 'Only with a solo setup that can handle the fight, use the Buffalo around Uleguerand Range D-8 as placeholders for Bonnacon (69). Farm Buffalo Hide and Meat while waiting; Cure Clogs and Tredecim Scythe are the named NM sale candidates. The lottery window starts after one hour and can take much longer. Skip the NM if its status attacks or nearby aggressive monsters make the camp unsafe.', 'Bonnacon', 5)
step('Level 75: keep your best gil circuit', 'Horizon stops at 75. Compare your actual sales from coeurl materials, Buffalo Hide/Meat, silk and the NM camps; keep the circuit that works for your job and available time. Rare NM drops can be worth selling, but ordinary materials pay while a lottery does not appear. Press Done to mark this guide complete.', 'Character_Progression_Guide_1-75_for_New_Players')
header='''-- Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
-- Generated by tools/build_horizon_solo.py. Reviewed source facts: docs/HORIZON-GIL-ROUTE.md.
local G = require("core.guide")
G.register({
    server = "HorizonXI",
    name = "Solo Guide - HorizonXI",
    progress_id = "Solo Gil - HorizonXI",
    legacy_progress_id = "Solo EXP - HorizonXI",
    desc = "Solo level 1-75 with separate EXP and Gil goals: choose your starting city, then follow camps, material drops, useful quest detours and optional notorious monsters. Horizon wiki links are attached to each step.",
    levels = "1-75 ALPHA",
    steps = [[
'''
Path('Vanaguide/guides/solo_horizon.lua').write_text(header+'\n'.join(steps)+'\n]],\n})\n')
print(len(steps),'source-linked steps; three city branches and a shared 11-75 route')
