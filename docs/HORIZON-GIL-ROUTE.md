# Horizon Solo Guide itinerary

Reviewed 2026-10-30 using HorizonXI Wiki pages and indexed copies of those pages. The wiki
is the source for included monster levels, drops, quest payments, NPC locations and named
Horizon changes. Player-level camp bands are authored suggestions, not a live test proving
all jobs can solo every encounter. Each combat instruction requires a manageable Easy Prey
pull; NM detours are optional. No fixed market prices or hourly profits are invented.

There are 44 stored steps and 30 visible steps per city route. Three distinct 1–10 branches
join a shared 11–75 itinerary; their optional starter NMs remain city-specific. The reader
skips other-city steps, keeps the selected origin at shared camps, and counts only the
selected route. All 16 leveling bands have explicit EXP and gil mobs. This is a leveling
route with material farming, six starter quest detours, a later Tiger's Teeth cash detour,
and six NM opportunities across the three origins.

## Checked Horizon details

- The Siren's Tear: Wahid in Bastok Mines I-8, river J-8/J-9, unarmed collection, 150 gil.
  Carmelo must be spoken to for another Tear. The wiki documents Monk/barehand complications.
- Gourmet: Salimah Markets L-8, onion 350 gil at noon–17:59, bulb/mushroom 200 at their
  specified hours, wrong-time reward 100, change areas before repeating.
- Lufet's Lake Salt: three Exclusive salts from Knightwell River Crabs, Nogelle Port G-7,
  600 gil, not repeatable. Fear of the Dark: Secodiand Northern F-6, two wings for 200.
- Mandragora-Mad: Yoran-Oran Walls E-5, one Cornette for 200, no zoning; buying Cornettes
  at the listed shop price loses money. Creepy Crawlies: Illu Bohjaa Woods I-6, three
  Calculi or three Silk Threads for 600. The route recommends Calculi when silk sells higher.
- Lizzy drops sellable Leaping Boots on Horizon. Emperor drops Emperor Hairpin; Exclusive
  versions belong to BCNMs. Their levels are 10–11 and 29–30 respectively.
- Cape Dhalmel is Horizon custom, 24–26, Buburimu. Rime Lynx is Horizon custom, 51–53,
  Beaucedine, and drops coeurl materials rather than Lynx Hide.
- Dune Widow is 45–47, G-8 Eastern Altepa; the wiki's general solo recommendation is 62+.
  Bonnacon is 69 at the D-8 Buffalo lottery; the route reserves it for capable level-75 setups.
- San d'Oria quest flags were checked against the catalogue: Fear of the Dark 78,
  Lufet's Lake Salt 81. Do not substitute unrelated quest IDs based on names alone.

The previous 61-quest list is archived at `archive/2026-10-30/solo_gil-quest-only.lua`.
It is not loaded or bundled. Its generic standard-LSB procedures have not all been checked
against Horizon and must not be described as verified. The new active itinerary uses
reviewed Horizon instructions and removes the repeated “may differ” placeholders.

Run `python3 tools/build_horizon_solo.py` to regenerate. The source inventory below records
all shipped steps and their principal reference; a step can also use facts reviewed on the
related monster, item and zone pages cited throughout this work. Cached wiki text is not
published. Offline tests check source links, all city branches, level coverage, paired mob
targets, correct quest flags, branch skipping, and retention of the superseded reference.

## Step source inventory

