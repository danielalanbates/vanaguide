# Per-server data sources (survey 2026-10-28)

Where VanaGuide can get each FFXI on Mac server's own quests, gear, crafting and skill rules.
Gathered by read-only web research; every claim below has its URL in the evidence list.

| Server | Era | Wiki | Public server data | Best source |
|---|---|---|---|---|
| MistXI | Two servers. Main (play.mistxi.com) has a level 75 cap. Legacy (legacy… | No wiki found. Static site with about 35 URLs in its sitemap (sitemap.… | https://github.com/mistxi/mistxi_launcher (Windows .NET 8 launcher, v1.6.0, last push 2026… | Use stock LandSandBoat data for WotG-era, 75-cap content, then apply a small hand-written override file built from https://mistxi.com/server-info/: EXP 3x, spee… |
| Moghouse XI (MogHouse.cc / BNET.cc 'FunServer') | Not stated. The image tracks the newest LandSandBoat 'base' branch wit… | No server wiki. The site is a WordPress-style hub (its robots.txt disa… | https://github.com/tagban/moghouse-lsb — the server image MogHouse runs: upstream LandSand… | Stock LandSandBoat at the commit labeled on the image (cc.moghouse.lsb-commit), with tagban/moghouse-lsb modules/init.txt and modules/moghouse/ as the overlay. … |
| LevelDown 99 (FFXI Level Down; sister server LevelDown 75) | LevelDown 99 is a '99/99 Custom Server' with all expansions enabled (A… | Fandom MediaWiki 1.43.9. api.php works without authentication. | No server fork or scripts found. GitHub repo and code searches for leveldown, leveldownffx… | Fetch all 103 main-namespace pages from the Fandom MediaWiki API with action=query&list=allpages&aplimit=500, then action=parse&prop=wikitext&formatversion=2 fo… |
| Scythe | Level 99, plus Master Levels up to 50. The initial level cap is 50, li… | No wiki. A static Cloudflare Pages site of hand-written HTML guide pag… | none | Pull the static JSON directly with plain HTTP GETs: https://scythe-bbq.pages.dev/data/{items,equipment,mobs,spells,weaponskills,mobskills,nm_hunts,shops,drops,r… |
| Olympus XI | Level 75 cap ('75 era'), classic Vana'diel through Treasures of Aht Ur… | In-game wiki only (/owiki in the Olympus launcher addon). Its data is … | https://github.com/bobertdrake/olympus-xi-patch: client DAT patches, launcher, VanaCore an… | Ingest the GitHub release asset: read wiki.json (version and sha256) from https://github.com/bobertdrake/olympus-xi-patch/releases/download/wiki/wiki.json, down… |
| Legendary (Relaunch) | Level 99 at creation with no limit break, retail content through Seeke… | Static documentation site built with MkDocs Material, which acts as th… | https://github.com/richardknutzjr/Relaunch is linked from the site, but returns 404 and gi… | Fetch https://ffxi-legendary.com/search/search_index.json (all 136 pages as text and HTML sections, one request) for guide prose and the rules layer, especially… |
| Vanadreams | Level 99. Every expansion through The Voracious Resurgence, plus Rhaps… | Custom static site (not MediaWiki): a JS reader (app.js) over JSON fil… | https://github.com/VanaDreams/vanadreams-launcher (Lua, Ashita addons + launcher UI, pushe… | Ingest the wiki's own JSON directly: GET https://vanadreams.org/wiki/data/{meta,index,quests,walk-quests,missions,walk-missions,recipes,synergy,jobs,keyitems,ba… |
| DriftwoodXI | Level 99 from first login; limit-break quests removed (Maat hands over… | None found. The website itself is the reference: /custom, /features/* … | https://github.com/DriftwoodGaming/server — fork of LandSandBoat/server; default branch 'b… | No wiki and no public server code with the custom systems. Scrape the official site pages (robots allows all but /reset and /delete): /custom (full change list)… |
| PegasusXI | Level 99 (MAX_LEVEL 99, INITIAL_LEVEL_CAP 50 in repo). Site: 'Playable… | MediaWiki 1.43.9 (self-hosted, api.php at /w/api.php), content 'text a… | https://github.com/aremais/PegasusXI — LandSandBoat server (not a GitHub fork; created 202… | Treat PegasusXI as near-stock LandSandBoat: build its guide from the aremais/PegasusXI repo (scripts/quests, scripts/missions, sql/*.sql for items, drops, recip… |
| HorizonXI | Level 75 cap 'Era+'. Launched 2022-12-17 in the CoP era. Treasures of … | MediaWiki, self-hosted at horizonffxi.wiki. Community-run: the front p… | none | No public source code exists, so the community wiki is the only full data source. Its Horizon_Changes page (about 120k characters) plus Category:Horizon_Changes… |
| CatsEyeXI | Level 75 cap (settings MAX_LEVEL=75, INITIAL_LEVEL_CAP=50). Enabled pe… | MediaWiki on BG-Wiki, in a 'CatsEyeXI...' page namespace (catseyexi.co… | https://github.com/CatsAndBoats/catseyexi (public LSB fork; default branch 'base' last syn… | Three layers. (1) Pull the public LSB fork CatsAndBoats/catseyexi (branch 'stable') and diff settings/default/main.lua and map.lua against upstream LSB to get m… |
| AscensionXI | Level 75 cap, Wings of the Goddess era without the three add-on scenar… | Custom first-party wiki on the server's own site: player-editable, wit… | none | No public source code, so the first-party wiki at ascensionffxi.com/wiki is the source. It is server-data-backed (21,426 pages in sitemap.xml with item stats an… |

## Details

### MistXI

**Wiki:**
- https://mistxi.com/server-info/
- https://mistxi.com/docs/
- https://mistxi.com/docs/commands/
- https://mistxi.com/docs/new-player-faq/

**Reading rules:** robots.txt is 'User-agent: * / Disallow:' (everything allowed) and lists a sitemap at https://mistxi.com/sitemap.xml. The terms have no clause on scraping or crawling. Section 4 bans 'automation' only in reference to the game service. The site says '© 2026 MistXI. All rights reserved.' There is no API. The auction house page loads its data dynamically from an endpoint I did not identify.

**Quests:**
- None documented. The site gives no list of custom, removed or altered quests.

**Missions:**
- None documented.

**Crafting:**
- Server Info says crafting skill-ups are 'Increased', with no rate given.
- No crafting cap or recipe changes are documented.

**Combat skills:**
- Server Info says weapon skill-ups are 'Increased', with no rate given.
- HP and MP multipliers are 'slightly increased', with no values given.
- Healing tick frequency is doubled.
- TP lost on /heal is reduced by 90%.

**Gear:**
- Login campaign reward tiers: 10pt potions and medicine, 50pt food, 100pt EXP and skill books, 300pt 12 stacks of 50pt food, 500pt furnishings and Mog House items, 750pt mounts, 1000pt endgame support items, 1500pt endgame or rare gear. Tiers may rotate.
- Owning more than one EXP ring is allowed.
- No drop-rate multiplier and no AF/relic changes are documented. The home page mentions 'Balanced job adjustments with transparent patch notes', but I found no patch notes page.

**Other:**
- EXP rate is 3x.
- Movement speed is 1.5x.
- Starting gil is 25,000 and starting inventory is 80 slots.
- All maps are enabled.
- Home Point warping and healing are on, plus outpost warps.
- Retail Trust system. Fields and Grounds of Valor are enabled, with tomes.
- Up to 2 characters per IP.
- Slumbering Gods Lottery: 1,000,000 gil monthly, 3-month cooldown per character, must have logged in within the last 14 days.
- Login campaign: 100 points per day, plus 300 bonus points on the 3rd consecutive day. Resets on the 1st of the month. Rewards come from the Greeter Moogle in Port San d'Oria, Port Bastok and Windurst Walls.
- Player commands: !help, !status, and !warp (only if enabled).
- The auction house is automated during low-activity periods ('Economy stimulation').
- GlobalMist linkshell for new players.

**Best source:** Use stock LandSandBoat data for WotG-era, 75-cap content, then apply a small hand-written override file built from https://mistxi.com/server-info/: EXP 3x, speed 1.5x, skill-ups increased, healing changes, the login campaign, and the 25k gil / 80-slot start. Re-check server-info and /news/ through the sitemap now and then. The site is small and static, so a manual summary works better than a scraper. There is no public server fork, so quest, recipe and drop data can't be diffed.

**Unknown:**
- Exact weapon, magic and crafting skill-up multipliers.
- Crafting caps (probably retail 100/110, not confirmed).
- Drop-rate multipliers.
- Which job adjustments were made. The site mentions patch notes, but I found no page for them.
- Whether the 75 and 99 servers differ beyond the level cap.
- The auction house API endpoint, which may be usable for live prices.
- Whether a wiki or knowledge base exists inside Discord. I did not join it.

**Evidence:**
- https://mistxi.com — 'A classic-era FFXI private server with thoughtful quality-of-life improvements'. Lists the launcher, lottery, login campaign, Discord authentication and GlobalMist.
- https://mistxi.com/server-info/ — level caps 75 (play.mistxi.com) and 99 (legacy.mistxi.com), content up to WotG, EXP 3x, movement 1.5x, weapon and crafting skill-ups increased, healing ticks doubled, 90% less TP lost on heal, 25,000 starting gil, 80 inventory slots, all maps, HP warps, 2 characters per IP, lottery and login campaign tiers.
- https://mistxi.com/news/changing-our-focus/ — dated 2026-01-05, development moves to the 75 era and the 99 server gets basic support.
- https://mistxi.com/docs/ — pages for commands (!help, !status, !warp) and the New Player FAQ.
- https://mistxi.com/robots.txt — 'Disallow:' is empty and a sitemap is listed.
- https://mistxi.com/terms/ — no scraping clause, 'automation' is banned in the Service.
- https://github.com/mistxi/mistxi_launcher — README describes the launcher v1.6.0, which handles Ashita v4, XiLoader and XIPivot.
- gh search repos mistxi — returned only texastoastt/mistxi (README only) and mistxi/mistxi_launcher.

### Moghouse XI (MogHouse.cc / BNET.cc 'FunServer')

**Wiki:**
- https://moghouse.cc/getting-setup/
- https://moghouse.cc/gm-commands/
- https://moghouse.cc/other-servers/

**Reading rules:** robots.txt: 'User-agent: * / Crawl-delay: 10', and it disallows /admin/, /includes/, /config/, /logs/, /backup/, /.env, /wp-admin/ and /wp-includes/. I saw no API. The site has about 15 content pages with no guide content specific to this server.

**Quests:**
- Optional LandSandBoat modules that would change quests are all commented out (off) in modules/init.txt: quest_workarounds.lua (would make Wish Upon a Star completable), soa_remove_imprimatur_gate.lua, wotg_decouple_story_missions_from_nation_quests.lua. So quests are stock LandSandBoat.

**Missions:**
- Stock LandSandBoat. The SoA and WotG mission-gate modules are present but off.

**Crafting:**
- No crafting changes appear in the repository. chocobo_raising_qol.lua is off.
- The !shop command (permission 0, so any player) sells all 8 HQ crystals at 3,000 gil each on page 1. Other pages: Food, Meds, Misc, Tools, COR dice, fireworks, swimwear.

**Combat skills:**
- Nothing in the public repository changes skill-ups. Rates would be in the private settings/*.lua files.

**Gear:**
- !gmgear gives GM body, head, legs, feet and hands (item IDs 12551, 12523, 12807, 12935, 12679). Its permission is 1 (GM level), not 0.
- No custom items or drop-rate changes are in the repository. Drop rates would be in the private settings repository.

**Other:**
- Modules that are on: test_npcs_in_gm_home.lua, announce_player_login.lua, the discord_bridge, moghouse/commands, moghouse/cpp (knockback, mount, jump, skyfx), and moghouse/jump.lua (/jump lifts the player onto rocks and steps).
- GM commands in the repository: aery, apocnigh, bringall, cerberus, chocobo, dominion, down, fixspeed, flash, fly, flymount, gmgear, gmisland, grats, home, jinx, job, kill, kirin, learnmagic, mobmp, nopants, nuke, seahorror, shop, signet, skyfx, slap, starlight, up. Each one's GM level is in tests/commands.lua.
- !home and !signet exist, but I did not check their permission levels.
- Off in the repository: homepoint_heal, ah_pagination, claim_shield, custom_hnm_system, persist_nm_time_of_deaths, mission_wardrobe_unlocks, and others.

**Best source:** Stock LandSandBoat at the commit labeled on the image (cc.moghouse.lsb-commit), with tagban/moghouse-lsb modules/init.txt and modules/moghouse/ as the overlay. Pull it with the GitHub API (gh api repos/tagban/moghouse-lsb/contents/...). This is a fun or GM-sandbox server with no content changes, so VanaGuide can treat it as 'LSB default' and add a short list of the player commands (permission 0).

**Unknown:**
- Level cap, expansions, EXP rate, skill-up and crafting rates, drop rates. These are in the private settings/ repository.
- The GM level given to ordinary players. 'GM Commands setup!' suggests players may get a GM level, which would make most commands usable. Not confirmed.
- Whether tagban (the repository owner) is the moghouse.cc operator. The README names moghouse.cc and ffxi.cc, but I saw no confirmation on the site itself.
- Population and whether the server is up. The site's status widget did not render.

**Evidence:**
- https://moghouse.cc — 'Moghouse is back as a FunServer. GM Commands setup! Use: --server ffxi.cc'. It is BNET.cc's successor and links to the LandSandBoat What Works wiki.
- https://moghouse.cc/getting-setup/ — server address '--server ffxi.cc' and Discord. No level cap, EXP or expansion information.
- https://moghouse.cc/robots.txt — Crawl-delay 10 plus admin and WordPress disallows.
- https://github.com/tagban/moghouse-lsb (README) — 'The server image MogHouse (ffxi.cc) runs: LandSandBoat, newest, with MogHouse's modules'. Settings stay in a private repository.
- https://github.com/tagban/moghouse-lsb/blob/main/modules/init.txt — lists the modules that are on and the optional LandSandBoat modules that are commented out.
- https://github.com/tagban/moghouse-lsb/blob/main/modules/moghouse/commands/shop.lua — permission 0, HQ crystals at 3,000 gil each.
- https://github.com/tagban/moghouse-lsb/blob/main/modules/moghouse/commands/gmgear.lua — permission 1, gives GM gear.

### LevelDown 99 (FFXI Level Down; sister server LevelDown 75)

**Wiki:**
- https://ffxileveldown.fandom.com/wiki/FFXILevelDown_Wiki
- https://ffxileveldown.fandom.com/wiki/About_Us
- https://ffxileveldown.fandom.com/wiki/Level_Down_75
- https://ffxileveldown.fandom.com/wiki/Custom_Content
- https://ffxileveldown.fandom.com/wiki/Custom_Quests
- https://ffxileveldown.fandom.com/wiki/Custom_NPCS_Adjustments
- https://ffxileveldown.fandom.com/wiki/Item_Adjustments
- https://ffxileveldown.fandom.com/wiki/Custom_Skills
- https://ffxileveldown.fandom.com/wiki/Custom_Crafting_Recipes
- https://ffxileveldown.fandom.com/wiki/LD_75_Crafting_Guide
- https://ffxileveldown.fandom.com/wiki/Mythic_Weapons
- https://ffxileveldown.fandom.com/wiki/Sky_/_Sea_Adjustments
- https://ffxileveldown.fandom.com/wiki/Paragon_Level
- https://ffxileveldown.fandom.com/wiki/Progression_Guide

**Reading rules:** api.php works with curl and a browser user agent: action=query&meta=siteinfo, list=allpages, list=recentchanges, and action=parse&prop=wikitext. Statistics: 789 pages in total, but only 96 content articles, 103 pages in main namespace, 520 images, 2,668 edits, 1 active user. Last edit 2026-09-16. WebFetch through the API returned HTTP 402. robots.txt is behind a Cloudflare managed challenge, so I could not read it. Fandom's general terms apply. Wiki text is CC BY-SA, as is standard on Fandom (not verified on this wiki). Many pages link out to bg-wiki for base data.

**Quests:**
- Skipparoo Quest skips all nation and expansion missions: CoP, RoV, ToAU, RoZ, WoTG and SoA. Key items are still given, but mission trusts, armor, weapons and accessories are not. Steps: Skip in North San d'Oria L-9 wants a San d'Orian Carrot. Skipper in Port Bastok I-8 wants a Galkan Sausage. Skipy in Windurst Walls I-4 wants a Windurstian Tea Leaf. SkippySkipSkip in Bibiki Bay H-7 wants a Carbuncle Ruby. The 99 server has no requirement. The 75 server requires Rank 10.
- On 99, skipping before Rank 10 forfeits a free level 99 Relic weapon given at Rank 10 in any nation. Trusts lost to the skip must be earned in the NM Hunt Campaign.
- Custom systems: NM Hunt Campaign (tiers 1–6, with separate reward pages for 75), Daily NM Hunt, The Daily Grind, Beach Besieged, Paragon Level, Supreme Kings, High Tier Battle Fields 1 and 2, and holiday or GM events (WhackAMole, HideNseek, Naked Run, When Pigs Fly).
- HTBF NPCs (Mimble-Pimble, Raving Opossum, Trisvain) work as on retail, but the key-item requirements are removed.
- On 75, a Hangout Rewards Chest gives Rhapsody in White when you first reach level 75 and Rhapsody in Crimson when any craft reaches 100. These are the key items for the 4th and 5th trust. The skip quest also gives both.

**Missions:**
- All missions can be skipped through the Skipparoo Quest (99: no requirement; 75: Rank 10 first).
- 99 characters start with all limit breaks bypassed and maximum fame in every nation.
- The SoA, WotG and other expansion missions are skippable. Abyssea has no timer. Dynamis, Escha Zi'Tah and Limbus are open.

**Crafting:**
- All crafts can be taken to 110 on both servers.
- 'Crafting skill up increased to 99.9%' on both servers. Crafting EXP rates are 'Increased' on 75.
- Crafting armor, rings and weapons are given automatically when a craft skills up.
- Custom recipe Kupo Shield: Light Crystal + Genbu's Shield + East Wind + Arctic Wind + Antarctic Wind + Zephyr. Requires 100 in all 8 crafts. Also available from Reja after reaching 110 in 4 crafts.
- Custom recipe Iridal Staff: Woodworking 80 + all 8 NQ elemental staves (one page says Wind Crystal, another says Earth Crystal).
- Custom recipe Chatoyant Staff: Woodworking 100 + Wind Crystal + all 8 HQ elemental staves.
- LD 75 Crafting Guide (about 21 KB) has skill-up recipe guides for all 8 crafts and notes that guild crafting kits can be used up to about level 50.

**Combat skills:**
- All magic and combat skills are capped on level-up, on both servers.
- Subjobs level with the main job (99: up to 50; 75: up to 37) while the subjob is below the main job and within 5 levels of it.
- AoE weapon skills: Tornado Kick, Shark Bite, Ground Strike, Calamity, Steel Cyclone, Spiral Hell, Blade: Ku, Tachi: Kaiten, True Strike, Mystic Boon, Full Swing, Empyreal Arrow, Detonator and Drakesbane. Any job can use them with the right weapon skill from main or subjob.
- Ninjutsu: Ni spells are AoE. /NIN gets Universal Tools.
- 99 characters start with all spells and weapon skills unlocked. On 75 these are retail or unlocked by the Rank Reward System.
- Paragon: after level 99 and a mastered job, 5 releveling challenges per job (110 levels across 22 jobs). Each gives +5 to one stat (STR through CHR, ATT, RATT, ACC, RACC, MATT or MACC) on that job. Each of the first 4 challenges removes a quarter of the !buff bonus. Changing a stat costs 5,000,000 gil.

**Gear:**
- Free Artifact armor at levels 52, 54, 56, 58 and 60 on both servers. !jobshop reopens the AF shop.
- 99: one free set of Reforged level 109 AF for the first job you take to 99 (from Reja Ygridhi in the Hangout). One free level 99 Relic weapon at Rank 10.
- Rezyn in Port Jeuno has a custom upgrade path: NQ AF to Reforged 109 AF, NQ Relic to Reforged 109 Relic, +2 Empyrean to Reforged 109 Empyrean. GEO follows the BLM path and RUN follows the PLD path.
- Monisette in Port Jeuno upgrades reforged armor with no wait time and no Limbus requirement, and stores Rem's Tale chapters.
- Nolan in Norg gives only maximum Escha augments (no random augments) and upgrades Eschalixirs from NQ to +2. Augments with a 'Pet:' line don't work. The wiki says he takes 3,000 Escha Silt and 6 Eschalixir +2.
- Custom Mythic path from Tyo at Aht Urhgan Whitegate E-8: a Vigil weapon plus ZNM materials plus stored Alexandrite (100, 150, 200, 250, 300, 350 and 400 per step) takes it through Base, 75, 80, 85, 90, 95 and 99. Vigil weapons for RUN and GEO come from login points or T4 ZNM.
- Relic and Mythic upgrade materials drop from Unity Wanted NM coffers.
- Sky and Sea NMs and gods are rescaled to level 90–130. They drop Rem's Tale chapters, upgrade materials and listed items (for example, Mother Globe drops Enhancing Sword, Mindmeld Kris and Waterfall Ring).
- Item Adjustments: Nexus Cape reuse is 5 minutes and it warps to the party leader. The Balrahn's, Ulthalam's and Jalzahn's Ring latents are permanent. Unity gear's rank latents are permanent.
- Paragon tier rewards: Crepuscular Earring at 10, one Resurgence ring at 25, and the trusts Ygnas at 50, Matsui-P at 100 and August at 110.
- 119 starter weapons and armor are sold for bayld by Craggy Bluff and Vesca in Eastern Adoulin.
- Custom trusts: Lion II, Ferreous Coffin and Valaineral.

**Other:**
- Base EXP is retail on both servers, but !buff gives +500% EXP plus bonuses from level 1 to 98, and +200% capacity points at 99.
- GoV and FoV repeat-page bonus: +4% per repeat up to 200%, also applied to FoV.
- Movement on 75: run speed +25% and mount speed +50%. !retailspeed sets speed back to retail.
- Travel commands on 99: !home, !homereturn, !dem, !mea, !holla, !vahzl, !yhoator, !hangout, !addallportals. On 75: !travel, !xpcamp N, !meritcamp. EXP and merit book NPCs teleport to camps (N. San d'Oria L-9, Bastok Mines I-9, Port Windurst B-5, Ru'Lude Gardens I-10).
- Starting package: 100,000 gil, Destrier Beret, Chocobo Shirt, three nation rings, all maps, global linkshell. Starting inventory is 30 on 75. 99 characters also start with all subjobs, spells, weapon skills, home points and survival guide warps unlocked.
- Sparks limit increased. Mounts work in Abyssea. Trusts can be summoned in Limbus. NPC Alfred changes race and face. Custom wyvern skin (Draconius).
- !shop (food, tools, ammo, meds). The auction house is stocked by a bot. !ah is disabled.
- Accounts: 2 active characters plus 1 non-playable mule.
- Phase 2 work in progress: Legion, Ambuscade, World Boss, Supreme Kings, Abyssea VNM and Provenance.

**Best source:** Fetch all 103 main-namespace pages from the Fandom MediaWiki API with action=query&list=allpages&aplimit=500, then action=parse&prop=wikitext&formatversion=2 for each page, using a browser User-Agent and a polite delay (the WebFetch path got HTTP 402). Keep the two servers apart by page names: pages starting 'LD 75' or ending '75' belong to 75, the rest to 99. Treat these wiki pages as overrides on stock LandSandBoat and bg-wiki data. The wiki itself says to use bg-wiki unless something is custom. No source code is available to diff.

**Unknown:**
- The exact meaning of 'Crafting skill up increased to 99.9%'. It may be the skill-up chance, not a rate multiplier.
- Drop-rate multipliers. Not stated.
- Whether all 8 crafts or only some can reach 110 at once (the wiki says 'All Crafts can be taken to 110').
- robots.txt contents, which were blocked by a Cloudflare challenge.
- Whether the wiki is current. It has 1 active editor, and several pages are marked 'UNDER CONSTRUCTION'.
- Any private server repository. None was found on GitHub or GitLab, and I did not search GitLab directly.
- Which content pages describe the 75 server and which the 99 server, where the title doesn't say.

**Evidence:**
- https://ffxileveldown.fandom.com/api.php?action=query&meta=siteinfo&siprop=statistics|general — MediaWiki 1.43.9, 789 pages, 96 articles, 1 active user.
- https://ffxileveldown.fandom.com/api.php?action=query&list=allpages&aplimit=500 — 103 main-namespace pages, for example Custom Quests, Mythic Weapons, LD 75 Crafting Guide and Paragon Level.
- https://ffxileveldown.fandom.com/api.php?action=query&list=recentchanges — last edit 2026-09-16 (NM Hunt Campaign).
- https://ffxileveldown.fandom.com/wiki/About_Us — '99/99 Custom Server, Expansions – All Enabled, Exp Rates – Retail ... Crafting – Enabled all to 110', 'Crafting skill up increased to 99.9%', free AF at 52 to 60, Reforged 109 AF, free Relic at Rank 10.
- https://ffxileveldown.fandom.com/wiki/Level_Down_75 — '75/37 Custom Server', expansions up to WotG, retail job EXP, increased crafting EXP, run speed +25%, mount speed +50%, 30 inventory.
- https://ffxileveldown.fandom.com/wiki/Getting_Started — !buff gives +500% EXP, the command list, subjob leveling, the AoE weapon skill table.
- https://ffxileveldown.fandom.com/wiki/Custom_Quests — Skipparoo Quest NPCs and items, and the missions it skips.
- https://ffxileveldown.fandom.com/wiki/Custom_NPCS_Adjustments — the custom upgrade paths for Rezyn, Monisette and Nolan.
- https://ffxileveldown.fandom.com/wiki/Mythic_Weapons — Tyo's Alexandrite costs per step, 100 to 400.
- https://ffxileveldown.fandom.com/wiki/Custom_Crafting_Recipes — recipes for Kupo Shield, Iridal Staff and Chatoyant Staff.
- https://ffxileveldown.fandom.com/wiki/Sky_/_Sea_Adjustments — NMs rescaled to levels 90 to 130, with an extra reward table.
- https://ffxileveldown.fandom.com/wiki/Installation — server addresses LevelDownFFXI.com (99) and ffxileveldown75.ddns.net (75).
- GitHub code search for 'LevelDownFFXI' — only CalvinCandie-tech/XI-Launcher, a third-party launcher whose default host is leveldownffxi.com.

### Scythe

**Wiki:**
- https://scythe-bbq.pages.dev/server-info.html
- https://scythe-bbq.pages.dev/other-features.html
- https://scythe-bbq.pages.dev/guides.html
- https://scythe-bbq.pages.dev/database.html
- https://scythe-bbq.pages.dev/missions.html
- https://scythe-bbq.pages.dev/relic-weapons.html
- https://scythe-bbq.pages.dev/nm-hunt.html

**Reading rules:** About 25 HTML content pages. There is no MediaWiki, no api.php and no robots.txt: /robots.txt and /sitemap.xml return the HTML home page with status 200. The database page loads static JSON from data/<name>.json (seen in js/database.js). Files and sizes: items.json 469KB, equipment.json 1.6MB, mobs.json 2.4MB, spells.json 96KB, weaponskills.json 16KB, mobskills.json 151KB, nm_hunts.json 30KB (499 entries), shops.json 18KB, drops.json 5.9MB (47,774 rows with mob, zone, item, itemId, gRate, iRate), recipes.json 1.0MB (4,703 rows with result, ingredients, crystal and skill), zones.json 22KB. There is also a site search index at /search-index.json (50KB). No terms of use restricting automated reading were seen.

**Quests:**
- All 22 jobs are unlocked at creation. Advanced jobs are available from level 1, with no flag quest and no 'The Holy Crest' quest.
- Limit-break quests start at level 50 (the initial cap is 50).
- Trusts are quest-based, and seasonal Trust NPCs are permanently active.
- Fay Weapon Augments quest: trade one of 20 eligible weapons to Callisto, fight a Pixie NM, and return. Random augments, 5 rerolls, across 14 Shadowreign zones.
- Monstrosity is experimental and starts through the Suspicious Hume quest and Odyssean Passage.
- Dynamis Divergence entry requires final RoV completion plus a trade to Aurix for an Empty Hourglass.
- The Gobbie Mystery Box requires a 7-day minimum character age.
- Login campaign: 500 points for the first login each Earth day, 100 for later logins. Trust Ciphers cost 100 points each.
- 'Quest fixes' are listed as direct Scythe implementations, but no specific quests are named.

**Missions:**
- Mission skip NPC (Lily, in the hub) skips completed expansion mission lines to reach endgame.
- CoP mission level caps are disabled, and mission battlefield caps are disabled.
- SoA missions need no fame or imprimatur.
- WotG missions are not gated behind the Campaign nation quests.
- Mog Wardrobe storage unlocks automatically as expansion missions are completed.
- Mission support covers released lines through RoV.

**Crafting:**
- Common skill cap is 3200, so all 8 crafts can reach 110 on one character with no specialization restriction. Specialization points are 400 (retail).
- Craft skill-ups are guaranteed up to recipe level. The page says 'dramatically accelerated' but gives no multiplier. HQ chance is 1x.
- !craftreward milestones at skill 10, 30, 50, 60, 70, 80, 90 and 110 (trainee weapon, belt, journeyman piece, ring, torque, apron, 'Way of the...' key item, smock).
- !craftshield manages Escutcheon progression.
- Chocobo Circuit hub: 9 guild material vendors always open with no rank requirement. Advanced Support NPC gives a 15-minute Imagery buff for all 9 crafts. Crystal vendor and crystal storage moogle.
- Synergy Engineers and Furnaces in 17 zones.
- Gathering (HELM): 50% success (retail about 15%), 33% tool break. Chocobo digging: 85% in favorable weather, 100/day fatigue cap.

**Combat skills:**
- Combat and magic skill-ups: 5x chance and 5x gain per tick.
- WS damage formula is Adoulin (modern). Immunobreak enabled. Stoneskin cap 350, Blink 2 shadows (retail). Blood Pact timers are independent.
- Mazurka generates enmity.
- Every job has Widescan.

**Gear:**
- Relic (REMA) rebalance: 14 relics, relic weapon skills at fTP 5.0, 9.0 and 13.0, multi-hit fTP replication, OCC 35% at 3x (Mandau 40%).
- !af, !relic and !empy sell the base armor sets for your current main job.
- !rema sells a base REMA weapon (Relic 75, Mythic 75, Empyrean 80, or Ergon for GEO/RUN) for 5,000,000 gil. Requires nation rank 10 and 10 gate-HNM kills.
- Ruspix Empyrean +2/+3 upgrades come through Sortie.
- Relic upgrade waits: 2h (2nd stage), 1h (3rd stage).
- Drop rates are 1x retail. Treasure casket drop 10%. Abyssea lights drop 80%.
- Abyssea popped NMs use ??? item trades instead of key-item pop chains, and some have level 125 variants.
- Campaign Union coffers give item level 119 gear. Magian Trials have streamlined kill counts.
- Scyld milestones: 50 kills for a Golden Bomb mount, 100 for a Kupon I-Skill, 200 for a Kupon I-Seal (Abdhaljs), 400 for a Kupon I-RME (300 REMA materials), 500 for a Kupon W-RMEA.

**Other:**
- EXP: 4x from mob kills and quests. FoV/GoV/RoE EXP, Capacity Points, gil, Sparks and Bayld are 1x. !buff gives Regen, Refresh, Regain and 200% EXP for levels 1-98, and 200% CP at level 99. No EXP loss on death.
- Movement: 125 base, 175 cap. Homepoints heal. All outpost warps (including Tu'Lia and Tavnazia), all maps, Explorer Moogle at level 10. Travel commands: !holla/!dem/!mea/!altep/!vahzl/!yhoat/!jugner/!meriph/!pashow and !home/!ah/!cc/!headto.
- Dynamis: 24h re-entry, level 65 minimum, CoP required, 100:1 currency exchange, Prismatic Hourglass 50,000 gil.
- Custom systems: NM Hunt (475 NMs across 145 zones, level 80, Scyld currency), Elite Hunts (25 bosses at level 99, unlocked at 475/475), Siege (5-wave raid), FATE (88 events in 44 zones), Sortie (60 minutes, 8 sectors, 17 NMs), Dynamis Divergence (4 zones), Master Levels, Empress's Repair Decree.
- Fishing is enabled, with no changes listed. Dual-boxing is allowed for 2 accounts. Merit cap is 30.
- ScytheSkills Ashita addon names 320 custom regional-boss skills.

**Best source:** Pull the static JSON directly with plain HTTP GETs: https://scythe-bbq.pages.dev/data/{items,equipment,mobs,spells,weaponskills,mobskills,nm_hunts,shops,drops,recipes,zones}.json. These carry server-side drop rates (gRate/iRate), recipes and NM hunt lists. Overlay the hand-written rules from server-info.html and other-features.html as a per-server 'rules' layer (rates, !commands, mission skip, crafting cap). No source code is public, so diff the drops and recipes against stock LSB SQL to find the custom changes.

**Unknown:**
- Whether the server source code or SQL is public anywhere. No GitHub repo was found.
- Exact craft skill-up multiplier, and whether any recipes were added or removed (could be found by diffing recipes.json against LSB).
- AF armor changes, and which quests the 'direct Scythe implementations' cover.
- The Discord invite URL (it sits behind community.html and was not opened).

**Evidence:**
- https://scythe-bbq.pages.dev - RoV ML50, 4x EXP, 5x skill-ups, 475 hunt NMs, 14 REMA relic mods, credits LandSandBoat; no wiki or repo link
- https://scythe-bbq.pages.dev/server-info.html - full settings table: 3200 craft common cap, 50% HELM, relic fTP 5-13, Dynamis 24h/65/100:1, unreleased systems list
- https://scythe-bbq.pages.dev/other-features.html - !craftreward tiers, !rema 5M gil + rank 10 + 10 HNM, mission skip (Lily), SoA without fame/imprimatur, travel commands
- https://scythe-bbq.pages.dev/guides.html - Scyld milestones, Fay augment flow (Callisto), ScytheSkills addon
- https://scythe-bbq.pages.dev/js/database.js - fetch(`data/${name}.json`)
- https://scythe-bbq.pages.dev/data/drops.json - 47,774 rows, e.g. {mob:'Aa Xalmo the Savage', item:'deae gratia', gRate:1000, iRate:150}
- https://scythe-bbq.pages.dev/data/recipes.json - 4,703 recipes
- https://scythe-bbq.pages.dev/robots.txt - returns the HTML index (no robots file)
- gh api search/repositories 'scythe ffxi' and 'scythe landsandboat' - no results

### Olympus XI

**Wiki:**
- https://github.com/bobertdrake/olympus-xi-patch/releases/tag/wiki
- https://olympus-games.dev/news
- https://olympus-games.dev/fishing
- https://olympus-games.dev/ballista

**Reading rules:** Website: 13 URLs in sitemap.xml. robots.txt allows / but disallows /api/ and /download. The 'wiki' GitHub release has wiki-20261022.2209.zip (1.9MB, 292 Lua files, 10.1MB unpacked) plus wiki.json (version, sha256 and filename manifest). Header: 'generated by olympus-xi/tools/gen-wiki.py from the Olympus server'. manifest.json counts: 7,344 monsters, 7,330 items, 3,310 recipes, 203 zones, 6,213 NPCs, 455 quests, 170 missions, 136 guides, 20 lore. Quest and mission records carry impl='full' (373) or impl='npc' (82), which gives a per-server implementation status. Items carry shop, guild shop, made-by and drop data. Recipes carry craft levels, ingredients and HQ tiers. Paths in the zip use backslashes. No terms restricting reading were seen. The rules page covers only conduct.

**Quests:**
- Character modes chosen at creation: Normal; Titan Mode (faster leveling, but death resets the job to level 1); Hardcore (one life, self-found, trading only with other Hardcore players, deaths listed in the Hall of the Fallen).
- Chenon's fishing certification (Selbina Fishing Tournament prerequisite), which includes a Sabiki step needing two Quus in one cast (patch-7).
- Lore NPCs and NMs Vaudun The Unspoken (Pashhow Marshlands), Nanaa Fuego and Astraea, each with custom models and TP moves (patches 1, 4 and 10). Vaudun drops 'the Unspoken' dagger and the title Unspoken.
- Wiki pack: 455 quests, of which 373 are impl=full and 82 impl=npc (NPC present but not fully scripted).

**Missions:**
- Wiki pack has 170 missions with walkthroughs for the nation, Zilart and CoP missions. No custom mission changes are stated.

**Crafting:**
- Not stated on the site. The wiki pack's 3,310 recipes come from the server DB and can be diffed against LSB to find changes.
- Launcher addon /ocraft (recipes, material sources, AH history, 12x synth, leveling guide) and an Artisan's Satchel (launcher 0.7.18).

**Combat skills:**
- Not stated anywhere seen.

**Gear:**
- 64 new NMs across 16 leveling zones, each guarding role-specific gear found nowhere else (home page). Their drops are in the wiki pack (launcher 0.7.18).
- Custom items: the Unspoken dagger (equippable in the off hand with Dual Wield, patch-5), Fuego Charm (item 10945), The Drowned Lantern trophy.
- Ballista PvP points can be exchanged for leveling gear, spells and titles.
- Patch-16 restored ToAU-era monsters to their old spawns in 20 dungeons (e.g. Canal Pugil in Toraimarai Canal, Stirge in Ranguemont Pass, Soldier Crawler in Crawlers' Nest), which changes drops and levels compared with modern LSB.
- The site says wiki drop rates come from this server, not retail. No multiplier is published.

**Other:**
- Weekly Selbina Fishing Tournament, Saturdays at 9 AM Pacific, NPC Chenon (Fishermen's Guild), one hour long, points-based Master ranking.
- Ballista queued PvP. Beastiary monster cards (Discord minigame). Party Finder /oparty. Friends /ofriend.
- The Olympus Map shows only the Home Points this server has (patch-12), so the HP network differs from retail.
- Discord: https://discord.gg/apYsQ4b4GN. Bot players were retired before launch (launcher 0.7.8).

**Best source:** Ingest the GitHub release asset: read wiki.json (version and sha256) from https://github.com/bobertdrake/olympus-xi-patch/releases/download/wiki/wiki.json, download the matching wiki-<ver>.zip, and parse the Lua tables (items/*.lua, quests/*.lua, missions/*.lua, recipes.lua, index/mobs.lua, zones, guides.lua). Use a Lua-table parser and normalize the backslash paths. Re-check on each new 'wiki' release (the launcher refreshes it on every Play). Use impl='full' or 'npc' to flag quests that are not fully scripted. Supplement with the patch-N release notes for custom content.

**Unknown:**
- EXP, skill-up, crafting and drop-rate multipliers: none are published on the site.
- Whether the 'olympus-xi' server repo named in the pack header is public. It was not found by GitHub search and is probably private.
- Whether custom recipes or quests exist beyond what diffing the pack would show.
- The level and stats of the custom NMs and their gear (data is in the items/mobs Lua, not reviewed in depth).

**Evidence:**
- https://olympus-games.dev - 75 era through ToAU, Normal/Titan/Hardcore modes, 64 new NMs in 16 zones, /owiki, Discord link, powered by LandSandBoat
- https://olympus-games.dev/robots.txt - Allow /, Disallow /api/ and /download
- https://olympus-games.dev/sitemap.xml - 13 URLs
- https://olympus-games.dev/wiki - 404
- https://olympus-games.dev/join and /rules - no rates published
- https://olympus-games.dev/fishing - Saturday 9 AM PT tournament, Chenon certification, results from 2026-10-07
- https://github.com/bobertdrake/olympus-xi-patch/releases/tag/wiki - 'Olympus Wiki data ... from the Olympus XI server's own files', wiki-20261022.2209.zip 1,900,716 bytes
- wiki zip manifest.json - counts 7344 monsters / 7330 items / 3310 recipes / 455 quests / 170 missions; quests show impl full=373, npc=82
- GitHub release notes patch-1 to patch-17 and launcher-0.3.0 to 0.7.18 (gh api releases) - custom NMs, items, era-restored spawns, HD maps showing only this server's Home Points

### Legendary (Relaunch)

**Wiki:**
- https://ffxi-legendary.com/changes/
- https://ffxi-legendary.com/changelog/
- https://ffxi-legendary.com/reference/gear-vs-retail/
- https://ffxi-legendary.com/reference/ws-vs-retail/
- https://ffxi-legendary.com/progression/reforge/
- https://ffxi-legendary.com/progression/item-database/
- https://ffxi-legendary.com/progression/gear-finder/

**Reading rules:** MkDocs full-text index at https://ffxi-legendary.com/search/search_index.json (1.1MB, 1,125 sections across 136 pages). sitemap.xml lists 136 URLs. Structured data: /assets/gear-data.json (3.6MB, 'pulled straight from the live server') and /assets/item-search-data.json (1.4MB, 12,227 items with sources, generated 2026-10-03). robots.txt holds only Cloudflare content-signal comment text with no actual Content-Signal or Disallow directives, so nothing is restricted in practice. The changelog is about 78KB of dated deploy notes.

**Quests:**
- Subjob and advanced-job unlock quests are bypassed (both unlocked at level 0).
- Wish Upon a Star (Bastok, weather-gated) is patched with a workaround.
- SoA Imprimatur key items and fame requirements are removed.
- Zilart completion unlocks Mog Wardrobe 3. The opening cutscene is skipped and zone-in cutscenes are suppressed (side effects still apply).
- Dynamis: no CoP prerequisite, level 1 minimum, 0h cooldown, Prismatic Hourglass given at creation.
- Custom quest lines: Weapon Forger (Relic/Mythic/Empyrean via !forgegates), Prime Trials, Weapon Pilgrimage, Kraken Club +1 obtain path (changelog 2026-09-21).

**Missions:**
- No mission skip mentioned. SoA mission gating is loosened (no imprimatur or fame). COP Dynamis has no CoP prerequisite.

**Crafting:**
- Craft skill-up rate 10x. Craft HQ chance 2x.
- Synergy crafting active. Crafted Gear economy page exists (economy/crafted-gear/).
- The changes page does not state skill caps, guild changes or recipe changes.

**Combat skills:**
- Combat and magic skill-up rate 1x (unchanged).
- Stoneskin cap 10,000 (retail 350). Blink 10 shadows (retail 2). Spikes 1800s (retail 180). Elemental debuffs 1200s (retail 120). Aquaveil 10 hits (retail 1).
- WS vs Retail page: weapon skill damage caps and WS availability differ intentionally.
- Trusts and Fellows: 2x HP/MP, 1.5x base stats, 15% AoE damage taken. Custom Trusts Corvus, Meat, Gemma, Cornelia and Matsui-P. Cross-job abilities and traits pages exist.

**Gear:**
- Reforge System: custom NM pools drop base AF, Relic and Empyrean armor plus marks, upgraded base to +1, +2 and +3 at the Reforge Vendor. +4 is a separate path.
- Retail HNMs Behemoth, King Behemoth, Adamantoise, Aspidochelone, Roc and Simurgh no longer spawn at retail locations. They exist only as Affinity NM copies.
- Legendary Ring (custom: EXP/CP boost, Auto-Reraise, EXP protection). Augment Moogle with 143 options. Weapon Journey through Ambuscade, REMA, Aeonic and Prime.
- Gear vs Retail page tracks item stats that differ from FFXIAH: lower values, different values, and server-only buffs.
- Drop rate 1x. Multiple EXP rings with no weekly limit, and up to 10 Divine Might earrings.
- Starting kit: 300,000 gil, 80-slot inventory and satchel, 8 Mog Wardrobes at 80 slots each.

**Other:**
- EXP, Capacity Points, Sparks and TABs are 3x. Gil, bayld and fame are 1x. No EXP loss on death. The subjob banks 25% of EXP.
- Fishing is disabled server-wide.
- Movement: 150 base, 250 cap, mount 200. All maps and outpost warps granted. Homepoints restore HP/MP. @unstuck (24h). !warp menu and !hub (Purgonorgo Isle hub). Escha ZiTah hosts the Hunting League hub and vendors.
- Currency caps raised: Sparks and Accolades 999,999, Valor 500,000, Ballista 20,000. Weekly spending cap disabled. Dynamis currency 10:1.
- Custom systems: Hunting League, Ascension prestige, Job Rebirth, Spell Mastery, Endless Tower, Gauntlet, Star-Devourer, Voidwatch in 30 zones, Casino, Chocobo Derby, achievements (37).
- Discord: https://discord.gg/BWaSwqn5Fq

**Best source:** Fetch https://ffxi-legendary.com/search/search_index.json (all 136 pages as text and HTML sections, one request) for guide prose and the rules layer, especially /changes/ for rate multipliers. Then fetch /assets/gear-data.json and /assets/item-search-data.json for live-server item stats and sources. Check the changelog weekly. No server source is available, because the linked GitHub repo is private or 404.

**Unknown:**
- Whether the Relaunch source will become public (it is linked but currently 404).
- Crafting skill caps, guild changes and custom recipes are not stated.
- Exact WS damage cap values (the ws-vs-retail page text in the index is short; the tables may be rendered from data).
- Whether expansions after SoA (RoV, TVR missions) are enabled. The site says 'through Seekers of Adoulin' but lists later endgame content such as Ambuscade, Omen and Sortie-tier weapons.

**Evidence:**
- https://ffxi-legendary.com - rates 3x EXP/CP/Sparks, level 99 at creation, Reforge, custom trusts, GitHub link to richardknutzjr/Relaunch, Discord link
- https://ffxi-legendary.com/changes/ - full retail-difference table: craft 10x / HQ 2x, combat skill-up 1x, Stoneskin 10,000, Blink 10, fishing disabled, retail HNMs removed, Dynamis 0h/10:1
- https://ffxi-legendary.com/search/search_index.json - 1,117,840 bytes, 1,125 docs, 136 pages
- https://ffxi-legendary.com/sitemap.xml - 136 <loc> entries
- https://ffxi-legendary.com/robots.txt - only content-signal comments, no directives
- https://ffxi-legendary.com/assets/gear-finder.js - dataUrl() resolves to gear-data.json; /assets/gear-data.json returns 200, 3,635,076 bytes
- https://ffxi-legendary.com/assets/item-search-data.json - generated_at 2026-10-03, items with source tags
- https://github.com/richardknutzjr/Relaunch - HTTP 404; git ls-remote 'Repository not found'
- https://ffxi-legendary.com/progression/reforge/ - AF/Relic/Empyrean base to +3 via NM marks

### Vanadreams

**Wiki:**
- https://vanadreams.org/wiki/
- https://vanadreams.org/wiki/sitemap.xml
- https://vanadreams.org/wiki/data/meta.json
- https://vanadreams.org/wiki/data/quests.json
- https://vanadreams.org/wiki/data/walk-quests.json
- https://vanadreams.org/wiki/data/missions.json
- https://vanadreams.org/wiki/data/recipes.json
- https://vanadreams.org/wiki/data/jobs.json

**Reading rules:** No api.php; better: the raw JSON the wiki itself loads. Sitemap lists 35,856 URLs (23,536 item, 3,232 key item, 963 quest, 856 spell, 514 mission, 310 battlefield, 298 zone, plus NM/TP-move pages). meta.json: items 23,536, zones 298, mobs 12,240, NMs 4,159, recipes 4,668, quests 963, missions 514, battlefields 310, spells 856. Data files seen: meta, index (1.37 MB), quests (101 KB), missions, recipes (551 KB), jobs (297 KB), plus referenced walk-quests, walk-missions, keyitems, battlefields, synergy, tpmoves, maps, zonelist, itemkeys, itemguides, jobguides, contrib, sharded item/zone files (shards 0-14,31; zshards 0-9). walk-quests.json has per-quest summary, requirements, numbered steps and notes. robots.txt: 'User-agent: * Allow: /' with an explicit welcome to agents and crawlers. Guide page says 'Data reflects the Vanadreams server as of 11 Oct 2026'.

**Quests:**
- Three character modes (Default, Classic, Moogle Mode), chosen permanently; Moogle Mode can skip any storyline (3 nations, Zilart, ToAU, CoP, WotG, Adoulin, TVR, Abyssea, RoV) at Mog the Merciful with every reward, mission warps for 50,000 gil, no day waits
- Ten limit-break quests replaced by one at level 70
- Classic mode: Records of Eminence off (starter trusts Gessho, Ayame, Cherukiki, Shantotto, Ulmia + Trust Permit instead); Classic Master reward is the Classic Aketon
- Stonewalled, Balamor's Ruse and Watery Grave are real fights; repeat clears pay bayld
- Elite Training chapters and the 15 Awoken Peculiar Foes of Records of Eminence are real fights
- Login Moogle sells RoE trusts for 250 points; ~100 Adoulin and WotG side quests added 16 Oct 2026
- Mog Garden quest line, Clan Centurio (2,289 marks across 150 zones), 3,813 Magian trials with capstone augment from Oseem and Gorpa-Masorpa
- Dynamis re-entry after one hour; ENM key items hourly

**Missions:**
- Chains of Promathia zones have no level caps; only mission boss fights capped, 5 above original: Ancient Flames Beckon 35, Ancient Vows 45, Desires of Emptiness and The Savage 55
- Wings of the Goddess can be finished; Rhapsodies runs to its end (Sempurne, Metus, Cloud of Darkness)
- Moogle Mode storyline skips pay every mission reward and open home points, Survival Guides, maws, waypoints, crystals, confluxes, Eschan portals and nation outposts

**Crafting:**
- Crafting skill-ups twice as likely (Default mode)
- Crafting HQ chance 5x
- 'Enough specialisation to cap every craft' (all crafts can reach max)
- Fishing skill 2x faster
- Synergy: ponzes of cinder = 1 + 1 per 5 fewell fed (helpers half); 60% chance of synergy skill-up for all present when recipe is no more than 10 levels below skill; rank-ups from the Synergy Enthusiast cost 10 cinders x target rank, up to Expert
- Wiki recipe data: 4,668 recipes including synergy ('ds' field on 589)

**Combat skills:**
- Combat and magic skill-ups 2x in Default and Classic, 4x in Moogle Mode
- Support job level = main job level (Default, Moogle); half (Classic)
- Ability recasts 15% shorter
- Regular monsters +15% HP and +20% stats; NMs and bosses +10% of both
- Moogle Mode: weapon skills and spells 2.5x, cures and items 5x while alone or among Moogles; spells learned at their level

**Gear:**
- Drops at standard rate (1x) since 22 Oct 2026 (was different earlier)
- Beastmen and gil-dropping NMs drop 2x gil + 5 per monster level; other monsters 5 gil per level
- Caskets drop about 1 kill in 2; brown caskets give +1 gear for monster level and opener's job, 1 in 3 augmented
- Every gear and weapon upgrade costs half (items, NM kills, gil, points); endgame currencies (beads, silt, gallimaufry, hallmarks, accolades) pay double
- Every NM can drop endgame upgrade materials (one sure, second most of the time, from 23 Oct 2026)
- Oseem in Norg: Pellucid/Fern/Taupe stones set a chosen augment at cap; Dark Matter rolls take-or-leave; reforged AF/relic/empyrean up a grade to +4 (+3 empyrean), missing mats payable in gil
- Artifact and empyrean set bonuses, pet gear, song/roll gear, True Shot all functional
- All 14 Aeonic weapons give Aftermath
- Mog Bonanza: pearl 200,000 gil; top prizes include 170+ gear pieces nothing else gives
- Login Campaign: monthly 500-pt bonus, no cap, Dark Matter in 1,000-pt tier; Omen/Vagary/Delve/Geas Fete/Aeonic gear not on kupon list
- Gorpa-Masorpa sells for hallmarks/gallantry and sets a cape slot to full with one material

**Other:**
- EXP 1x from kills, RoE, FoV/GoV (Default); Classic half; Moogle Mode server rate +4
- Capacity points 10x (Moogle 10x plus half)
- FoV tabs 20x
- No EXP loss below level 31
- Sparks/Unity accolades cap 1,000,000, no weekly limit
- Hold all three experience rings at once; up to 969 merit points stored
- New characters: 10,000 gil, every map, every outpost warp, Explorer Moogle
- Faster movement on foot and mounted; Sneak/Invisible last 10x longer
- NM lottery pops always spawn, no cooldown; every NM incl. HNMs respawns within 30 s; 8,338 zone spawns added in October
- Auction house bot-stocked, nothing under 80 gil, bot buys player listings
- Extra BST pet spawns in Giddeus, Tahrongi Canyon, Bibiki Bay, Labyrinth of Onzozo, Phomiuna Aqueducts
- Mog Garden by Mog Dinghy from the three port towns with Pioneer's Badge or nation rank 3
- Rates have changed several times in Oct 2026 (16 Oct: EXP 1.33x; 22 Oct: back to 1x) so the guide must date-stamp server rates
- Unrestricted addons and multiboxing allowed

**Best source:** Ingest the wiki's own JSON directly: GET https://vanadreams.org/wiki/data/{meta,index,quests,walk-quests,missions,walk-missions,recipes,synergy,jobs,keyitems,battlefields,...}.json plus item/zone shards. It is generated from their server repo, so it reflects their custom content and their quest walkthrough steps. Re-pull on a schedule (check meta.json and the 'Data reflects ... as of' date). Server rates/modes come from the 'systems' and 'guide' tables embedded in https://vanadreams.org/wiki/app.js; parse those or hand-maintain them. robots.txt explicitly welcomes crawlers.

**Unknown:**
- The server LSB fork is not public; the wiki says its data is generated from 'the server repo', which is private
- Whether walk-quests text was written by hand or generated, and how accurate it is for custom changes
- Exact numeric movement speed ('faster on foot and mounted')
- Whether all 35,856 wiki pages are up to date after the 22-23 Oct 2026 rate changes (guide page says 11 Oct 2026)
- Crafting specialisation numbers (only 'enough to cap every craft')

**Evidence:**
- https://vanadreams.org/robots.txt — 'Hey there, agents and crawlers. You're welcome here', Allow: /, Sitemap https://vanadreams.org/wiki/sitemap.xml
- https://vanadreams.org/wiki/sitemap.xml — 35,856 URLs, all under /wiki/p/ (item 23,536, ki 3,232, quest 963, spell 856, mission 514, bf 310, zone 298)
- https://vanadreams.org/wiki/data/meta.json — items 23536, zones 298, mobs 12240, nms 4159, recipes 4668, quests 963, missions 514, battlefields 310, spells 856
- https://vanadreams.org/wiki/app.js — header comment 'a static reader over data/*.json generated from the server repo'; fetch('data/' + p + '.json'); embedded Server guide and 'Rates and modes' table (Default/Classic/Moogle) and changelog 28 Sep-24 Oct 2026
- https://vanadreams.org/wiki/p/guide — 'Data reflects the Vanadreams server as of 11 Oct 2026'
- https://vanadreams.org/wiki/data/walk-quests.json — per-quest s/req/st/nt walkthrough fields
- https://vanadreams.org/wiki/notes.js — player notes shared through /api/public/wiki with Discord sign-in
- https://github.com/VanaDreams — 3 repos (vanadreams-launcher, vanatunes, grampsshop), no server repo
- https://fairywitch.ca — WebFetch returned only the title 'Vanadreams — A private Final Fantasy XI world.' (JS-rendered)

### DriftwoodXI

**Reading rules:** No wiki and no api.php. Static-looking site pages fetched fine. robots.txt: 'User-agent: *', Disallow /reset and /delete only. Known JSON endpoints (from earlier launcher research in this repo's docs/DRIFTWOOD.md): /api/players, /api/manifest (client file list); no item/quest data API was seen.

**Quests:**
- Limit-break quests removed; Maat's testimony fights 'left with the level caps'
- Start with WAR/MNK/WHM/BLM/RDM/THF; other job unlock quests accept at level 1 (no level 30 gate); subjob unlocks at level 1
- Job unlocks purchasable: 100 Drift Coins completes that job's unlock quest (log entry, fame, title, emote)
- Quest gil 3x on first clear only; repeat turn-ins pay retail
- Fame 3x
- Drift Board (/quests): 10 daily and 9 weekly custom contracts plus a server-wide contract, paying Drift Coins; no NPC
- Self-Destruct and Final Sting retired from every enemy; Blue Magic spells bought instead (50 and 100 coins)
- Retail road to Mythic weapons 'is not in'; ArmsDealer sells Mythics at 1,000 coins
- Pop items bought with Dynamis hundred-pieces and Job Testimonies

**Missions:**
- Skip to end of RoZ and CoP for 1,000 Drift Coins (writes finisher mission state only; no key items, rank, or quest rewards); then Sky, Sea and the item-level ladder open
- Zilart and Promathia waypoints in DWPort 250 coins each after both stories are done
- Site lists ToAU 48 missions and WotG 54 missions; individual mission changes not described
- Expansions open one at a time after play-verification

**Crafting:**
- Every craft levels freely to 70; triple retail's specialisation allowance lets any three crafts reach 110
- Craft skill-up chance 3x, skill-up amounts 2x retail
- HQ chance 2x retail
- Gathering tools (harvesting, excavation, logging, mining) 0% break; 75% success on harvesting, excavation, logging, mining and digging
- 100 chocobo digs per day (was 200, cut to 50, raised to 100); Burrow and Bore granted
- Fishing enabled, 5x skill-up; /fishing plans a route 0-110; Lu Shang's Fishing Rod sold on a shelf
- DWCraft addon shows recipes, costs, and a levelling ladder; /craft shows the crafter's ledger

**Combat skills:**
- Every swing rolls for combat skill-up, hit or miss, and every roll under cap lands
- Weapon skill and skillchain points 10x (incl. Magian trials)
- Sub job level = main job level
- Job ability recasts 15% shorter; elemental magic recasts 3x retail
- Healing tick delay 1 s, no TP reduction while healing
- Ordinary high-level enemies have less padding; NMs keep theirs; aggro and link radius halved
- Magic skill-up change not stated

**Gear:**
- Item level ceiling raised to 119 (from 104 -> 109 -> 114 -> 119); armor families to 109 through the forge; reforged iL109 piece climbs to +1 at 119
- Empyrean weapons sold on ArmsDealer shelf at iL99; Oboro (Port Jeuno) sells weapons toward 119; Antonia (Upper Jeuno) sells Arasy iL119 weapons for 3,000,000 gil
- Outfitter: lv50-60 AF sets 25 coins/piece, Dynamis relic armor 125, lv74 AF+1 100, Empyrean +2 sets 200, lv27-33 race gear 25; quests and Dynamis still award every piece
- Jeweler: Wyrmking earrings 100, Sea earrings 200, Rajas/Sattva/Tamas rings 300
- Drops doubled; a Rare drop your main already owns goes to your next character
- Caskets rarer than retail; 3 in 4 locked and carry randomly augmented gear
- Spoils: EXP-giving monsters can drop gear with 1-4 random augments; NMs 10x likelier; 1 in 20 is Super Auged
- Custom augments: Weapon Burst (10 variants), X-Magic on rings (6 kinds), Runes; Drift Exchange sells Weapon Burst/X-Magic augments for 5,000 Burst Tokens + 750 Drift Coins
- Nemesis: 50 trophies buy an iL119 +1 with four Super Auged augments

**Other:**
- EXP, gil, bayld, capacity points, tabs 3x; FoV/GoV 1.5x and enabled everywhere
- Death penalty half of retail, from level 31; party level-gap penalty removed
- Merits granted at 75, job points at 99; max merits held 99; Weapon Skill merits combined 15 -> 70; JA groups 10 -> 20; HP/MP/7 attributes 30 upgrades each; lowering a merit refunds; Ascension banks limit points for Mastery tiers
- Multiple EXP rings usable, recharge restrictions removed
- Movement 1.5x on foot and mounted; road to Tu'Lia open
- All maps, outpost warps and home point crystals unlocked; 80 inventory slots; start with 5,000 gil
- Spells unlocked account-wide; DWSquad: summon up to 5 of your 16 characters as party members
- Custom content: The Gauntlet (50 floors, up to 18 seats, full clear 1,275 Burst Tokens), The Raid (18 boss trials, 13 venues, 5 tiers), Nemesis (240 NMs at +100 levels), Unleashed (Legend NM every 2 hours on even hour Eastern), Politics (6 elected seats on 4-week seasons setting DWPort fares)
- Dynamis one-hour shared lockout; Garrison restarts every 10 minutes
- 1,000-slot shared warehouse (2,000 with gil); market no listing fee, buy orders escrow
- One account per player; 158-addon allowlist

**Best source:** No wiki and no public server code with the custom systems. Scrape the official site pages (robots allows all but /reset and /delete): /custom (full change list), /features/<dw*> (18 pages), /news/<slug> (~40 posts, e.g. rates-and-progression, crafting-gathering-and-fishing, the-outfitter, relics-at-the-armsdealer). Store as a hand-curated 'server overlay' of rates, unlock rules, shop prices and removed/added content applied on top of a stock LSB/retail baseline for quests, items and recipes. Optionally read addon Lua in DriftwoodGaming/DriftwoodXI-Content packages for shop/menu data.

**Unknown:**
- Merit page conflict: /custom says WS merits 15->70 and attributes 30 each, rates page says 'max merits held raised to 99' — both may be true (cap held vs cap spent)
- Magic skill-up rate not stated
- Whether the live server code is a private fork (likely) and whether any retail quests are removed beyond LB/Mythic/Maat
- Individual quest/mission behavior differences inside ToAU/WotG/SoA
- Exact drop multiplier for Treasure Hunter interaction (news post drops-gil-and-treasure-hunter not read)

**Evidence:**
- https://xi.driftwoodgaming.com — level 99 without interruption, LB quests removed, expansions Base..SoA open, 3x rates, 1.5x FoV/GoV, 10x WS points, 1.5x movement, 80 slots, 5,000 gil, open beta 9 Aug 2026, 33 addons
- https://xi.driftwoodgaming.com/custom — crafting 70 / three to 110, HQ 2x, tools never break, iL ceiling 119, drops doubled, merit caps, Gauntlet/Raid/Nemesis/Unleashed/Politics, aggro radius halved, JA recast -15%, elemental recast 3x
- https://xi.driftwoodgaming.com/news/crafting-gathering-and-fishing — 27 Jul 2026 by Zatara: skill-up chance 3x, amounts 2x, HQ 2x, 75% gather success, 100 digs/day, fishing 5x
- https://xi.driftwoodgaming.com/news/rates-and-progression — 27 Jul 2026: 3x rates, subjob at 1 and equal level, merits at 75, Maat gives Limit Breaker and Job Breaker, max merits 99, half death penalty from 31
- https://xi.driftwoodgaming.com/features/dwquest — Drift Board, 1,000-coin RoZ/CoP skip, 100-coin job unlocks, Outfitter/Jeweler/ArmsDealer prices, Self-Destruct/Final Sting retired
- https://xi.driftwoodgaming.com/robots.txt — Disallow /reset, /delete only
- https://api.github.com/repos/DriftwoodGaming/server — fork of LandSandBoat/server; default branch base last commit 2023-03-10; branches are upstream-fix branches dated 2026-07-24..28
- https://github.com/DriftwoodGaming/DriftwoodXI-Content — top-level: ashita.json, bundles, content.json, packages, texturepacks.json; pushed 2026-10-28

### PegasusXI

**Wiki:**
- https://pegasusxi.com/wiki/Main_Page
- https://pegasusxi.com/w/api.php

**Reading rules:** api.php works without login: siteinfo statistics pages 137,407, articles 46,867, edits 142,078, images 71,667, users 7, active users 1, admins 1. Last recent changes 2026-08-30 by PegasusAdmin (CSS/gadget edits, file uploads). Full-text search for 'PegasusXI' returns 298 hits, mostly renamed BG-Wiki meta pages ('PegasusXI Wiki Staff', 'PegasusXI Wiki Suggestions', 'BG Wiki Staff'). Pages are edit-protected. robots.txt contains only 'User-agent: *' with no Disallow. License CC BY-NC-SA 3.0 (non-commercial, share-alike, attribution) applies to reuse. Main page states content past CoP is 'still in development', so articles may describe retail behavior not live.

**Quests:**
- Retail-like; no custom quest changes stated on site or wiki
- Repo modules/custom/lua/quest_workarounds.lua: temporary fix making Bastok 'Wish Upon a Star' completable by accepting SUNSHINE weather (LSB PR 5831)
- Repo custom modules present (whether enabled live unknown): wotg_decouple_story_missions_from_nation_quests.lua, soa_remove_imprimatur_gate.lua, mission_wardrobe_unlocks.lua, replace_trust_with_cornelia.lua
- modules/init.txt in repo loads only custom/commands/, custom/lua/test_npcs_in_gm_home.lua, custom/lua/new_player_linkshell.lua
- Subjob quest level 18 (retail)

**Missions:**
- Content after CoP still in development (site + wiki main page)
- Repo has wotg_decouple_story_missions_from_nation_quests.lua and soa_remove_imprimatur_gate.lua modules but init.txt does not list them

**Crafting:**
- Crafting rate 1.0 'retail-like' (server-info page)
- Repo map.lua: CRAFT_CHANCE_MULTIPLIER 1.0, CRAFT_AMOUNT_MULTIPLIER 1, CRAFT_MODERN_SYSTEM true, CRAFT_COMMON_CAP 700, CRAFT_SPECIALIZATION_POINTS 400, CRAFT_HQ_CHANCE_MULTIPLIER 1.0 (all retail)
- Repo main.lua: HARVESTING/EXCAVATION/LOGGING/MINING_RATE 50%
- Fishing, gardening, chocobo digging enabled

**Combat skills:**
- Repo map.lua: SKILLUP_CHANCE_MULTIPLIER 1.0, SKILLUP_AMOUNT_MULTIPLIER 1 (retail)
- Combat 'faithful to retail, with a few QoL enhancements' (site)
- Repo main.lua: retail-modern stat multipliers (2H STR->Attack 1.0, 1H main 0.75, DEX->Acc 0.75), DELAY_REDUCTION_CAP 0.80

**Gear:**
- No custom gear stated on site
- Repo main.lua: CASKET_DROP_RATE 0.1 (retail), ABYSSEA_LIGHTS_DROP_RATE 80
- Client pack ships XIPivot DAT overlays incl. 'PegasusXI-Enhancements' (contents not checked)
- Wiki has recent uploads of +4 gear images (e.g. 'Cab. Gauntlets +4'), i.e. BG-Wiki-era content

**Other:**
- EXP 1.0 'retail-like' (server-info); repo map.lua EXP_RATE 1.0, EXP_LOSS_LEVEL 31, CAPACITY_RATE 1.0, FAME_MULTIPLIER 1.00
- Repo main.lua: GIL/BAYLD/EXP/BOOK_EXP/TABS/ROE_EXP/SPARKS_RATE all 1.000
- Movement speed retail (BASE_SPEED 50, MOUNT_SPEED 80 in repo)
- Trusts enabled; all 22 jobs; level sync enabled
- Player-driven AH with custom stocked-AH support; repo modules/custom/cpp ah_announcement.cpp, ah_pagination.cpp
- Original Dynamis present; Dynamis Divergence in development
- ENABLE_COP_ZONE_CAP 0 in repo (CoP zone level caps off) — live value unknown
- Site tools: items.html, bazaars.html, bcnm.html (BCNM ranking), dynamis-tracker.html, players.html
- No bots/automation; single box per operator's repo rules.html; 88-addon approved list

**Best source:** Treat PegasusXI as near-stock LandSandBoat: build its guide from the aremais/PegasusXI repo (scripts/quests, scripts/missions, sql/*.sql for items, drops, recipes; settings/default for rates), gated by the site's 'playable through CoP' statement. Use the PegasusXI MediaWiki api.php (action=query/parse, 46,867 articles) only as secondary, since it is a BG-Wiki copy (CC BY-NC-SA 3.0) and not server-specific. Re-check repo push date; the repo may lag the live server and the live settings override files are not public.

**Unknown:**
- Whether live server uses settings/default values or a private override (settings/*.lua not committed)
- Conflict: repo enables expansions through TVR while site says playable only through CoP; how post-CoP content is gated live
- Which custom modules are actually enabled live (init.txt lists only two)
- Contents of the 'PegasusXI-Enhancements' DAT overlay
- Whether the wiki has any Pegasus-specific edits beyond rebranding (only 1 active user)
- Whether 'faster travel options, inventory management, smart party tools' QoL items exist and what they are

**Evidence:**
- https://pegasusxi.com — level cap 99, 'Playable through Chains of Promathia', retail-like, wiki link pegasusxi.com/wiki, news through Jun 02 2026
- https://pegasusxi.com/server-info.html — Experience rate 1.0, Crafting rate 1.0 (retail-like), movement retail, trusts on, 22 jobs, fishing/gardening/chocobo digging on, Dynamis Divergence in development
- https://pegasusxi.com/w/api.php?action=query&meta=siteinfo&siprop=general|statistics — MediaWiki 1.43.9; pages 137407, articles 46867, users 7, active 1; rightsinfo CC BY-NC-SA 3.0 'text adapted from BG-Wiki'
- https://pegasusxi.com/w/api.php?action=query&list=recentchanges — latest edits 2026-08-30 by PegasusAdmin
- https://pegasusxi.com/robots.txt — only 'User-agent: *'
- https://github.com/aremais/PegasusXI — fork=false, created 2026-03-17, pushed 2026-08-04; changelogs/lsb-to-base-2026-08-02.md documents LSB sync of 28 commits
- https://github.com/aremais/PegasusXI/blob/base/settings/default/main.lua — ENABLE_COP..TVR = 1, MAX_LEVEL 99, INITIAL_LEVEL_CAP 50, all rates 1.000, gathering 50%
- https://github.com/aremais/PegasusXI/blob/base/settings/default/map.lua — EXP_RATE 1.0, SKILLUP/CRAFT multipliers 1.0, CRAFT_COMMON_CAP 700, SPECIALIZATION 400
- https://github.com/aremais/PegasusXI/blob/base/modules/init.txt — loads custom/commands/, test_npcs_in_gm_home.lua, new_player_linkshell.lua

### HorizonXI

**Wiki:**
- https://horizonffxi.wiki/
- https://horizonffxi.wiki/Horizon_Changes
- https://horizonffxi.wiki/Category:Horizon_Changes
- https://horizonffxi.wiki/Category:Out_of_Era
- https://horizonffxi.wiki/DAT_Comparison
- https://horizonffxi.wiki/Guild

**Reading rules:** The sitemap index (https://horizonffxi.wiki/sitemap/sitemap-index-horizonffxi.wiki.xml) lists 16,026 NS_0 article URLs plus 731 NS_14 category URLs, 16,757 in total. robots.txt disallows /w/api.php, /w/index.php, /w/rest.php, all Special: pages, action/oldid/diff query strings and talk pages, and sets Crawl-delay 10. It blocks GPTBot, ClaudeBot, CCBot, AhrefsBot and SemrushBot outright. So the API exists but automated use is explicitly disallowed. horizonxi.com robots.txt has 'Content-Signal: search=yes,ai-train=no,use=reference' and blocks ClaudeBot, GPTBot, CCBot, Google-Extended and others. The news API returned the 30 most recent posts as JSON, with html, category and date fields.

**Quests:**
- Fill In awards Nanaa's Charm (Treasure Hunter +1)
- New/custom quests: Dyer's Woad, custom Omni Aketon quest
- Chocobo's Wounds needs only ~1 Vana'diel hour between trades
- Eco-Warrior quests (all 3 nations) award Dragon Chronicles worth 4,500-9,000 EXP
- BCNM loot pools changed (Protectra V, Shellra V, Enlight added); Under Observation drops gil-value items instead of scrolls; Waking the Beast is harder, has more weapon drops, and drops the Yinyang Robe
- Nation rings awarded on completing Nation Missions 1-3
- Patch 2026-10-23: BLU/COR/PUP artifact quest progress can be reset at Vingijard; patch 2026-10-09: free Mhaura->Selbina boat during 'His Name is Valgeir'

**Missions:**
- Signet gives an EXP bonus in CoP areas: 5% at 50-59, 7.5% at 60-69, 10% at 70-75; since 2026-09-25 Signet has no effect in ToAU zones
- Patch notes 2026-09-27 to 10-23 contain many ToAU/CoP battlefield fixes (e.g. 'Shadows of the Mind', 'Omens', 'Desires of Emptiness', 'Return to the Depths'), so mission behavior is still being changed

**Crafting:**
- Many ores stack; some NPC-sold recipe items (e.g. Darksteel Pick) cost less
- Chocobo digging: daily real-life limit, visible skill-up messages, adjusted loot pools
- Clamming loot pools reworked; Excavation/Logging/Mining/Harvesting pools in several zones raised in value
- Sickles break only if the wearer is not in the full Field Tunica set
- The wiki Guild page gives skill-up chances of 60% per successful synth below level 50 and 25% from 50-99.9, but notes these come from AirSkyBoat code and are unconfirmed because HorizonXI code is closed

**Combat skills:**
- Weapon skills unlock at skill 5 instead of 10 for every weapon type; many elemental WS are hybrid and stack with Sneak Attack
- Skillchain damage on non-NM mobs cannot be resisted; Magic Burst +35 magic accuracy / +35 magic attack except on NMs
- Job changes, e.g. MNK Boost +20% attack with 30s recast and Chakra 2min recast; WHM Reraise at 25, Haste 18s recast, Refresh 50 MP; BLM Poison 4/tick, elemental debuffs 120s; NIN Yonin at 20; DRK Last Resort 60s
- Healing MP starts at 12/tick and rises by 4/tick
- Patch 2023-06-09: guard skill-up opportunities aligned

**Gear:**
- Artifact weapons are level 40; Artifact Armor, Relic Weapons and Exp Rings each have changed subpages
- Speed Belt gives 5% haste; Hydra armor reworked; new Shepherd's armor set for pet jobs
- CoP reward rings changed except Rajas Ring; warp rings unusable; Laurel Crown is cosmetic
- NMs drop non-Rare/Ex gear where possible; Kirin drops Shellra V
- Coffer and chest key drop rates raised; all drop rates 'adjusted to better match the era' (no values given); Treasure Hunter follows SE's official chart

**Other:**
- EXP: Wings of the Goddess EXP tables; Level Sync with a penalty after 10 levels; experience scrolls give 3x
- Fishing requires level 15; fishing, gardening and chocobo digging are enabled
- Travel: outpost teleport NPCs moved to era positions; new Jeuno outpost NPCs Twinkstix/Burnstix/Sprinkstix; Warp Tarus Polo-Colo and Mumbo-Bumbo in Port Windurst; Mog House home points; movement speed is the 75-era default (20% slower)
- Custom systems: HENM tiers, HAAP/HARP programs, linked AH with a 21-item limit, 10% bazaar tax, Mog Satchel via Discord link, 2 linkshells, !unstuck/!uptime
- Dynamis is CoP-era with a 71h lockout; 3 HNM kings respawn every 22-23h with 10-minute windows; claim shield on prominent NMs
- EXP camps re-tuned on 2026-10-02 ('Era+ TP burn camps' and merit camps, e.g. Uleguerand Gigas, Wajaom Woodpecker, Aydeewa Deforester/Mycoskulker, Mount Zhayolm Eruca/Wamoura Prince, Arrapago Dweomershell/Nirgali)

**Best source:** No public source code exists, so the community wiki is the only full data source. Its Horizon_Changes page (about 120k characters) plus Category:Horizon_Changes and Category:Out_of_Era are the diff layer to put over a retail/LSB baseline. Its robots.txt bans api.php and named AI crawlers, so do not bulk-scrape. Ask the wiki editors (Discord / Editor Hub) for permission or a dump, or get Daniel's explicit go-ahead before running a polite, low-rate fetch of only the Horizon_Changes pages. For ongoing changes, poll the official JSON API https://api.horizonxi.com/api/v1/news, filter category=='patch-notes', and parse the html. The launcher already uses this API.

**Unknown:**
- Exact crafting skill-up multiplier and craft caps on HorizonXI (only ASB-derived, unconfirmed figures were seen)
- Exact drop-rate values (wiki says 'adjusted', no numbers)
- Whether ToAU content beyond missions (Assault, Salvage, Nyzul, Besieged) is open; not checked
- Whether the wiki editors would grant scraping permission

**Evidence:**
- https://horizonffxi.wiki/ - front page: 'level 75 cap Era+', current era ToAU, launched 2022-12-17 in CoP, rebased AirSkyBoat->LandSandBoat 2026-01-30, 'era+ code changes remain private', not maintained by staff
- https://horizonffxi.wiki/Horizon_Changes - full change list (WotG EXP, WS at skill 5, Nanaa's Charm from Fill In, warp rings disabled, 71h Dynamis, 21-item AH, etc.)
- https://horizonffxi.wiki/robots.txt - disallows /w/api.php and Special:, Crawl-delay 10, blocks ClaudeBot/GPTBot/CCBot
- https://horizonffxi.wiki/sitemap/sitemap-index-horizonffxi.wiki.xml - 16,026 article + 731 category URLs
- https://horizonffxi.wiki/Guild (via search snippet) - crafting skill-up figures from ASB code, noted as unconfirmed
- https://horizonxi.com/robots.txt - Content-Signal ai-train=no, ClaudeBot disallowed
- https://api.horizonxi.com/api/v1/news - 30 JSON posts; patch notes 2026-09-25 to 10-23 including the 2026-10-02 EXP camp adjustments
- GitHub org HorizonFFXI - only launcher binaries, prereqs, hxiloader and a MediaWiki DarkMode mirror; no server repo

### CatsEyeXI

**Wiki:**
- https://www.catseyexi.com/wiki
- https://www.bg-wiki.com/ffxi/Category:CatsEyeXI
- https://www.bg-wiki.com/ffxi/CatsEyeXI_Systems/Quests
- https://www.bg-wiki.com/ffxi/CatsEyeXI_Systems/Synthesis
- https://www.bg-wiki.com/ffxi/CatseyeXI_Crafting_Guide
- https://www.bg-wiki.com/ffxi/CatsEyeXI_Content/Missions
- https://www.bg-wiki.com/ffxi/CatsEyeXI_Content/Drops
- https://www.bg-wiki.com/ffxi/CatsEyeXI_Systems/Navigation
- https://www.bg-wiki.com/ffxi/CatsEyeXI_Systems/Jobs

**Reading rules:** The BG-Wiki API works: api.php list=allpages with apprefix=CatsEyeXI returned 122 pages, and action=parse&prop=wikitext returned full wikitext (e.g. Systems/Jobs 127 KB, Systems/Quests 108 KB, Systems/Synthesis 94 KB, Systems/Fishing 53 KB). BG-Wiki robots.txt only disallows diff/oldid/edit URLs, with Crawl-Delay 30 for * (150 for GPTBot/CCBot/PerplexityBot, which are not fully blocked). catseyexi.com robots.txt disallows /api/; item sitemaps list 20,461 /item/N pages, but they render 'Loading item information...' without JS. The terms have no scraping clause beyond 'unauthorized access' and addon-policy automation.

**Quests:**
- 100+ custom quests (home page); BG-Wiki CatsEyeXI_Systems/Quests has sections Content Quests, System Quests, per-city lists and Limit Breaks
- Custom travel-unlock quests: 'Up, Up and Away', 'Digging Up Dirt' (CW BCNM teleports via Domenic), 'Gobbie Travels' (Portalix teleports to Beadeaux/Davoi/Oztroja), 'Near Death Experience' and 'Blast to the Past' (EXP Book teleports)
- Mythic and Aeonic weapon skills are obtained through custom quests
- Loxley Quest System (LQS), Novice Trials, Grand Trials and Milestone Rewards systems each have their own pages

**Missions:**
- The 3-mage gate opens without the Portal Charm KI
- After ZM6 there is a sparkle in the Chamber of Oracles to return to the device chamber
- Assaults are not fully implemented, so Assault rank is tied to ToAU mission progress; promote via the Wildcat Captain (Whitegate K-10) by trading currency
- ACP, AMK and ASA missions are not implemented
- RoV is partly implemented to grant trusts (White/Crimson KIs); trust ciphers go only to ACE/CW accounts
- ENABLE_COP_ZONE_CAP 0 (no CoP zone level caps)

**Crafting:**
- map.lua: CRAFT_CHANCE_MULTIPLIER 1.5 and CRAFT_AMOUNT_MULTIPLIER 2 (upstream LSB 1.0/1)
- CRAFT_MODERN_SYSTEM true, CRAFT_COMMON_CAP 700, CRAFT_SPECIALIZATION_POINTS 400; BG-Wiki states main craft cap 110 and sub craft cap 70
- BG-Wiki Synthesis page lists custom recipes (furnishings, food, custom materials with HQ1-3, crafted movement-speed gear such as Areion Boots and Harbinger's Gaiters)
- Crafting Rewards: reaching 100 in any craft gives ACE players a one-time completed stage-5 Relic weapon
- Gathering: HARVESTING/EXCAVATION/LOGGING/MINING_RATE 50%, break chance 33%, DIGGING_RATE 85, DIG_FATIGUE 300, burrow/bore granted

**Combat skills:**
- map.lua: SKILLUP_CHANCE_MULTIPLIER 2.0 and SKILLUP_AMOUNT_MULTIPLIER 2 (upstream 1.0/1); SKILLUP_BLOODPACT true
- USE_OLD_CURE_FORMULA true, USE_OLD_MAGIC_DAMAGE true, DIVINE_POWER 1.125, AVATAR_DAMAGE_MOD 0.6, BLINK_SHADOWS 2, ELEMENTAL_DEBUFF_DURATION 120, SNEAK_INVIS_DURATION_MULTIPLIER 2
- USE_ADOULIN_WEAPON_SKILL_CHANGES false; MAX_MERIT_POINTS 50; per-job changes on BG-Wiki CatsEyeXI_Systems/Jobs (22 job sections; e.g. some pet level caps raised to 75)

**Gear:**
- Custom Equipment pages per slot (CatsEyeXI_Content/Equipment/*, about 35 pages)
- Relic: ACE players get a one-time stage-4 relic at Lv75 + Rank 10; relics can be swapped for 5,000,000 gil; Ragnarok adds RUN and Mjollnir adds GEO; Magian DMG+ augments also add Resist Death
- Separate pages for Empyrean, Mythic, Ergon and Oboro weapons, Artifact +1 Augments, Salvage Augments, Dynamis Augments and Adept Reforging
- Drops page: altered drops (e.g. an Alexandrite set at 100/50/25% plus Ctn. Purse 10%); custom HNM and Dynamis drops; DROP_RATE_MULTIPLIER 1.0 in public settings
- NUMBER_OF_DM_EARRINGS 5 (retail 1); CASKET_DROP_RATE 0.1

**Other:**
- EXP_RATE 1.5 in map.lua; the wiki says ACE gets x1.5 with no chain bonus, CW gets EXP plus chain bonus after Lv40 in parties, and WEW gets a chain bonus at 75; DISABLE_PARTY_EXP_PENALTY true; Ventures EXP camp list on BG-Wiki CatsEyeXI_Content/EXP
- Fishing: FISHING_SKILL_MULTIPLIER 3.0; Crooked Jones (Norg H-8) fishing ventures pay 'doubloons'; AUTO_FISHING_CONTEST true
- Travel: ALL_MAPS 1, UNLOCK_OUTPOST_WARPS 1, HOMEPOINT_TELEPORT 1 (ACE only, per wiki), EXPLORER_MOOGLE_LV 10, Whitegate warp for 300 gil from Ajithaam after Lure of the Wildcat, mini tuning-fork warps for 100 gil, outpost warps also unlocked by Garrison
- START_GIL 5000, START_INVENTORY 80, TABS_RATE 3.0, SPARKS_RATE 1.5, ENM_COOLDOWN 71, Garrison not once-per-week, rank 1
- Custom systems: Domain Invasion, Dragonslaying, Summit of the Stars, Prestige, Claim Shield, Mog Vault, Mog Bonanza, Aether Caskets, Ephemeral Box, PartyFinder

**Best source:** Three layers. (1) Pull the public LSB fork CatsAndBoats/catseyexi (branch 'stable') and diff settings/default/main.lua and map.lua against upstream LSB to get machine-readable rates and expansion toggles. The custom quest/item code sits in the private 'modules' and 'cexi-src' submodules and cannot be pulled. (2) Pull the about 122 CatsEyeXI pages from BG-Wiki with api.php (list=allpages&apprefix=CatsEyeXI, then action=parse&prop=wikitext), at no more than 1 request per 30s per robots Crawl-Delay, and parse the templates ({{Custom Equipment}}, {{Item Tooltip}}). (3) Skip catseyexi.com /api/ because robots.txt disallows it; ask the CatsEyeXI staff for an item/mob export if per-item data is needed.

**Unknown:**
- Live server may override settings/default with gitignored settings/*.lua (the repo comments say the test server does this), so the public defaults may not equal live values
- Contents of the private modules repo (custom quests, recipes and items as code)
- Whether ACE, CW and WEW use different rate settings in code (the wiki says EXP differs per mode)
- modules/custom/lua and modules/era in the fork look like upstream LSB example modules; init.txt does not load them, so their presence says nothing about CatsEyeXI behavior

**Evidence:**
- https://www.catseyexi.com/ - level 75, three modes ACE/CW/WEW, 100+ custom quests, Ventures, Summit of the Stars, Domain Invasion, Dragonslaying
- https://www.catseyexi.com/wiki - index page sending readers to BG-Wiki Category:CatsEyeXI
- https://www.bg-wiki.com/api.php?action=query&list=allpages&apprefix=CatsEyeXI - 122 pages returned
- https://github.com/CatsAndBoats/catseyexi - fork of LandSandBoat/server; stable pushed 2026-10-15; .gitmodules points modules/catseyexi -> catsandboats/modules and src/map/cexi -> catsandboats/cexi-src, both 404 (private)
- settings/default/map.lua@stable - EXP_RATE 1.5, SKILLUP_CHANCE_MULTIPLIER 2.0, CRAFT_CHANCE_MULTIPLIER 1.5, SKILLUP/CRAFT_AMOUNT 2, FISHING_SKILL_MULTIPLIER 3.0, CRAFT_COMMON_CAP 700, SPECIALIZATION 400, MAX_MERIT_POINTS 50 (diffed against upstream LSB map.lua)
- settings/default/main.lua@stable - MAX_LEVEL 75, ENABLE_ABYSSEA/SOA/TVR 0, ENABLE_ROV 1, ALL_MAPS 1, USE_OLD_CURE_FORMULA true, NUMBER_OF_DM_EARRINGS 5, TABS_RATE 3
- https://www.bg-wiki.com/ffxi/CatsEyeXI_Content/Missions - Portal Charm not needed, Assault rank tied to ToAU missions, ACP/AMK/ASA not implemented, RoV partial
- https://www.bg-wiki.com/ffxi/CatsEyeXI_Systems/Relic_Weapon - stage-4 relic milestone, 5M gil exchange, RUN on Ragnarok, GEO on Mjollnir
- https://www.bg-wiki.com/ffxi/CatsEyeXI_Systems/Navigation - custom teleport quests and NPCs
- https://www.bg-wiki.com/ffxi/CatsEyeXI_Content/EXP - ACE x1.5, no chain bonus; Ventures camp list
- https://www.bg-wiki.com/ffxi/CatsEyeXI_Systems/Fishing - Crooked Jones, doubloons
- https://catseyexi.com/robots.txt - Disallow /api/; item sitemaps 0-2 have 10,000 + 10,000 + 461 URLs
- https://catseyexi.com/terms - no explicit scraping clause

### AscensionXI

**Wiki:**
- https://www.ascensionffxi.com/wiki
- https://www.ascensionffxi.com/wiki/Custom_Changes
- https://www.ascensionffxi.com/wiki/Crafting
- https://www.ascensionffxi.com/wiki/Quests
- https://www.ascensionffxi.com/wiki/Custom_Quests
- https://www.ascensionffxi.com/wiki/Custom_Items
- https://www.ascensionffxi.com/wiki/changes

**Reading rules:** sitemap.xml lists 21,426 /wiki/ URLs (flat, e.g. /wiki/Ridill, /wiki/A_Boy's_Dream) plus 28 news and 22 feature pages. robots.txt: 'Content-Signal: search=yes,ai-train=no,use=reference', Allow / for *, but blocks ClaudeBot, anthropic-ai, Claude-Web, GPTBot, CCBot, Google-Extended and others. No JSON/API endpoint was seen in the pages fetched.

**Quests:**
- 568 quests listed on /wiki/Quests across 10 tabs, including an 'AscensionXI' tab of 30 custom quests (e.g. Branch Manager, Fist Impressions, Signed for in Person, Hides for the Household)
- Custom quests named on Custom_Changes: Finders Keepers, nation rings at level 10, Sanction without ToAU mission 2, Till Depth Do Us Part (Anchor Ring, level 15), This Time Together (2 trusts at 40), Warm Regards / Cold Comfort / Beyond the Outposts (warp destinations, 500 gil each)
- About 25 quests and missions use short waits instead of waiting for midnight; Cold Comfort reward is 20,000 gil
- Maat's In Defiant Challenge from level 46; Dancers fight Laila
- Mission level caps: rank 2 dragon at 25, Qu'Bia rank 5 at 50, Promathia fights at 30/40/50/60
- Trusts Curilla, Naji and Kupipi from level-10 quests; Ayame and Ulmia later; 1 trust, 2 from Lv40

**Missions:**
- CoP capped at mission 7-5; ZM capped at The Mithra and the Crystal
- Nation start in a city without the opening cutscene
- Open-world mission monsters do not protect Hardcore characters from level reset; battlefield, BCNM, KSNM and ENM fights do
- Aht Urhgan mission 2 not required for Sanction

**Crafting:**
- All eight crafts reach 110; Expert rank in every guild at skill 98; 'steady skill-ups below 60'
- Base HQ 2% plus 1% per level over, capped at 80%; HQ ingredient +10 points; HQ2 from +11 levels and HQ3 from +31; at +56 the split is 50/25/25%; HQ yields 2-4x (up to 12)
- Break ingredient loss 12.5% (retail 50%); desynthesis 95% success at or above recipe level
- Recipe counts: WW 525, Smith 652, Gold 762, Cloth 548, Leather 564, Bone 294, Alchemy 560, Cooking 420
- New materials: Sumi Stone, Quicksilver Stone, Semolina Wheat, Wasabi Root, Coal; Work Orders replace guild points; Synergy engineers removed; Artisan's Apron/Hat/Torque and Kupo Shield stages; Craftsman's Restraint blocks HQ
- Nexus addon for crafting from Void Storage; HELM replaces gathering points (32 zones, bands 0/20/40/60/80); chocobo digging allowance 50 plus half of skill per day, banked 7 days

**Combat skills:**
- Twelve weapon skills need 150 skill: A-rated jobs get them at 49, B-rated at 51
- Job reworks with numbers, e.g. WAR Retaliation at 10, Defense Bonus V (+60 DEF); BLM Scythe C+ (230 at 75), Subjugate at 75, Primal Font replaces Manafont, Ancient Magic 200 MP / 6s cast; THF TH10 start rising to TH14, Dagger A+ (276); RDM Spellchain at 55; DNC Presto and Feather Step at 75
- Two-hours recast 45 minutes; WS +20% enmity; spell interruption only after moving more than 1.5 yalms; spell queue; no ranged distance penalty to 25 yalms
- Cure = Healing skill + 1/2 MND + 1/4 VIT; post-cast delay 2.0s; nuke MP tiers 9/37/91/195

**Gear:**
- Artifact gear reworked for all jobs: weapons at 40, armor at 50
- Forsaken and Rekindled weapons; Reese Torr upgrades Rekindled to +1 at 20 and +2 at 30
- Bad-luck protection: each miss adds 20% of base chance on most NM drops; Archer's Ring and Elshimo Marble +1% per kill; Strike Baghnakhs, Valor Earring, Traveler's Mantle, Plantreaper and Viking Axe guaranteed after 95 misses
- Treasure caskets always give 8 tries; monster scroll drops at least 5%; old NM drops restored (Leaping Boots, Emperor Hairpin)
- Conquest gear costs double points at Major Markup; Amalasanda charges 10x for magic scrolls; Chocobo Torque at level 1; Blind Ring works
- Example: Ridill Lv70, DMG 40, delay 236, dropped by Fafnir at 1.0%

**Other:**
- EXP: Even Match = 100; kill caps 200/250/300 (<=50, <=60, >60); parties of 2-6 get 80% of solo; chain +4% per link up to chain 20; Level Sync at 15+; Anchor Ring banks EXP; Dragon Chronicles 2,500-3,000 EXP; training pages pay 100/75/50/25% for the first 4 per day; Ascension (6 times per job, at Celestine); Expedition bonus every 10th kill for levels 10-74
- Fishing has no rod fight and fish never deplete; fish must be within 10 levels of skill; Carp Creel 200 points, Sand Charm 15,000 points at Fennella
- Travel: Sergeant Sendoff sells outpost warps for gil or conquest points; Afdeen removed
- Group content: Onslaught (9 strongholds, caps 10/20/30); Echo hunts (111 NMs); Garrison rebuilt; Dynamis 4 cities (mobs 77, NMs 80, bosses 85)
- NM respawns: Roc/Simurgh about 21h, Cerberus/Khimaira about 36h, Tiamat/Jormungand 48-49h; weather rolled once per Vana'diel day
- Commands: !points, !void, !vault, !quests, !luck, !spellqueue, !settings

**Best source:** No public source code, so the first-party wiki at ascensionffxi.com/wiki is the source. It is server-data-backed (21,426 pages in sitemap.xml with item stats and drop rates). Ingest Custom_Changes as the rules/diff layer and the Quests/Crafting/item pages for data, using sitemap.xml for discovery. robots.txt blocks AI crawlers (ClaudeBot, GPTBot) and sets ai-train=no, so ask the AscensionXI staff (Discord https://discord.gg/e924EXBC6m) for permission or a data export before bulk ingest. Get Daniel's go-ahead before any automated pull. Watch /wiki/changes and /news/<date> for updates.

**Unknown:**
- Whether AscensionXI is LandSandBoat-based (assumed by the task; not stated on any page seen)
- Exact crafting skill-up rate numbers ('steady skill-ups below 60' only)
- Release schedule for further expansions and jobs
- Whether a JSON or API backend exists behind the wiki (none seen)
- How many of the 21,426 wiki pages have player-written text versus generated stubs

**Evidence:**
- https://www.ascensionffxi.com/ - 'Level 75 Ironman' server; feature list (Ascension, Hardcore, Expedition, Onslaught, Anchor Ring, Void Storage/Crafting, HELM, predictable weather); Discord link; no GitHub link
- https://www.ascensionffxi.com/wiki/Custom_Changes - full rules page (WotG era, job availability, EXP formulas, crafting to 110, bad-luck protection, NM respawns, travel, commands)
- https://www.ascensionffxi.com/wiki/Crafting - HQ math and per-craft recipe counts
- https://www.ascensionffxi.com/wiki/Quests - 568 quests, 30 in the AscensionXI tab
- https://www.ascensionffxi.com/wiki/Ridill - item page with a 'Dropped by' table (Fafnir 1.0%)
- https://www.ascensionffxi.com/sitemap.xml - 21,426 wiki URLs
- https://www.ascensionffxi.com/robots.txt - Content-Signal ai-train=no; ClaudeBot/anthropic-ai/GPTBot disallowed
- https://www.ascensionffxi.com/feature/progressive-server - 'opening FFXI piece by piece', no schedule given
- gh search repos/code for 'ascensionxi' and 'ascensionffxi' - no repositories found