| Step | Instruction | Origin | Source |
| --- | --- | --- | --- |
| 1 | Start in Windurst. | Windurst | [Wiki](https://horizonffxi.wiki/A_solo_guide_to_leveling) |
| 2 | Levels 1-3: Tiny Mandragora and Bumblebee. | Windurst | [Wiki](https://horizonffxi.wiki/East_Sarutabaruta) |
| 3 | Levels 4-6: Mandragora and Crawler. | Windurst | [Wiki](https://horizonffxi.wiki/East_Sarutabaruta) |
| 4 | Quest detour: turn found Cornettes into gil. | Windurst | [Wiki](https://horizonffxi.wiki/Mandragora-Mad) |
| 5 | Levels 7-10: Crawler silk and calculus. | Windurst | [Wiki](https://horizonffxi.wiki/Crawler) |
| 6 | Quest detour: Creepy Crawlies. | Windurst | [Wiki](https://horizonffxi.wiki/Creepy_Crawlies) |
| 7 | Start in San d'Oria. | San d'Oria | [Wiki](https://horizonffxi.wiki/A_solo_guide_to_leveling) |
| 8 | Levels 1-3: Wild Rabbit outside the gates. | San d'Oria | [Wiki](https://horizonffxi.wiki/Category:Rabbits) |
| 9 | Levels 4-6: Forest Hare and bat wings. | San d'Oria | [Wiki](https://horizonffxi.wiki/Fear_of_the_Dark) |
| 10 | Quest detour: Lufet's Lake Salt. | San d'Oria | [Wiki](https://horizonffxi.wiki/Lufet%27s_Lake_Salt) |
| 11 | Levels 7-10: finish the Ronfaure material circuit. | San d'Oria | [Wiki](https://horizonffxi.wiki/Category:Rabbits) |
| 12 | Quest detour: Fear of the Dark. | San d'Oria | [Wiki](https://horizonffxi.wiki/Fear_of_the_Dark) |
| 13 | Start in Bastok. | Bastok | [Wiki](https://horizonffxi.wiki/A_solo_guide_to_leveling) |
| 14 | Levels 1-3: Huge Hornet outside Bastok. | Bastok | [Wiki](https://horizonffxi.wiki/South_Gustaberg) |
| 15 | Levels 4-6: Stone Eater ore circuit. | Bastok | [Wiki](https://horizonffxi.wiki/South_Gustaberg) |
| 16 | Quest detour: The Siren's Tear. | Bastok | [Wiki](https://horizonffxi.wiki/The_Siren%27s_Tear) |
| 17 | Levels 7-10: Rock Lizard and Wild Onion. | Bastok | [Wiki](https://horizonffxi.wiki/South_Gustaberg) |
| 18 | Quest detour: Gourmet at the profitable time. | Bastok | [Wiki](https://horizonffxi.wiki/Gourmet) |
| 19 | Levels 11-15: Canyon Rarab. | All starts | [Wiki](https://horizonffxi.wiki/Category:Rabbits) |
| 20 | Optional NM at 12+: Spiny Spipi. | Windurst | [Wiki](https://horizonffxi.wiki/Spiny_Spipi) |
| 21 | Optional NM at 12+: Jaggedy-Eared Jack. | San d'Oria | [Wiki](https://horizonffxi.wiki/Category:Rabbits) |
| 22 | Optional NM at 12+: Leaping Lizzy. | Bastok | [Wiki](https://horizonffxi.wiki/Leaping_Lizzy) |
| 23 | Levels 16-20: Wild Dhalmel. | All starts | [Wiki](https://horizonffxi.wiki/Category:Dhalmels) |
| 24 | Levels 21-25: Wild Dhalmel. | All starts | [Wiki](https://horizonffxi.wiki/A_solo_guide_to_leveling) |
| 25 | Levels 26-30: Bull Dhalmel. | All starts | [Wiki](https://horizonffxi.wiki/Buburimu_Peninsula) |
| 26 | Levels 31-35: Cape Dhalmel. | All starts | [Wiki](https://horizonffxi.wiki/Cape_Dhalmel) |
| 27 | Optional NM at 35+: Valkurm Emperor. | All starts | [Wiki](https://horizonffxi.wiki/Valkurm_Emperor) |
| 28 | Levels 36-40: Giant Spider. | All starts | [Wiki](https://horizonffxi.wiki/Giant_Spider) |
| 29 | Levels 41-45: Desert Dhalmel. | All starts | [Wiki](https://horizonffxi.wiki/Eastern_Altepa_Desert) |
| 30 | Levels 46-50: Royal Leech. | All starts | [Wiki](https://horizonffxi.wiki/Royal_Leech) |
| 31 | Level 50 cap: In Defiant Challenge. | All starts | [Wiki](https://horizonffxi.wiki/Limit_Break) |
| 32 | Levels 51-55: Master Coeurl. | All starts | [Wiki](https://horizonffxi.wiki/The_Sanctuary_of_Zi%27Tah) |
| 33 | Optional cash detour: Tiger's Teeth. | All starts | [Wiki](https://horizonffxi.wiki/Reputation-guide) |
| 34 | Level 55 cap: Atop the Highest Mountains. | All starts | [Wiki](https://horizonffxi.wiki/Limit_Break) |
| 35 | Levels 56-60: Rime Lynx. | All starts | [Wiki](https://horizonffxi.wiki/Rime_Lynx) |
| 36 | Level 60 cap: Whence Blows the Wind. | All starts | [Wiki](https://horizonffxi.wiki/Limit_Break) |
| 37 | Levels 61-65: Variable Hare. | All starts | [Wiki](https://horizonffxi.wiki/Variable_Hare) |
| 38 | Optional NM at 62+: Dune Widow. | All starts | [Wiki](https://horizonffxi.wiki/Dune_Widow) |
| 39 | Level 65 cap: Riding on the Clouds. | All starts | [Wiki](https://horizonffxi.wiki/Limit_Break) |
| 40 | Levels 66-70: Buffalo. | All starts | [Wiki](https://horizonffxi.wiki/Uleguerand_Range) |
| 41 | Level 70 cap: Shattering Stars. | All starts | [Wiki](https://horizonffxi.wiki/Limit_Break) |
| 42 | Levels 71-75: Polar Hare. | All starts | [Wiki](https://horizonffxi.wiki/Uleguerand_Range) |
| 43 | Optional NM at 75: Bonnacon. | All starts | [Wiki](https://horizonffxi.wiki/Bonnacon) |
| 44 | Level 75: keep your best gil circuit. | All starts | [Wiki](https://horizonffxi.wiki/Character_Progression_Guide_1-75_for_New_Players) |

## Unified guide and separate goals

`Solo Guide - HorizonXI` replaces both EXP and Gil menu entries. Each leveling step keeps
EXP and Gil in separate data tags, rendered as two bullet points by both readers. Notes,
quest detours, NM opportunities, city choices and the 30-step per-origin itinerary remain.
`progress_id = "Solo Gil - HorizonXI"` keeps the stable bookmark identity for the previous
itinerary; `legacy_progress_id` identifies the old EXP route for native migration by level
band. Retired EXP source and generator are archived outside the active guide directory.
The addon resolves old guide names to the unified guide and uses the stable Gil save key.
A legacy addon EXP-only index cannot safely identify its new instruction and starts the
unified route unless an existing Gil bookmark is available; old EXP saved data is retained.
