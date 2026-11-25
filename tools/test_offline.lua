-- Vanaguide :: tools/test_offline.lua
-- Runs the addon's logic against a fake world.  `luajit tools/test_offline.lua` from the
-- repository root; exits non-zero on the first failure.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

package.path = 'Vanaguide/?.lua;Vanaguide/?/init.lua;' .. package.path
dofile('tools/stubs.lua')

local pass, fail = 0, 0
local function ok(cond, what)
    if cond then pass = pass + 1 else fail = fail + 1; print('FAIL: ' .. what) end
end
local function eq(a, b, what)
    if a == b then pass = pass + 1
    else fail = fail + 1; print(('FAIL: %s (got %s, want %s)'):format(what, tostring(a), tostring(b))) end
end

local U      = require('core.util')
local zones  = require('data.zone_names')
local G      = require('core.guide')
local C      = require('core.conditions')
local P      = require('core.progress')
local story  = require('core.story')
local graph  = require('routing.zonegraph')
local R      = require('routing.router')

-- The quest-source generator test uses temporary input files and writes no game state.
local generator_test = os.execute('python3 tools/test_gen_quests.py')
if generator_test == true or generator_test == 0 then
    pass = pass + 1
else
    fail = fail + 1
    print('FAIL: quest source generator fixtures')
end

-- ---- zone data ----------------------------------------------------------------
eq(zones.name[230], "Southern San d'Oria", 'zone 230 name')
eq(zones.find("southern san d'oria"), 230, 'zone lookup by name')
eq(zones.find('Port_Jeuno'), 246, 'zone lookup with underscores')
eq(U.zone_name(246), 'Port Jeuno', 'zone name through util')

-- ---- parser -------------------------------------------------------------------
local steps, errs = G.parse([[
-- a comment
t Ask the gate guard|Z|230|POS|-140,120,8|N|By the fountain.|
A Mission 1-1|M|sandoria,2|Z|230|
K Kill orcs for tusks|IT|1122,3|Z|140|
R Run to the Jeuno gate|Z|246|POS|10,-20|
L Reach level 10|LV|10|
]])
eq(#errs, 0, 'guide parses cleanly')
eq(#steps, 5, 'five steps')
eq(steps[1].kind, 'talk', 'verb t -> talk')
eq(steps[1].pos.r, 8, 'explicit radius')
eq(steps[4].pos.r, 10, 'default radius')
eq(steps[2].mission.area, 'sandoria', 'mission tag')
local mission_accept_parse = G.parse_line('A Accept mission|MA|sandoria,0|')
eq(mission_accept_parse.mission_accept.id, 0, 'mission-accepted tag parses the current mission id')
ok(C.is_automatic(mission_accept_parse), 'mission acceptance is an automatic condition')
eq(steps[3].item.count, 3, 'item count')
ok(select(2, G.parse('q nonsense|Z|230|'))[1] ~= nil, 'bad verb reported')
ok(select(2, G.parse('A Accept quest|QA|sandoria,10|QAZ|sandoria,10|'))[1]
    :match('unknown tag'), 'unknown tag rejected instead of ignored')
ok(select(2, G.parse('C Complete objective|LV|7|LV|8|'))[1]
    :match('duplicate tag'), 'duplicate tag rejected')
ok(select(2, G.parse('C Collect item|IT|not-an-id|'))[1]
    :match('IT needs'), 'malformed item condition rejected')
ok(select(2, G.parse('L Reach level|LV|0|'))[1]
    :match('LV needs'), 'zero level condition rejected')

-- Who a step is about: its own NPC tag, else its database entry's NPC only in that entry's zone.
do
    local s = G.parse('T Trade the axe to Endracion|M|sandoria,0|Z|230|POS|-112.8,-37.2|NPC|Endracion|')[1]
    eq(s.npc, 'Endracion', 'NPC tag')
    eq(G.npc_of(s, { npc = 'Ambrotien', zone = 230 }), 'Endracion', 'the NPC tag beats the database')
    local away = G.parse('T Deliver the report to Naji|M|bastok,0|Z|237|')[1]
    eq(G.npc_of(away, { npc = 'Argus', zone = 236 }), nil,
       "a database NPC in another zone is not this step's NPC")
    local here = G.parse('C Mission|M|bastok,0|Z|236|N|Starts with Argus.|')[1]
    eq(G.npc_of(here, { npc = 'Argus', zone = 236 }), 'Argus', 'the database NPC in its own zone')
    eq(G.npc_of(G.parse('C Mission|M|cop,110|Z|126|N|First stop: Enter Lower Delkfutt.|')[1], nil),
       nil, 'a place is not an NPC')
    ok(select(2, G.parse('t Talk|Z|230|NPC||'))[1] ~= nil, 'an empty NPC tag is reported')
end

-- The RetroAchievements id a step stands for (guides/achievements.lua).  It is shown, never a
-- condition: a step with only RA is still a manual step.  tools/test_achievements.lua has the rest.
do
    local s = G.parse('C Squire No More|RA|900102||N|Complete the quest.|')[1]
    eq(s.ra, 900102, 'RA tag')
    ok(not require('core.conditions').is_automatic(s), 'RA alone is not a completion condition')
    ok(select(2, G.parse('C x|RA|none|'))[1] ~= nil, 'a non-numeric RA id is reported')
end

-- ---- conditions ---------------------------------------------------------------
WORLD.zone, WORLD.x, WORLD.z = 230, -140, 120
local w = C.world()
eq(C.distance(steps[1], w), 0, 'distance zero when standing on it')
ok(not C.done(steps[1], w), 'talk step is manual even when you are standing there')
WORLD.zone = 246; WORLD.x, WORLD.z = 12, -21
ok(C.done(steps[4], C.world()), 'run-to step completes on arrival')
WORLD.items[1122] = 2
ok(not C.done(steps[3], C.world()), '2 of 3 tusks is not done')
WORLD.items[1122] = 3
ok(C.done(steps[3], C.world()), '3 of 3 tusks is done')
WORLD.main_job_level = 10
ok(C.done(steps[5], C.world()), 'level step')
local zone_only_travel = G.parse_line('F Travel to Ordelles Caves|Z|193|')
ok(not C.done(zone_only_travel, { zone = 230 }), 'zone-only travel waits outside destination')
ok(C.done(zone_only_travel, { zone = 193 }), 'zone-only travel completes on zone arrival')
local fixed_checkpoint = G.parse_line('t Examine marker|Z|193|POS|10,20|FIXED||')
ok(fixed_checkpoint.fixed, 'FIXED checkpoint tag parses')
fixed_checkpoint.index = 1
P.set_guide(G.register({ name = 'Fixed checkpoint fixture', steps = { fixed_checkpoint } }))
WORLD.zone, WORLD.x, WORLD.z = 193, 10, 20
eq(P.advance(), 0, 'FIXED waypoint remains active on arrival')
P.check()
eq(P.advance(), 1, 'FIXED waypoint advances after manual Done')
P.set_guide(nil)

-- ---- story flags from packet 0x056 --------------------------------------------
local function packet_0056(page, ids)
    local bytes = {}
    for i = 1, 32 do bytes[i] = 0 end
    for _, id in ipairs(ids) do
        local b, bit = math.floor(id / 8) + 1, id % 8
        bytes[b] = bytes[b] + 2 ^ bit
    end
    local unpk = table.unpack or unpack
    local body = string.char(0, 0, 0, 0)                        -- 0x00..0x03 header
        .. string.char(unpk(bytes, 1, 32))                      -- 0x04..0x23
        .. string.char(page % 256, math.floor(page / 256) % 256, 0, 0)         -- 0x24 page id
        .. string.rep('\0', 8)
    return body
end
story.on_packet(0x056, packet_0056(0x0090, {}), 48)
story.on_packet(0x056, packet_0056(0x0050, { 5 }), 48)       -- current, San d'Oria
local accepted_step = G.parse_line("A Accept quest|QA|sandoria,5|")
ok(story.quest_active('sandoria', 5), 'accepted quest flag read from current page')
ok(not story.quest_done('sandoria', 5), 'accepted quest is not yet completed')
ok(C.done(accepted_step, { story = story }), 'QA condition completes on active quest flag')
story.on_packet(0x056, packet_0056(0x0050, {}), 48)
story.on_packet(0x056, packet_0056(0x0090, { 5, 12 }), 48)     -- completed, San d'Oria
ok(not story.quest_active('sandoria', 5), 'turn-in clears the active quest flag')
ok(story.quest_done('sandoria', 5), 'quest flag 5 read from packet')
ok(story.quest_done('sandoria', 12), 'quest flag 12 read from packet')
ok(C.done(accepted_step, { story = story }), 'QA condition stays complete after turn-in')
ok(not story.quest_done('sandoria', 6), 'unset flag stays unset')
ok(not story.quest_done('jeuno', 5), 'flags do not leak between areas')

-- current-mission packet: nation 0, nation mission 3
local mission = string.char(0, 0, 0, 0)
    .. string.char(0, 0, 0, 0)      -- 0x04 nation
    .. string.char(3, 0, 0, 0)      -- 0x08 current nation mission
    .. string.rep('\0', 0x24 - 0x0C)
    .. string.char(0xFF, 0xFF, 0, 0)
    .. string.rep('\0', 8)
story.on_packet(0x056, mission, #mission)
ok(story.mission_done('sandoria', 2), 'mission 2 done when current is 3')
ok(not story.mission_done('sandoria', 3), 'the current mission is not done')
local accepted_mission_packet = mission:sub(1, 8) .. string.char(0, 0, 0, 0) .. mission:sub(13)
story.on_packet(0x056, accepted_mission_packet, #accepted_mission_packet)
local accept_mission_step = G.parse_line('A Accept mission|MA|sandoria,0|')
ok(story.mission_active('sandoria', 0), 'current mission id identifies an accepted mission')
ok(not story.mission_done('sandoria', 0), 'an accepted mission is not yet completed')
ok(C.done(accept_mission_step, { story = story }), 'MA completes once the server marks the mission active')
story.on_packet(0x056, mission, #mission)
ok(story.mission_active('sandoria', 3), 'the current mission remains active')
ok(story.mission_active('sandoria', 0), 'a completed prior mission stays satisfied')

-- 65535 means "no mission active", not "past every mission". A fresh character reports it
-- for every storyline, and reading it as progress marked all 24 San d'Oria missions done.
local none = string.char(0, 0, 0, 0)
    .. string.char(0, 0, 0, 0)          -- nation 0
    .. string.char(0xFF, 0xFF, 0, 0)    -- current nation mission = 65535
    .. string.rep('\0', 0x24 - 0x0C)
    .. string.char(0xFF, 0xFF, 0, 0)
    .. string.rep('\0', 8)
story.on_packet(0x056, none, #none)
ok(not story.mission_done('sandoria', 0), 'no mission active does not complete mission 0')
ok(not story.mission_done('sandoria', 23), 'nor the last one')
eq(story.mission_current('sandoria'), nil, 'and the current mission reads as nothing')
story.on_packet(0x056, mission, #mission)   -- put the world back for the tests below

-- The nation storyline's completed bitset, page 0x00D0, identified in-game: completing a
-- mission clears the current number back to 65535, so this page is the only evidence left.
story.on_packet(0x056, packet_0056(0x00D0, { 0, 1 }), 48)
ok(story.mission_done('sandoria', 0), 'a completed nation mission is read from page 0x00D0')
ok(story.mission_done('sandoria', 1), 'and the second one')
ok(not story.mission_done('sandoria', 9), 'but not one that is still to do')

-- ---- every mission log, the way LandSandBoat packs it ----------------------------
-- Built from src/map/packets/s2c/0x056_mission.cpp / 0x056_mission_other.cpp, and the state
-- CLuaBaseEntity::completeMission / addMission leave behind (lua_base_entity.cpp).
do
    local unpk = table.unpack or unpack
    -- a 0x056 of `page` whose 32 data bytes are zero except `u32s` ({offset = value}, offsets
    -- from the start of the packet) and `bits` (flag ids across the 32 bytes)
    local function pkt(page, u32s, bits)
        local b = {}
        for i = 1, 32 do b[i] = 0 end
        for off, v in pairs(u32s or {}) do
            for k = 0, 3 do b[off - 4 + k + 1] = math.floor(v / 256 ^ k) % 256 end
        end
        for _, id in ipairs(bits or {}) do
            local i, bit = math.floor(id / 8) + 1, id % 8
            b[i] = b[i] + 2 ^ bit
        end
        return string.char(0, 0, 0, 0) .. string.char(unpk(b, 1, 32))
            .. string.char(page % 256, math.floor(page / 256) % 256, 0, 0) .. string.rep('\0', 8)
    end
    local function feed(p) story.on_packet(0x056, p, #p) end
    -- 0xFFFF with every storyline "none" (65535 for the nation, 0 for logs 3+, SoA/RoV at
    -- their un-started offsets), then overrides.
    local function main(t)
        local u = { [0x04] = t.nation or 0, [0x08] = t.nation_mission or 65535,
                    [0x0C] = t.zilart or 0, [0x10] = t.cop or 0,
                    [0x18] = (t.acp or 0) + (t.amk or 0) * 16 + (t.asa or 0) * 256,
                    [0x1C] = t.soa_raw or 0x6E, [0x20] = t.rov_raw or 0x6C }
        return pkt(0xFFFF, u)
    end
    story.reset()

    -- Chains of Promathia, guide 43 step 8 (Ancient Vows, 248).  CoP has no completed bit
    -- anywhere; the current number is the whole record, and LandSandBoat's own
    -- hasCompletedMission(COP, id) is `id < current`.
    require('guides.init')
    local cop = G.get('Chains of Promathia - in order')
    ok(cop ~= nil, 'the CoP storyline guide is registered')
    local vows
    for _, s in ipairs(cop.steps) do if s.mission and s.mission.id == 248 then vows = s end end
    ok(vows ~= nil and vows.mission.area == 'cop', 'it has Ancient Vows as M|cop,248|')
    local cw = { story = story }
    feed(main({ cop = 248 }))                                   -- !addmission COP 248
    ok(not C.done(vows, cw), 'CoP 248 is open while it is the current mission')
    eq(story.mission_current('cop'), 248, 'and reads as the current one')
    -- What the audit harness did: `!completemission COP 248`.  When 248 is current the server
    -- sets current to 0 (logs above 2) and stores no bit for CoP, so 0xFFFF says CoP = 0 --
    -- and the server itself no longer counts 248 as complete.  (When 248 is *not* current,
    -- which the harness's `!delmission` made sure of, it only logs "can't complete non
    -- current mission" and sends nothing.)  Open is the right answer.
    feed(main({ cop = 0 }))
    ok(not C.done(vows, cw), 'after a bare !completemission COP 248 the step stays open, as on the server')
    -- What the mission script does: completeMission then addMission(nextMission), so
    -- current becomes The Call of the Wyrmking (258).  That is what finishes a CoP mission.
    feed(main({ cop = 258 }))
    ok(C.done(vows, cw), 'CoP 248 is done once the current mission has moved on to 258')
    ok(not story.mission_done('cop', 258), 'and 258 itself is not')
    ok(story.mission_done('cop', 110), 'and every earlier CoP mission is')

    -- Nations + Zilart share page 0x00D0, 8 bytes each.  A Bastok character's completed
    -- mission 2 is bit 64+2 of the page; reading the page whole put it at id 66.
    feed(main({ nation = 1 }))
    feed(pkt(0x00D0, nil, { 64 + 2, 192 + 4 }))
    ok(story.mission_done('bastok', 2), 'Bastok mission 2 is read from the Bastok bytes of 0x00D0')
    ok(not story.mission_done('bastok', 66), 'not as Bastok mission 66')
    ok(not story.mission_done('sandoria', 2), "and it is not a San d'Oria mission")
    ok(story.mission_done('zilart', 4), 'Zilart completed bits are the last 8 bytes of 0x00D0')
    ok(not story.mission_done('zilart', 0), 'and Zilart current 0 marks nothing done')
    feed(pkt(0x00D0, nil, { 128 + 5 }))
    ok(story.mission_done('windurst', 5), 'Windurst completed bits are bytes 16..23')
    ok(not story.mission_done('bastok', 2), 'a fresh 0x00D0 replaces the previous one')

    -- ToAU / WoTG: current numbers ride on the Aht Urhgan quest page 0x0080 (Data[5], Data[6]),
    -- completed bits on 0x00D8.  0xFFFE is TVR's page and must not be read as ToAU.
    feed(pkt(0x0080, { [0x18] = 3, [0x1C] = 9 }, { 5, 100 }))
    feed(pkt(0xFFFE, { [0x04] = 0 }))
    eq(story.mission_current('toau'), 3, 'ToAU current comes from page 0x0080, and 0xFFFE leaves it alone')
    ok(story.mission_done('toau', 2), 'ToAU 2 is done while 3 is current')
    ok(story.mission_done('wotg', 8), 'WoTG 8 is done while 9 is current')
    ok(story.quest_active('ahturhgan', 5), 'Aht Urhgan quest 5 is in progress (page 0x0080)')
    ok(story.quest_active('ahturhgan', 100), 'and quest 100')
    -- ToAU current 3 in Data[5] is bits 160,161 if the page were read whole
    ok(not story.quest_active('ahturhgan', 160), 'the mission numbers are not quest flags')
    feed(pkt(0x0080, { [0x18] = 0, [0x1C] = 0 }))              -- !completemission TOAU 3
    feed(pkt(0x00D8, nil, { 3, 64 + 9 }))
    ok(story.mission_done('toau', 3), 'a completed ToAU mission is read from 0x00D8 bytes 0..7')
    ok(story.mission_done('wotg', 9), 'a completed WoTG mission from bytes 8..15')
    ok(not story.mission_done('toau', 4), 'but not the next one')
    feed(pkt(0x00C0, nil, { 12, 128 + 1 }))
    ok(story.quest_done('ahturhgan', 12), 'Aht Urhgan completed quests are read from 0x00C0')
    ok(not story.quest_done('ahturhgan', 129), 'bytes 16..31 of 0x00C0 are Assault, not quests')

    -- ACP / AMK / ASA nibbles: the guide area is 'amk'.
    feed(main({ acp = 5, amk = 7, asa = 2 }))
    ok(story.mission_done('acp', 4) and not story.mission_done('acp', 5), 'ACP from the low nibble of 0x18')
    ok(story.mission_done('amk', 6) and not story.mission_done('amk', 7), "AMK from the high nibble, as area 'amk'")
    ok(story.mission_done('asa', 1) and not story.mission_done('asa', 2), 'ASA from the low nibble of 0x19')

    -- Seekers of Adoulin (current*2 + 0x6E) and RoV (current + 0x6C).  Read raw, a character
    -- who had not started either had Adoulin missions 0..109 and all of RoV "done".
    feed(main({}))
    ok(not story.mission_done('adoulin', 0), 'an un-started Adoulin storyline has nothing done')
    ok(not story.mission_done('rov', 0), 'nor RoV')
    feed(main({ soa_raw = 0x6E + 9 * 2, rov_raw = 0x6C + 12 }))
    eq(story.mission_current('adoulin'), 9, 'Adoulin current is (raw - 0x6E) / 2')
    ok(story.mission_done('adoulin', 8) and not story.mission_done('adoulin', 100), 'and completes only what is past it')
    eq(story.mission_current('rov'), 12, 'RoV current is raw - 0x6C')
    ok(story.mission_done('rov', 10) and not story.mission_done('rov', 12), 'and completes only what is past it')
    feed(main({ soa_raw = 0, rov_raw = 0 }))
    eq(story.mission_current('adoulin'), nil, 'a declined expansion (0) is nothing started')

    -- put the San d'Oria world back for the progress tests below
    story.reset()
    story.on_packet(0x056, packet_0056(0x0090, { 5, 12 }), 48)
    story.on_packet(0x056, mission, #mission)
    story.on_packet(0x056, packet_0056(0x00D0, { 0, 1 }), 48)
end

-- ---- progress -----------------------------------------------------------------
local guide = G.register({ name = 'Test guide', steps = steps })
P.set_guide(guide)
WORLD.zone, WORLD.main_job_level = 230, 1
WORLD.items[1122] = 0
eq(P.index, 1, 'starts at step 1')
P.check(1)
P.advance()
-- step 2 is 'mission sandoria 2', which the packet above already marked finished, so the
-- cursor is expected to walk over both.
eq(P.index, 3, 'a ticked step advances the cursor, and takes a finished mission with it')
P.check(3); P.advance()
eq(P.index, 4, 'cursor walks over everything satisfied')
P.back()
eq(P.index, 3, 'back undoes the last tick')
local saved_progress = P.save_state()
P.set_guide(guide, saved_progress)
eq(P.index, 3, 'matching guide structure resumes saved progress')
ok(P.checked[1] == true, 'matching guide structure retains manual checks')
local revised_steps = {}
for i, step in ipairs(steps) do revised_steps[i] = step end
revised_steps[#revised_steps + 1] = G.parse_line('N New step|')
local revised_guide = G.register({ name = 'Test guide revision', steps = revised_steps })
P.set_guide(revised_guide, saved_progress)
eq(P.index, 1, 'changed guide structure resets stale cursor')
ok(next(P.checked) == nil and next(P.skipped) == nil,
    'changed guide structure clears stale step marks')
P.set_guide(guide, saved_progress)
eq(P.index, 3, 'original guide structure can restore its saved progress')
local out_of_range = P.save_state()
out_of_range.index = #guide.steps + 50
P.set_guide(guide, out_of_range)
eq(P.index, #guide.steps + 1, 'matching but out-of-range cursor is clamped')
local damaged_progress = P.save_state()
damaged_progress.index = 'not-a-number'
damaged_progress.checked = { [1] = true, [0] = true, [999] = true, invalid = true }
damaged_progress.skipped = 'not-a-table'
P.set_guide(guide, damaged_progress)
eq(P.index, 1, 'malformed saved cursor defaults safely to step one')
ok(P.checked[1] == true and P.checked[0] == nil and P.checked[999] == nil,
    'saved manual checks are restricted to valid step indices')
ok(next(P.skipped) == nil, 'malformed saved skip map defaults to empty')
P.set_guide(guide)

-- ---- routing ------------------------------------------------------------------
local legs, cost = graph.route(230, 246)
ok(legs ~= nil, 'route exists San d\'Oria -> Port Jeuno')
ok(cost > 0, 'route has a cost')
eq(legs[#legs].to, 246, 'route ends at the destination')
local air = graph.route(232, 246)
eq(#air, 1, 'the airship is one leg from Port San d\'Oria')
eq(air[1].kind, 'transit', 'and it is transit, not walking')
ok(R.describe(air):find('Airship') ~= nil, 'route description names the airship')

ok(graph.route(230, 299) == nil, 'unreachable zone routes to nil')
local version = graph.version
ok(graph.learn(230, 299), 'a new zone line is learned')
ok(graph.version > version, 'learning bumps the graph version, so the router drops its cache')
ok(not graph.learn(230, 299), 'and only learned once')
ok(graph.route(230, 299) ~= nil, 'learning opens the route')

-- The generated zone lines are in the graph, not just the hand-written seed: the two Adoulin
-- cities touch, and nothing in data/travel.lua says so.
local adoulin = graph.route(256, 257)
ok(adoulin ~= nil and #adoulin == 1 and adoulin[1].kind == 'walk', 'Western Adoulin walks to Eastern Adoulin')

-- A seed pair the server's table contradicts is kept out: Southern San d'Oria and Port
-- San d'Oria do not touch, the way round is through Northern San d'Oria.
local sandy = graph.route(230, 232)
ok(#graph.suspect > 0, 'contradicted seed pairs are listed')
ok(sandy ~= nil and #sandy == 2 and sandy[1].to == 231, 'no walk across a contradicted seed pair')

-- NPC crossings: the Cavernous Maw is the only way to the [S] zones.
local maw = graph.route(105, 84)
ok(maw ~= nil and #maw == 1 and maw[1].kind == 'transit', 'Batallia Downs to Batallia Downs [S] is one maw')
ok(maw ~= nil and maw[1].via:find('Cavernous Maw') ~= nil, 'and the leg says so')
local maw_at = require('routing.zonepoints').leg_target(maw[1], 0, 0)
ok(maw_at ~= nil and math.abs(maw_at.x - -45.1) < 1, 'the arrow points at the maw')

-- The Lower Jeuno waypoint is the way to Adoulin.
local wp = graph.route(245, 256)
ok(wp ~= nil and #wp == 1 and wp[1].net == 'waypoint', 'Lower Jeuno to Western Adoulin is the waypoint')

-- Home Points: a network through a hub the caller never sees.
local hp = graph.route(244, 25)
ok(hp ~= nil, 'Tavnazia is reachable')
local folded = hp ~= nil
for _, leg in ipairs(hp or {}) do
    if type(leg.from) ~= 'number' or type(leg.to) ~= 'number' then folded = false end
end
ok(folded, 'the Home Point hub is folded out of the route')
ok(hp ~= nil and hp[#hp].to == 25, 'and the route ends where it should')
local warp = nil
for _, leg in ipairs(hp or {}) do if leg.net == 'homepoint' then warp = leg end end
ok(warp ~= nil and warp.via:find('Home Point') ~= nil, 'the warp leg names the Home Point')
ok(warp ~= nil and require('routing.zonepoints').leg_target(warp, 0, 0) ~= nil,
   'and has a Home Point to walk to')
ok(not graph.learn(26, 236), 'a Home Point warp is not learned as a zone line')
local _, hp_cost = graph.route(244, 25)
ok(graph.eta(hp) ~= nil and graph.eta(hp) < hp_cost,
   'the estimate is the warp time, not the last-resort price it was chosen by')

-- ---- account-wide learned graph (core/learned.lua) ----------------------------
local Learned = require('core.learned')

-- serialize -> parse is a round trip, and parse rejects junk without throwing.
local seed = { ['1:2'] = true, ['2:1'] = true, ['300:301'] = true }
local back = Learned.parse(Learned.serialize(seed))
eq(back['1:2'], true, 'serialize/parse keeps a learned key')
eq(back['300:301'], true, 'serialize/parse keeps a far key')
eq(next(Learned.parse('this is not lua { ')), nil, 'parse of garbage is empty, not an error')
eq(next(Learned.parse('return 7')), nil, 'parse of a non-table chunk is empty')
eq(Learned.parse("return { ['9:9']=true, bad=true, ['x:y']=true }")['9:9'], true,
    'parse keeps well-formed keys')
eq(Learned.parse("return { bad=true, ['x:y']=true }")['bad'], nil,
    'parse drops keys that are not from:to')

-- merge is a union; both directions and both sources survive.
local m = Learned.merge({ ['1:2'] = true }, { ['3:4'] = true, ['1:2'] = true })
eq(m['1:2'], true, 'merge keeps a shared key'); eq(m['3:4'], true, 'merge adds the other source')
local mc = 0; for _ in pairs(m) do mc = mc + 1 end
eq(mc, 2, 'merge de-duplicates')

-- pairs_list de-duplicates both directions to one from<to pair and sorts.
local pl = Learned.pairs_list({ ['5:2'] = true, ['2:5'] = true, ['1:9'] = true })
eq(#pl, 2, 'pairs_list collapses both directions to one pair')
eq(pl[1][1], 1, 'pairs_list is sorted'); eq(pl[1][2], 9, 'and keeps from<to')
eq(pl[2][1], 2, 'second pair low is the min'); eq(pl[2][2], 5, 'second pair high is the max')

-- dump_block is valid Lua that returns the pairs, and names zones when asked.
local block = Learned.dump_block({ ['230:300'] = true }, function (id) return zones.name[id] end)
ok(block:find('Z.learned_walk') ~= nil, 'dump names the table')
ok(block:find('{ 230, 300 }') ~= nil, 'dump lists the pair')
ok(block:find("Southern San d'Oria") ~= nil, 'dump names the zone in a comment')
local chunk = loadstring('local Z = {}\n' .. block .. '\nreturn Z.learned_walk')
ok(chunk ~= nil, 'the dumped block is loadable Lua')
if chunk ~= nil then eq(chunk()[1][1], 230, 'and evaluates to the pair list') end
eq(Learned.dump_block({}):find('0 crossings') ~= nil and true or false, true,
    'an empty dump says so')

-- ---- recommendation -----------------------------------------------------------
WORLD.zone, WORLD.x, WORLD.z, WORLD.yaw = 230, 0, 0, 0
local rec = R.recommend(steps[1], C.world())
eq(rec.mode, 'here', 'step in this zone recommends walking')
ok(rec.distance > 100, 'distance reported')
WORLD.zone = 246
rec = R.recommend(steps[1], C.world())
eq(rec.mode, 'travel', 'step elsewhere recommends travel')
ok(rec.hops >= 1, 'travel has at least one leg')

-- ---- shipped guides -----------------------------------------------------------
require('guides.init')
local shipped = 0
for _, g in ipairs(G.list()) do
    if g.name ~= 'Test guide' then
        shipped = shipped + 1
        eq(#g.errors, 0, ('guide %q parses cleanly'):format(g.name))
        ok(#g.steps > 0, ('guide %q has steps'):format(g.name))
        for _, s in ipairs(g.steps) do
            if s.zone ~= nil then
                ok(zones.name[s.zone] ~= nil, ('guide %q step %d names a real zone'):format(g.name, s.index))
            end
        end
    end
end
ok(shipped >= 4, 'at least four guides ship')

local squire_intro = G.get("San d'Oria - A Squire's Test")
ok(squire_intro ~= nil, 'the first Squire quest walkthrough ships')
if squire_intro ~= nil then
    eq(#squire_intro.errors, 0, 'the first Squire quest walkthrough parses cleanly')
    eq(squire_intro.levels, 'Open at any level', 'the guide metadata does not invent a level gate')
    eq(squire_intro.steps[1].level, nil, 'quest acceptance has no level-gate condition')
    eq(squire_intro.steps[1].quest_accept.id, 10, 'the quest acceptance checks flag 10')
    eq(squire_intro.steps[1].pos.x, -138.33, 'the Balasiel arrow uses the local NPC x coordinate')
    eq(squire_intro.steps[1].pos.z, 65.76, 'the Balasiel arrow uses the local NPC z coordinate')
    eq(squire_intro.steps[2].zone, 190, 'the in-game quest hint routes to King Ranperre’s Tomb')
    eq(squire_intro.steps[3].item.id, 940, 'the guide waits for a Revival Tree Root')
    eq(squire_intro.steps[3].zone, 190, 'the root objective is in King Ranperre’s Tomb')
    eq(squire_intro.steps[3].pos.x, 2.9, 'the Spook arrow uses the local spawn x coordinate')
    eq(squire_intro.steps[3].pos.z, -99.3, 'the Spook arrow uses the local spawn z coordinate')
    eq(squire_intro.steps[3].pos.r, 10, 'the Spook arrow uses the default arrival radius')
    eq(squire_intro.steps[5].quest.id, 10, 'turn-in waits for the quest completion flag')
    WORLD.zone, WORLD.x, WORLD.z = 230, -138.33, 65.76
    local balasiel = R.recommend(squire_intro.steps[1], C.world())
    eq(balasiel.mode, 'here', 'Balasiel has a local arrow')
    ok(balasiel.distance < 0.1, 'the Balasiel arrow reaches the local SQL NPC position')
    eq(R.recommend(squire_intro.steps[2], C.world()).mode, 'travel', 'the guide routes to the Tomb')
    WORLD.zone, WORLD.x, WORLD.z = 190, 2.912, -99.302
    local spook = R.recommend(squire_intro.steps[3], C.world())
    eq(spook.mode, 'here', 'the Spook drop location uses a local arrow')
    ok(spook.distance < 0.1, 'the Spook arrow reaches the rounded SQL spawn point')
    story.reset()
    WORLD.main_job_level = 1
    WORLD.zone = 230
    P.set_guide(squire_intro)
    P.advance()
    eq(P.index, 1, 'the first Squire guide offers quest acceptance at level 1')
    story.on_packet(0x056, packet_0056(0x0050, { 10 }), 48)
    P.advance()
    eq(P.index, 2, 'quest acceptance advances to the Tomb route')
    WORLD.zone = 190
    P.advance()
    eq(P.index, 3, 'entering the Tomb advances to the item objective')
    ok(not P.complete(), 'the root drop is required before returning')
    WORLD.items[940] = 1
    P.advance()
    eq(P.index, 4, 'the Revival Tree Root advances to the return route')
    WORLD.zone = 230
    P.advance()
    eq(P.index, 5, 'returning to San d’Oria advances to turn-in')
    story.on_packet(0x056, packet_0056(0x0090, { 10 }), 48)
    P.advance()
    ok(P.complete(), 'quest completion finishes the full first Squire route')
    story.reset()
    P.set_guide(nil)
    WORLD.items[940] = nil
end

local sandoria_first_mission = G.get("San d'Oria - Smash the Orcish Scouts")
ok(sandoria_first_mission ~= nil, 'the first San d’Oria mission walkthrough ships')
if sandoria_first_mission ~= nil then
    eq(#sandoria_first_mission.errors, 0, 'the first San d’Oria mission walkthrough parses cleanly')
    eq(sandoria_first_mission.steps[1].mission_accept.id, 0, 'the mission acceptance waits for mission 0')
    eq(sandoria_first_mission.steps[3].item.id, 16656, 'the objective waits for an Orcish Axe')
    eq(sandoria_first_mission.steps[3].zone, 100, 'the item waypoint is in West Ronfaure')
    eq(sandoria_first_mission.steps[5].mission.id, 0, 'turn-in waits for mission 0 completion')
    eq(sandoria_first_mission.steps[5].pos.x, -112.82, 'Endracion arrow uses the local NPC x coordinate')
    eq(sandoria_first_mission.steps[5].pos.z, -37.19, 'Endracion arrow uses the local NPC z coordinate')
    eq(sandoria_first_mission.steps[1].pos.x, 93.42, 'Ambrotien arrow uses the exact local NPC x coordinate')
    eq(sandoria_first_mission.steps[1].pos.z, -57.35, 'Ambrotien arrow uses the exact local NPC z coordinate')
    WORLD.zone, WORLD.x, WORLD.z = 230, 93.42, -57.35
    eq(R.recommend(sandoria_first_mission.steps[1], C.world()).mode, 'here', 'Ambrotien has a mission-start arrow')
    story.reset()
    P.set_guide(sandoria_first_mission)
    P.advance()
    eq(P.index, 1, 'the mission route waits for server-side acceptance')
    story.on_packet(0x056, accepted_mission_packet, #accepted_mission_packet)
    P.advance()
    eq(P.index, 2, 'mission acceptance advances to West Ronfaure')
    WORLD.zone = 100
    P.advance()
    eq(P.index, 3, 'entering West Ronfaure advances to the item objective')
    WORLD.x, WORLD.z = -366.087, 215.323
    local orc = R.recommend(sandoria_first_mission.steps[3], C.world())
    eq(orc.mode, 'here', 'the Orcish Fodder spawn has an arrow')
    ok(orc.distance < 0.1, 'the Orcish Fodder arrow uses the local SQL spawn coordinates')
    WORLD.items[16656] = 1
    P.advance()
    eq(P.index, 4, 'the Orcish Axe advances to the return route')
    WORLD.zone = 230
    P.advance()
    eq(P.index, 5, 'returning advances to the mission turn-in')
    WORLD.zone, WORLD.x, WORLD.z = 230, -112.82, -37.19
    local endracion = R.recommend(sandoria_first_mission.steps[5], C.world())
    eq(endracion.mode, 'here', 'the mission turn-in arrow reaches Endracion')
    ok(endracion.distance < 0.1, 'the Endracion arrow reaches the local SQL NPC position')
    story.on_packet(0x056, packet_0056(0x00D0, { 0 }), 48)
    P.advance()
    ok(P.complete(), 'mission completion finishes the entire M1-1 route')
    story.reset()
    P.set_guide(nil)
    WORLD.items[16656] = nil
end

local function nation_mission_packet(nation, current)
    return string.char(0, 0, 0, 0)
        .. string.char(nation, 0, 0, 0)
        .. string.char(current % 256, math.floor(current / 256) % 256, 0, 0)
        .. string.rep('\0', 0x24 - 0x0C)
        .. string.char(0xFF, 0xFF, 0, 0)
        .. string.rep('\0', 8)
end

local sandoria_second_mission = G.get("San d'Oria - Bat Hunt")
ok(sandoria_second_mission ~= nil, 'the second San d’Oria mission walkthrough ships')
if sandoria_second_mission ~= nil then
    eq(#sandoria_second_mission.errors, 0, 'the San d’Oria M1-2 walkthrough parses cleanly')
    eq(sandoria_second_mission.steps[1].mission_accept.id, 1, 'San d’Oria M1-2 acceptance waits for mission 1')
    eq(sandoria_second_mission.steps[3].zone, 190, 'the upper tombstone is in King Ranperre’s Tomb')
    eq(sandoria_second_mission.steps[4].item.id, 1112, 'the objective waits for Orcish Mail Scales item 1112')
    eq(sandoria_second_mission.steps[4].zone, 190, 'the item waypoint is in King Ranperre’s Tomb')
    eq(sandoria_second_mission.steps[6].mission.id, 1, 'San d’Oria M1-2 turn-in waits for mission 1 completion')
    eq(sandoria_second_mission.steps[1].pos.x, 93.42, 'Bat Hunt arrow uses Ambrotien local x')
    eq(sandoria_second_mission.steps[1].pos.z, -57.35, 'Bat Hunt arrow uses Ambrotien local z')
    WORLD.zone, WORLD.x, WORLD.z = 230, 93.42, -57.35
    eq(R.recommend(sandoria_second_mission.steps[1], C.world()).mode, 'here', 'Ambrotien has a local M1-2 acceptance arrow')
    story.reset()
    P.set_guide(sandoria_second_mission)
    local packet = nation_mission_packet(0, 1)
    story.on_packet(0x056, packet, #packet)
    P.advance()
    eq(P.index, 2, 'San d’Oria M1-2 acceptance advances to King Ranperre’s Tomb')
    WORLD.zone = 190
    P.advance()
    eq(P.index, 3, 'entering the tomb advances to the upper tombstone')
    WORLD.x, WORLD.z = 1, -101
    local tombstone = R.recommend(sandoria_second_mission.steps[3], C.world())
    eq(tombstone.mode, 'here', 'the upper tombstone has a local arrow')
    ok(tombstone.distance < 0.1, 'the tombstone arrow matches the mission-script position')
    P.advance()
    eq(P.index, 3, 'the tombstone interaction remains a manual confirmation')
    P.check()
    P.advance()
    eq(P.index, 4, 'confirming the tombstone advances to the scale objective')
    WORLD.x, WORLD.z = -10, -89
    local bats = R.recommend(sandoria_second_mission.steps[4], C.world())
    eq(bats.mode, 'here', 'the Ding Bat group has a local drop arrow')
    ok(bats.distance < 0.1, 'the Ding Bat arrow matches the local SQL spawn point')
    WORLD.items[1112] = 1
    P.advance()
    eq(P.index, 5, 'Orcish Mail Scales advance to the return route')
    WORLD.zone = 230
    P.advance()
    eq(P.index, 6, 'returning to Southern San d’Oria advances to turn-in')
    story.on_packet(0x056, packet_0056(0x00D0, { 0, 1 }), 48)
    P.advance()
    ok(P.complete(), 'mission completion finishes the San d’Oria M1-2 route')
    story.reset()
    P.set_guide(nil)
    WORLD.items[1112] = nil
end

local sandoria_third_mission = G.get("San d'Oria - Save the Children")
ok(sandoria_third_mission ~= nil, 'the San d’Oria M1-3 walkthrough ships')
if sandoria_third_mission ~= nil then
    eq(#sandoria_third_mission.errors, 0, 'the San d’Oria M1-3 walkthrough parses cleanly')
    eq(#sandoria_third_mission.steps, 8, 'the San d’Oria M1-3 route covers all eight mission checkpoints')
    eq(sandoria_third_mission.steps[1].mission_accept.id, 2, 'Save the Children waits for mission 2 acceptance')
    eq(sandoria_third_mission.steps[2].fixed, true, 'Arnau briefing requires player confirmation')
    eq(sandoria_third_mission.steps[4].fixed, true, 'the battlefield remains a manual victory checkpoint')
    eq(sandoria_third_mission.steps[5].key_item, 157, 'the post-battle step waits for Orcish Hut Key')
    eq(sandoria_third_mission.steps[6].fixed, true, 'opening Hut Door requires player confirmation')
    eq(sandoria_third_mission.steps[8].mission.id, 2, 'the turn-in waits for mission 2 completion')
    eq(sandoria_third_mission.steps[1].pos.x, 93.42, 'M1-3 start arrow uses Ambrotien local x')
    eq(sandoria_third_mission.steps[1].pos.z, -57.35, 'M1-3 start arrow uses Ambrotien local z')
    eq(sandoria_third_mission.steps[2].pos.x, 149.89, 'M1-3 briefing arrow uses Arnau local x')
    eq(sandoria_third_mission.steps[2].pos.z, 141.87, 'M1-3 briefing arrow uses Arnau local z')
    eq(sandoria_third_mission.steps[4].pos.x, -165.36, 'M1-3 battlefield arrow uses Hut Door local x')
    eq(sandoria_third_mission.steps[4].pos.z, 77.77, 'M1-3 battlefield arrow uses Hut Door local z')

    WORLD.zone, WORLD.x, WORLD.z = 230, 93.42, -57.35
    local ambrotien = R.recommend(sandoria_third_mission.steps[1], C.world())
    eq(ambrotien.mode, 'here', 'Ambrotien has a local M1-3 acceptance arrow')
    ok(ambrotien.distance < 0.1, 'the M1-3 start arrow reaches Ambrotien')
    story.reset()
    P.set_guide(sandoria_third_mission)
    P.advance()
    eq(P.index, 1, 'the M1-3 guide waits for server-side mission acceptance')
    story.on_packet(0x056, nation_mission_packet(0, 2), 48)
    P.advance()
    eq(P.index, 2, 'mission acceptance routes to Arnau’s briefing')
    WORLD.zone, WORLD.x, WORLD.z = 231, 149.89, 141.87
    local arnau = R.recommend(sandoria_third_mission.steps[2], C.world())
    eq(arnau.mode, 'here', 'Arnau has a local briefing arrow')
    ok(arnau.distance < 0.1, 'the Arnau arrow reaches the local SQL NPC position')
    P.check()
    P.advance()
    eq(P.index, 3, 'manual confirmation of Arnau’s mission briefing advances the route')
    WORLD.zone = 140
    P.advance()
    eq(P.index, 4, 'entering Ghelsba Outpost points to the battlefield door')
    WORLD.x, WORLD.z = -165.36, 77.77
    local hut = R.recommend(sandoria_third_mission.steps[4], C.world())
    eq(hut.mode, 'here', 'the Save the Children battlefield has a local arrow')
    ok(hut.distance < 0.1, 'the battlefield arrow reaches Hut Door')
    P.check()
    P.advance()
    eq(P.index, 5, 'the manual battlefield checkpoint advances only after victory')
    P.advance()
    eq(P.index, 5, 'the guide waits for the server-awarded Orcish Hut Key')
    WORLD.key_items[157] = true
    P.advance()
    eq(P.index, 6, 'the Orcish Hut Key advances to the required door event')
    P.check()
    P.advance()
    eq(P.index, 7, 'confirming the Hut Door event routes back to San d’Oria')
    WORLD.zone = 230
    P.advance()
    eq(P.index, 8, 'returning to San d’Oria routes to Ambrotien turn-in')
    story.on_packet(0x056, packet_0056(0x00D0, { 0, 1, 2 }), 48)
    P.advance()
    ok(P.complete(), 'mission completion finishes the Save the Children route')
    story.reset()
    P.set_guide(nil)
    WORLD.key_items[157] = nil
end

local sandoria_fourth_mission = G.get("San d'Oria - The Rescue Drill")
ok(sandoria_fourth_mission ~= nil, 'the San d’Oria M2-1 walkthrough ships')
if sandoria_fourth_mission ~= nil then
    eq(#sandoria_fourth_mission.errors, 0, 'the San d’Oria M2-1 walkthrough parses cleanly')
    eq(#sandoria_fourth_mission.steps, 19, 'the Rescue Drill covers acceptance through turn-in')
    eq(sandoria_fourth_mission.steps[1].mission_accept.id, 3, 'the Rescue Drill waits for mission 3 acceptance')
    eq(sandoria_fourth_mission.steps[3].fixed, true, 'the drill start dialogue is a manual checkpoint')
    eq(sandoria_fourth_mission.steps[12].fixed, true, 'Ruillont’s instructions remain a manual checkpoint')
    eq(sandoria_fourth_mission.steps[15].fixed, true, 'the sword handoff to Ruillont remains manual')
    eq(sandoria_fourth_mission.steps[17].key_item, 65, 'the certificate step waits for key item 65')
    eq(sandoria_fourth_mission.steps[19].mission.id, 3, 'the turn-in waits for mission 3 completion')
    local expected_waypoints = {
        { 1, 93.42, -57.35 }, { 3, -481.20, 220.55 }, { 4, -286.48, 287.82 },
        { 5, -307.02, 341.55 }, { 6, -344.96, 265.02 }, { 7, -291.76, 141.19 },
        { 8, -261.94, 127.61 }, { 9, -315.84, 184.48 }, { 10, -363.42, 267.72 },
        { 12, -69.85, 610.81 }, { 17, -344.96, 265.02 }, { 19, 93.42, -57.35 },
    }
    for _, target in ipairs(expected_waypoints) do
        local step = sandoria_fourth_mission.steps[target[1]]
        eq(step.pos.x, target[2], ('Rescue Drill step %d uses its local SQL x coordinate'):format(target[1]))
        eq(step.pos.z, target[3], ('Rescue Drill step %d uses its local SQL z coordinate'):format(target[1]))
    end
    WORLD.zone, WORLD.x, WORLD.z = 230, 93.42, -57.35
    local ambrotien = R.recommend(sandoria_fourth_mission.steps[1], C.world())
    eq(ambrotien.mode, 'here', 'Rescue Drill acceptance points to Ambrotien')
    ok(ambrotien.distance < 0.1, 'Rescue Drill start arrow reaches Ambrotien')
    story.reset()
    P.set_guide(sandoria_fourth_mission)
    P.advance()
    eq(P.index, 1, 'Rescue Drill waits for server-side mission acceptance')
    story.on_packet(0x056, nation_mission_packet(0, 3), 48)
    P.advance()
    eq(P.index, 2, 'mission acceptance routes to La Theine Plateau')
    WORLD.zone = 102
    P.advance()
    eq(P.index, 3, 'entering La Theine routes to the drill starting guard')
    for index = 3, 10 do
        local step = sandoria_fourth_mission.steps[index]
        WORLD.zone, WORLD.x, WORLD.z = step.zone, step.pos.x, step.pos.z
        local arrow = R.recommend(step, C.world())
        eq(arrow.mode, 'here', ('Rescue Drill step %d resolves to an exact local NPC arrow'):format(index))
        ok(arrow.distance < 0.1, ('Rescue Drill step %d reaches its NPC marker'):format(index))
        P.check()
        P.advance()
    end
    eq(P.index, 11, 'the La Theine drill checkpoints lead to the Ordelles travel step')
    WORLD.zone = 193
    P.advance()
    eq(P.index, 12, 'entering Ordelles Caves routes to Ruillont')
    WORLD.zone, WORLD.x, WORLD.z = 193, -69.85, 610.81
    P.advance()
    eq(P.index, 12, 'the Ruillont cutscene requires manual confirmation')
    P.check(); P.advance()
    eq(P.index, 13, 'Ruillont instructions route to the La Theine return trip')
    P.advance()
    eq(P.index, 13, 'the return trip waits until the player leaves the caves')
    WORLD.zone = 102
    P.advance()
    eq(P.index, 14, 'returning to La Theine routes to the conditional rescue guard')
    P.check(); P.advance()
    eq(P.index, 15, 'the selected guard checkpoint leads to the sword trade')
    WORLD.zone, WORLD.x, WORLD.z = 193, -69.85, 610.81
    P.check(); P.advance()
    eq(P.index, 16, 'the sword trade checkpoint leads back to La Theine')
    WORLD.zone = 102
    P.advance()
    eq(P.index, 17, 'returning to La Theine routes to the certificate checkpoint')
    WORLD.x, WORLD.z = -344.96, 265.02
    WORLD.key_items[65] = true
    P.advance()
    eq(P.index, 17, 'the certificate checkpoint still requires manual confirmation')
    P.check(); P.advance()
    eq(P.index, 18, 'manual certificate confirmation routes back to San d’Oria')
    WORLD.zone = 230
    P.advance()
    eq(P.index, 19, 'returning to San d’Oria routes to mission turn-in')
    story.on_packet(0x056, packet_0056(0x00D0, { 0, 1, 2, 3 }), 48)
    P.advance()
    ok(P.complete(), 'mission completion finishes The Rescue Drill route')
    story.reset()
    P.set_guide(nil)
    WORLD.key_items[65] = nil
end

local bastok_second_mission = G.get('Bastok - A Geological Survey')
ok(bastok_second_mission ~= nil, 'the second Bastok mission walkthrough ships')
if bastok_second_mission ~= nil then
    eq(#bastok_second_mission.errors, 0, 'the Bastok M1-2 walkthrough parses cleanly')
    eq(bastok_second_mission.steps[1].mission_accept.id, 1, 'Bastok M1-2 acceptance waits for mission 1')
    eq(bastok_second_mission.steps[1].pos.x, -361.9, 'Bastok M1-2 arrow uses Cleades local x')
    eq(bastok_second_mission.steps[1].pos.z, -169.13, 'Bastok M1-2 arrow uses Cleades local z')
    eq(bastok_second_mission.steps[2].key_item, 3, "Cid's test starts when Blue Acidity Tester key item 3 arrives")
    eq(bastok_second_mission.steps[2].pos.x, -12.6, 'Bastok M1-2 Cid arrow uses local x')
    eq(bastok_second_mission.steps[2].pos.z, 2.43, 'Bastok M1-2 Cid arrow uses local z')
    for index = 4, 6 do
        eq(bastok_second_mission.steps[index].key_item, 4, ('Dangruf geyser %d waits for Red Acidity Tester key item 4'):format(index - 3))
        eq(bastok_second_mission.steps[index].zone, 191, ('Dangruf geyser %d is in Dangruf Wadi'):format(index - 3))
    end
    eq(bastok_second_mission.steps[8].mission.id, 1, 'Bastok M1-2 turn-in waits for mission 1 completion')
    WORLD.zone, WORLD.x, WORLD.z = 235, -361.9, -169.13
    eq(R.recommend(bastok_second_mission.steps[1], C.world()).mode, 'here', 'Cleades has a local M1-2 acceptance arrow')
    story.reset()
    P.set_guide(bastok_second_mission)
    local packet = nation_mission_packet(1, 1)
    story.on_packet(0x056, packet, #packet)
    P.advance()
    eq(P.index, 2, 'Bastok M1-2 acceptance advances to Cid')
    WORLD.zone, WORLD.x, WORLD.z = 237, -12.6, 2.43
    WORLD.key_items[3] = true
    P.advance()
    eq(P.index, 3, 'the blue tester advances to travel to Dangruf Wadi')
    WORLD.zone = 191
    P.advance()
    eq(P.index, 4, 'entering Dangruf Wadi points at the first geyser')
    P.skip()
    P.advance()
    eq(P.index, 5, 'a failed first geyser attempt advances to the next one')
    WORLD.key_items[4] = true
    P.advance()
    eq(P.index, 7, 'one successful geyser satisfies the remaining alternatives')
    WORLD.zone = 237
    P.advance()
    eq(P.index, 8, 'returning to Metalworks advances to Cid turn-in')
    story.on_packet(0x056, packet_0056(0x00D0, { 64, 65 }), 48)
    P.advance()
    ok(P.complete(), 'mission completion finishes the Bastok M1-2 route')
    story.reset()
    P.set_guide(nil)
    WORLD.key_items[3], WORLD.key_items[4] = nil, nil
end

local bastok_first_mission = G.get('Bastok - The Zeruhn Report')
ok(bastok_first_mission ~= nil, 'the first Bastok mission walkthrough ships')
if bastok_first_mission ~= nil then
    eq(#bastok_first_mission.errors, 0, 'the Bastok M1-1 walkthrough parses cleanly')
    eq(bastok_first_mission.steps[1].mission_accept.area, 'bastok', 'Bastok acceptance uses its nation mission flag')
    eq(bastok_first_mission.steps[3].key_item, 1, 'the Zeruhn Report objective waits for key item 1')
    eq(bastok_first_mission.steps[3].pos.x, -60.92, 'Makarim arrow uses the local NPC x coordinate')
    eq(bastok_first_mission.steps[3].pos.z, -333.29, 'Makarim arrow uses the local NPC z coordinate')
    eq(bastok_first_mission.steps[5].mission.area, 'bastok', 'Bastok turn-in waits for its mission completion flag')
    eq(bastok_first_mission.steps[5].pos.x, 66.9, 'Naji arrow uses the local NPC x coordinate')
    eq(bastok_first_mission.steps[5].pos.z, -4.6, 'Naji arrow uses the local NPC z coordinate')
    eq(bastok_first_mission.steps[1].pos.x, -361.9, 'Bastok M1-1 arrow uses Cleades local x')
    eq(bastok_first_mission.steps[1].pos.z, -169.13, 'Bastok M1-1 arrow uses Cleades local z')
    WORLD.zone, WORLD.x, WORLD.z = 235, -361.9, -169.13
    eq(R.recommend(bastok_first_mission.steps[1], C.world()).mode, 'here', 'Cleades has a local mission-start arrow')
    story.reset()
    P.set_guide(bastok_first_mission)
    P.advance()
    eq(P.index, 1, 'the Bastok mission route waits for server-side acceptance')
    local packet = nation_mission_packet(1, 0)
    story.on_packet(0x056, packet, #packet)
    P.advance()
    eq(P.index, 2, 'Bastok mission acceptance advances to Zeruhn Mines')
    WORLD.zone = 172
    P.advance()
    eq(P.index, 3, 'entering Zeruhn Mines advances to the report objective')
    WORLD.zone, WORLD.x, WORLD.z = 172, -60.92, -333.29
    local makarim = R.recommend(bastok_first_mission.steps[3], C.world())
    eq(makarim.mode, 'here', 'the Zeruhn Report arrow reaches Makarim')
    ok(makarim.distance < 0.1, 'the Makarim arrow reaches the local SQL NPC position')
    ok(not P.complete(), 'the Zeruhn Report key item is required before returning')
    WORLD.key_items[1] = true
    P.advance()
    eq(P.index, 4, 'the Zeruhn Report advances to the return route')
    WORLD.zone = 237
    P.advance()
    eq(P.index, 5, 'returning to Metalworks advances to Naji turn-in')
    WORLD.zone, WORLD.x, WORLD.z = 237, 66.9, -4.6
    local naji = R.recommend(bastok_first_mission.steps[5], C.world())
    eq(naji.mode, 'here', 'the Bastok return arrow reaches Naji')
    ok(naji.distance < 0.1, 'the Naji arrow reaches the local SQL NPC position')
    story.on_packet(0x056, packet_0056(0x00D0, { 64 }), 48)
    P.advance()
    ok(P.complete(), 'mission completion finishes the Bastok M1-1 route')
    story.reset()
    P.set_guide(nil)
    WORLD.key_items[1] = nil
end

local bastok_third_mission = G.get('Bastok - Fetichism')
ok(bastok_third_mission ~= nil, 'the third Bastok mission walkthrough ships')
if bastok_third_mission ~= nil then
    eq(#bastok_third_mission.errors, 0, 'the Bastok M1-3 walkthrough parses cleanly')
    eq(bastok_third_mission.steps[1].mission_accept.id, 2, 'Bastok M1-3 acceptance waits for mission 2')
    eq(bastok_third_mission.steps[1].pos.x, -361.9, 'Bastok M1-3 arrow uses Cleades local x')
    eq(bastok_third_mission.steps[1].pos.z, -169.13, 'Bastok M1-3 arrow uses Cleades local z')
    for index, item in ipairs({ 606, 607, 608, 609 }) do
        eq(bastok_third_mission.steps[index + 1].item.id, item, ('fetich objective %d waits for item %d'):format(index, item))
        eq(bastok_third_mission.steps[index + 1].zone, 143, ('fetich objective %d is in Palborough Mines'):format(index))
        eq(bastok_third_mission.steps[index + 1].pos.x, 52, ('fetich objective %d uses the local spawn x coordinate'):format(index))
        eq(bastok_third_mission.steps[index + 1].pos.z, 60, ('fetich objective %d uses the local spawn z coordinate'):format(index))
    end
    eq(bastok_third_mission.steps[7].mission.id, 2, 'Bastok M1-3 turn-in waits for mission 2 completion')
    WORLD.zone, WORLD.x, WORLD.z = 235, -361.9, -169.13
    eq(R.recommend(bastok_third_mission.steps[1], C.world()).mode, 'here', 'Cleades has a local M1-3 acceptance arrow')
    story.reset()
    P.set_guide(bastok_third_mission)
    local packet = nation_mission_packet(1, 2)
    story.on_packet(0x056, packet, #packet)
    P.advance()
    eq(P.index, 2, 'Bastok M1-3 acceptance advances to the first fetich objective')
    WORLD.zone, WORLD.x, WORLD.z = 143, 52, 60
    local fetich = R.recommend(bastok_third_mission.steps[2], C.world())
    eq(fetich.mode, 'here', 'the Fetich route arrow reaches the nearby Amber Quadav spawn')
    ok(fetich.distance < 0.1, 'the Fetich arrow reaches the rounded local SQL spawn point')
    P.advance()
    eq(P.index, 2, 'Palborough Mines provides a local spawn arrow')
    for index, item in ipairs({ 606, 607, 608, 609 }) do
        WORLD.items[item] = 1
        P.advance()
        eq(P.index, index + 2, ('fetich piece %d advances the checklist'):format(index))
    end
    eq(P.index, 6, 'all four pieces advance to the return route')
    WORLD.zone = 235
    P.advance()
    eq(P.index, 7, 'returning to Bastok Markets advances to the trade-in')
    story.on_packet(0x056, packet_0056(0x00D0, { 64, 65, 66 }), 48)
    P.advance()
    ok(P.complete(), 'mission completion finishes the Bastok M1-3 route')
    story.reset()
    P.set_guide(nil)
    for _, item in ipairs({ 606, 607, 608, 609 }) do WORLD.items[item] = nil end
end

local windurst_first_mission = G.get('Windurst - The Horutoto Ruins Experiment')
ok(windurst_first_mission ~= nil, 'the first Windurst mission walkthrough ships')
if windurst_first_mission ~= nil then
    eq(#windurst_first_mission.errors, 0, 'the Windurst M1-1 walkthrough parses cleanly')
    eq(windurst_first_mission.steps[1].mission_accept.area, 'windurst', 'Windurst acceptance uses its nation mission flag')
    eq(windurst_first_mission.steps[5].key_item, 28, 'the first gizmo checkpoint waits for Cracked Mana Orb key item 28')
    eq(windurst_first_mission.steps[1].pos.x, -230.63, 'Windurst M1-1 arrow uses Janshura local x')
    eq(windurst_first_mission.steps[1].pos.z, 184.05, 'Windurst M1-1 arrow uses Janshura local z')
    eq(windurst_first_mission.steps[2].pos.x, -111.14, 'Windurst M1-1 arrow uses Hakkuru local x')
    eq(windurst_first_mission.steps[2].pos.z, 102.06, 'Windurst M1-1 arrow uses Hakkuru local z')
    for index = 5, 10 do
        eq(windurst_first_mission.steps[index].key_item, 28, ('Windurst gizmo checkpoint %d shares the server item condition'):format(index - 4))
        eq(windurst_first_mission.steps[index].zone, 192, ('Windurst gizmo checkpoint %d is in Inner Horutoto Ruins'):format(index - 4))
    end
    eq(windurst_first_mission.steps[12].mission.area, 'windurst', 'Windurst turn-in waits for its mission completion flag')
    WORLD.zone, WORLD.x, WORLD.z = 240, -230.63, 184.05
    eq(R.recommend(windurst_first_mission.steps[1], C.world()).mode, 'here', 'Janshura-Rashura has a local mission-start arrow')
    story.reset()
    P.set_guide(windurst_first_mission)
    local packet = nation_mission_packet(2, 0)
    story.on_packet(0x056, packet, #packet)
    P.advance()
    eq(P.index, 2, 'Windurst mission acceptance advances to Hakkuru-Rinkuru')
    WORLD.zone, WORLD.x, WORLD.z = 240, -111.14, 102.06
    local hakkuru = R.recommend(windurst_first_mission.steps[2], C.world())
    eq(hakkuru.mode, 'here', 'Hakkuru has a Port Windurst arrow')
    ok(hakkuru.distance < 0.1, 'the Hakkuru arrow reaches the local SQL NPC position')
    WORLD.zone, WORLD.x, WORLD.z = 240, -230.63, 184.05
    P.advance()
    eq(P.index, 2, 'the guide waits for the player to finish Hakkuru-Rinkuru dialogue')
    P.check()
    P.advance()
    eq(P.index, 3, 'checking the dialogue step advances to Inner Horutoto Ruins')
    WORLD.zone = 192
    P.advance()
    eq(P.index, 4, 'entering the ruins advances to the gate objective')
    P.check()
    P.advance()
    eq(P.index, 5, 'checking the gate advances to randomized gizmo searches')
    P.skip()
    P.advance()
    eq(P.index, 6, 'a wrong gizmo can be skipped to the next marked location')
    WORLD.key_items[28] = true
    P.advance()
    eq(P.index, 11, 'the orb satisfies all remaining randomized gizmo checkpoints')
    WORLD.zone = 240
    P.advance()
    eq(P.index, 12, 'returning to Port Windurst advances to mission turn-in')
    story.on_packet(0x056, packet_0056(0x00D0, { 128 }), 48)
    P.advance()
    ok(P.complete(), 'mission completion finishes the Windurst M1-1 route')
    story.reset()
    P.set_guide(nil)
    WORLD.key_items[28] = nil
end

local windurst_second_mission = G.get('Windurst - The Heart of the Matter')
ok(windurst_second_mission ~= nil, 'the second Windurst mission walkthrough ships')
if windurst_second_mission ~= nil then
    eq(#windurst_second_mission.errors, 0, 'the Windurst M1-2 walkthrough parses cleanly')
    eq(windurst_second_mission.steps[1].mission_accept.id, 1, 'Windurst M1-2 acceptance waits for mission 1')
    eq(windurst_second_mission.steps[1].pos.x, -230.63, 'Windurst M1-2 arrow uses Janshura local x')
    eq(windurst_second_mission.steps[1].pos.z, 184.05, 'Windurst M1-2 arrow uses Janshura local z')
    eq(windurst_second_mission.steps[2].key_item, 37, 'Apururu objective waits for the first Dark Mana Orb')
    eq(windurst_second_mission.steps[2].pos.x, -12.09, 'Apururu arrow uses local NPC x')
    eq(windurst_second_mission.steps[2].pos.z, 15.94, 'Apururu arrow uses local NPC z')
    eq(windurst_second_mission.steps[3].key_item, 112, 'Pore-Ohre objective waits for the Southeastern Star Charm')
    eq(windurst_second_mission.steps[3].pos.x, 262.27, 'Pore-Ohre arrow uses local NPC x')
    eq(windurst_second_mission.steps[3].pos.z, -459.61, 'Pore-Ohre arrow uses local NPC z')
    eq(windurst_second_mission.steps[4].zone, 194, 'the ruin route enters Outer Horutoto Ruins')
    ok(windurst_second_mission.steps[5].fixed, 'placing six orbs is a deliberate manual checkpoint')
    ok(windurst_second_mission.steps[6].fixed, 'the gate interaction is a deliberate manual checkpoint')
    local gizmo_positions = {
        { 542, -618 }, { 500, -573 }, { 458, -618 },
        { 458, -702 }, { 500, -747 }, { 542, -702 },
    }
    for index, position in ipairs(gizmo_positions) do
        local step = windurst_second_mission.steps[index + 6]
        eq(step.key_item, 58 + index, ('glowing Mana Orb objective %d waits for key item %d'):format(index, 58 + index))
        eq(step.zone, 194, ('glowing Mana Orb objective %d is in Outer Horutoto Ruins'):format(index))
        eq(step.pos.x, position[1], ('glowing Mana Orb gizmo %d uses its local SQL X coordinate'):format(index))
        eq(step.pos.z, position[2], ('glowing Mana Orb gizmo %d uses its local SQL Z coordinate'):format(index))
    end
    eq(windurst_second_mission.steps[13].zone, 116, 'the expected Cardian scene triggers in East Sarutabaruta')
    eq(windurst_second_mission.steps[14].mission.id, 1, 'Windurst M1-2 turn-in waits for mission 1 completion')

    WORLD.zone, WORLD.x, WORLD.z = 240, -230.63, 184.05
    eq(R.recommend(windurst_second_mission.steps[1], C.world()).mode, 'here', 'Janshura-Rashura has a local M1-2 mission-start arrow')
    story.reset()
    P.set_guide(windurst_second_mission)
    local packet = nation_mission_packet(2, 1)
    story.on_packet(0x056, packet, #packet)
    P.advance()
    eq(P.index, 2, 'Windurst M1-2 acceptance advances to Apururu')
    WORLD.zone, WORLD.x, WORLD.z = 241, -12.09, 15.94
    eq(R.recommend(windurst_second_mission.steps[2], C.world()).mode, 'here', 'Apururu has a local mission arrow')
    WORLD.key_items[37] = true
    P.advance()
    eq(P.index, 3, 'the Dark Mana Orb advances the guide to Pore-Ohre')
    WORLD.zone, WORLD.x, WORLD.z = 116, 262.27, -459.61
    WORLD.key_items[112] = true
    P.advance()
    eq(P.index, 4, 'the Star Charm advances the guide to Outer Horutoto Ruins')
    WORLD.zone = 194
    P.advance()
    P.check()
    P.advance()
    eq(P.index, 5, 'entering Outer Horutoto Ruins advances to orb placement')
    P.advance()
    eq(P.index, 5, 'orb placement remains manual until confirmed')
    P.check()
    P.advance()
    eq(P.index, 6, 'confirmed orb placement advances to the gate')
    P.check()
    P.advance()
    eq(P.index, 7, 'confirmed gate event advances to the first glowing orb')
    for index = 1, 6 do
        WORLD.key_items[58 + index] = true
        P.advance()
        eq(P.index, index + 7, ('glowing Mana Orb %d advances sequentially'):format(index))
    end
    eq(P.index, 13, 'six glowing orbs advance to the Cardian scene')
    WORLD.zone = 116
    P.advance()
    eq(P.index, 14, 'East Sarutabaruta advances to the Apururu turn-in')
    WORLD.zone = 241
    story.on_packet(0x056, packet_0056(0x00D0, { 128, 129 }), 48)
    P.advance()
    ok(P.complete(), 'mission completion finishes the Windurst M1-2 route')
    story.reset()
    P.set_guide(nil)
    WORLD.key_items[37], WORLD.key_items[112] = nil, nil
    for key_item = 59, 64 do WORLD.key_items[key_item] = nil end
end

local squire = G.get("San d'Oria - A Squire's Test II")
ok(squire ~= nil, 'the source-verified quest walkthrough ships')
if squire ~= nil then
    eq(#squire.errors, 0, 'the Squire quest walkthrough parses cleanly')
    eq(squire.steps[3].quest_accept.area, 'sandoria', 'the acceptance step uses San d’Oria quest flags')
    eq(squire.steps[3].quest_accept.id, 19, 'the acceptance step checks quest id 19')
    eq(squire.steps[4].kind, 'travel', 'the guide routes into Ordelles Caves')
    eq(squire.steps[4].zone, 193, 'the cave route uses the Ordelles zone')
    WORLD.zone, WORLD.x, WORLD.z = 230, -138.33, 65.76
    local route = R.recommend(squire.steps[4], C.world())
    eq(route.mode, 'travel', 'the Squire guide routes from Southern San d’Oria')
    ok(route.hops >= 1, 'the cave route has at least one zone transition')
    WORLD.zone, WORLD.x, WORLD.z = 193, -94, 273
    local first_marker = R.recommend(squire.steps[5], C.world())
    eq(first_marker.mode, 'here', 'the first cave marker uses the local arrow')
    eq(first_marker.distance, 0, 'the first marker arrow reaches zero distance on location')
    ok(squire.steps[6].fixed, 'the first marker interaction is a fixed manual checkpoint')
    eq(R.recommend(squire.steps[6], C.world()).distance, 0,
       'the first marker interaction remains targeted at the marker')
    local second_marker = R.recommend(squire.steps[7], C.world())
    eq(second_marker.mode, 'here', 'the second cave marker uses the local arrow')
    eq(math.floor(second_marker.distance + 0.5), 46, 'the second marker distance is measured')
    WORLD.x, WORLD.z = -139, 264
    local return_route = R.recommend(squire.steps[9], C.world())
    eq(return_route.mode, 'travel', 'the guide routes back out of Ordelles')
    ok(return_route.hops >= 1, 'the return route has at least one zone transition')
    eq(squire.steps[8].key_item, 141, 'the objective waits for Stalactite Dew')
    eq(squire.steps[10].quest.id, 19, 'the turn-in waits for server quest completion')
    story.reset()
    story.on_packet(0x056, packet_0056(0x0050, { 19 }), 48)
    ok(C.done(squire.steps[3], C.world()), 'the acceptance step observes the active quest flag')
    WORLD.key_items[141] = true
    ok(C.done(squire.steps[8], C.world()), 'the cave objective observes the awarded key item')
    story.on_packet(0x056, packet_0056(0x0090, { 19 }), 48)
    ok(C.done(squire.steps[10], C.world()), 'turn-in completes from the server quest flag')

    story.reset()
    WORLD.key_items[141] = nil
    WORLD.main_job_level = 9
    WORLD.zone, WORLD.x, WORLD.z = 230, -138.33, 65.76
    P.set_guide(squire)
    P.advance()
    eq(P.index, 1, 'the quest route waits until level 10')
    WORLD.main_job_level = 10
    P.advance()
    eq(P.index, 2, 'the route then waits for the prerequisite quest')
    story.on_packet(0x056, packet_0056(0x0090, { 10 }), 48)
    P.advance()
    eq(P.index, 3, 'the completed prerequisite unlocks the acceptance step')
    story.on_packet(0x056, packet_0056(0x0050, { 19 }), 48)
    P.advance()
    eq(P.index, 4, 'the accepted quest advances to travel')
    WORLD.zone = 193
    P.advance()
    eq(P.index, 5, 'entering Ordelles completes the zone-only travel step')
    WORLD.x, WORLD.z = -94, 273
    P.advance()
    eq(P.index, 6, 'reaching the first marker completes its waypoint')
    P.advance()
    eq(P.index, 6, 'arrival does not skip the first marker interaction')
    P.check()
    P.advance()
    eq(P.index, 7, 'the first marker interaction advances manually')
    WORLD.x, WORLD.z = -139, 264
    P.advance()
    eq(P.index, 8, 'reaching the second marker completes its waypoint')
    P.back()
    eq(P.index, 6, 'back after timer expiry restores the first-marker checkpoint')
    eq(P.advance(), 0, 'the restored marker checkpoint remains manual')
    WORLD.x, WORLD.z = -94, 273
    eq(R.recommend(P.step(), C.world()).distance, 0, 'retry arrow points back to the first marker')
    P.advance()
    eq(P.index, 6, 'returning to the first marker still waits for interaction')
    P.check()
    P.advance()
    eq(P.index, 7, 'manual retry confirmation returns to the second-marker step')
    WORLD.x, WORLD.z = -139, 264
    P.advance()
    eq(P.index, 8, 'retry reaches the second marker again')
    ok(not P.complete(), 'the guide still waits for Stalactite Dew')
    WORLD.key_items[141] = true
    P.advance()
    eq(P.index, 9, 'the key item advances the guide to the return route')
    WORLD.zone = 230
    P.advance()
    eq(P.index, 10, 'returning to San d’Oria advances to turn-in')
    story.on_packet(0x056, packet_0056(0x0090, { 10, 19 }), 48)
    P.advance()
    ok(P.complete(), 'server completion finishes the entire quest route')

    story.reset()
    P.set_guide(nil)
    WORLD.key_items[141] = nil
end

local knight = G.get("San d'Oria - A Knight's Test")
ok(knight ~= nil, 'the source-derived Paladin quest walkthrough ships')
if knight ~= nil then
    eq(#knight.errors, 0, 'the Knight quest walkthrough parses cleanly')
    eq(knight.steps[1].level, 30, 'the local LSB advanced-job level gates acceptance')
    eq(knight.steps[2].quest.id, 19, 'the previous Squire quest gates the new guide')
    eq(knight.steps[3].quest_accept.id, 29, 'the quest acceptance checks the correct flag')
    eq(knight.steps[4].key_item, 143, 'acceptance reward waits for the Book of Tasks')
    eq(knight.steps[6].key_item, 145, 'Baunise step waits for the Book of the West')
    eq(knight.steps[8].key_item, 144, 'Cahaurme step waits for the Book of the East')
    eq(knight.steps[10].key_item, 146, 'Davoi step waits for the Knight’s Soul')
    eq(knight.steps[12].quest.id, 29, 'turn-in waits for the server quest flag')

    WORLD.zone, WORLD.x, WORLD.z = 230, -138.33, 65.76
    eq(R.recommend(knight.steps[4], C.world()).mode, 'here', 'the acceptance reward stays at Balasiel')
    eq(R.recommend(knight.steps[5], C.world()).mode, 'here', 'the first NPC has a local arrow')
    eq(R.recommend(knight.steps[7], C.world()).mode, 'here', 'the second NPC has a local arrow')
    eq(R.recommend(knight.steps[9], C.world()).mode, 'travel', 'the route continues to Davoi')
    WORLD.zone = 149
    local well = R.recommend(knight.steps[10], C.world())
    eq(well.mode, 'here', 'the well marker has a local arrow in Davoi')
    eq(math.floor(well.distance + 0.5), 368, 'the Davoi well marker distance is measured')
    eq(R.recommend(knight.steps[11], C.world()).mode, 'travel', 'the guide routes back to San d’Oria')

    story.reset()
    WORLD.main_job_level = 29
    WORLD.key_items[143], WORLD.key_items[144], WORLD.key_items[145], WORLD.key_items[146] = nil, nil, nil, nil
    WORLD.zone, WORLD.x, WORLD.z = 230, -138.33, 65.76
    P.set_guide(knight)
    P.advance()
    eq(P.index, 1, 'the Paladin guide waits until level 30')
    WORLD.main_job_level = 30
    P.advance()
    eq(P.index, 2, 'the level gate advances to the Squire prerequisite')
    story.on_packet(0x056, packet_0056(0x0090, { 19 }), 48)
    P.advance()
    eq(P.index, 3, 'the completed Squire quest unlocks acceptance')
    story.on_packet(0x056, packet_0056(0x0050, { 29 }), 48)
    P.advance()
    eq(P.index, 4, 'the accepted quest advances to its reward checkpoint')
    P.advance()
    eq(P.index, 4, 'the guide waits for the Book of Tasks from the acceptance event')
    WORLD.key_items[143] = true
    P.advance()
    eq(P.index, 5, 'the Book of Tasks advances to Baunise')
    P.check()
    P.advance()
    eq(P.index, 6, 'speaking with Baunise advances to the West book objective')
    WORLD.key_items[145] = true
    P.advance()
    eq(P.index, 7, 'the West book advances to Cahaurme')
    P.check()
    P.advance()
    eq(P.index, 8, 'speaking with Cahaurme advances to the East book objective')
    WORLD.key_items[144] = true
    P.advance()
    eq(P.index, 9, 'the East book advances the guide toward Davoi')
    WORLD.zone = 149
    P.advance()
    eq(P.index, 10, 'entering Davoi advances to the Disused Well')
    WORLD.key_items[146] = true
    P.advance()
    eq(P.index, 11, 'the Knight’s Soul advances to the return route')
    WORLD.zone = 230
    P.advance()
    eq(P.index, 12, 'returning to San d’Oria advances to turn-in')
    story.on_packet(0x056, packet_0056(0x0090, { 19, 29 }), 48)
    P.advance()
    ok(P.complete(), 'the quest completion flag finishes the full Knight route')
    story.reset()
    P.set_guide(nil)
    WORLD.key_items[143], WORLD.key_items[144], WORLD.key_items[145], WORLD.key_items[146] = nil, nil, nil, nil
end

-- ---- authored classic support-job routes ---------------------------------------
-- Factual fixtures checked against pinned upstream scripts, not a running server.
do
    local qdb = require('data.quests')
    local routes = {
        { name = 'Support jobs', town = 'Selbina', quest = 24, zone = 248, x = -54, z = -44,
          npc = 'Isacio', items = { 538, 537, 539 } },
        { name = 'Support jobs - Mhaura', town = 'Mhaura', quest = 10, zone = 249, x = -49, z = 20,
          npc = 'Vera', items = { 542, 541, 540 } },
    }
    local old_current = story.quest.current.other
    local old_completed = story.quest.completed.other
    for _, route in ipairs(routes) do
        local g = G.get(route.name)
        ok(g ~= nil, route.name .. ' is registered by guides.init')
        if g then
            local accept, turnin, level, items, trades = nil, nil, nil, {}, {}
            local routeSteps = {}
            for _, step in ipairs(g.steps) do if not step.home or step.home == route.town then routeSteps[#routeSteps + 1] = step end end
            eq(#routeSteps, 10, route.town .. ' combined support route has ten steps')
            for _, s in ipairs(routeSteps) do
                if s.quest_accept then accept = s end
                if s.quest then turnin = s end
                if s.level then level = s end
                if s.item then items[#items + 1] = s end
                if s.fixed then trades[#trades + 1] = s end
                ok(s.key_item == nil, route.name .. ' does not invent a key-item reward')
            end
            eq(level and level.level, 18, route.name .. ' uses the classic configured default level')
            eq(accept and accept.quest_accept.area, 'other', route.name .. ' uses other-areas quest log')
            eq(accept and accept.quest_accept.id, route.quest, route.name .. ' acceptance id')
            eq(turnin and turnin.quest.id, route.quest, route.name .. ' completion id')
            local db = qdb.quests.other[route.quest]
            eq(db.npc, route.npc, route.name .. ' agrees with existing NPC data')
            eq(accept.zone, db.zone, route.name .. ' agrees with existing zone data')
            eq(accept.pos.x, db.x, route.name .. ' NPC horizontal x')
            eq(accept.pos.z, db.z, route.name .. ' NPC horizontal z')
            eq(#items, 3, route.name .. ' has exactly three collection objectives')
            local held = {}
            local w = { level = 17, zone = route.zone, x = route.x, z = route.z,
                        item_count = function(id) return held[id] or 0 end, story = story }
            ok(not C.done(level, w), route.name .. ' waits below level 18')
            w.level = 18
            ok(C.done(level, w), route.name .. ' level threshold completes')
            eq(C.distance(accept, w), 0, route.name .. ' waypoint reaches the sourced NPC')
            for i, item in ipairs(items) do
                eq(item.item.id, route.items[i], route.name .. ' collection/trade order item ' .. i)
                eq(item.item.count, 1, route.name .. ' asks for one item ' .. i)
                ok(not C.done(item, w), route.name .. ' missing item waits ' .. i)
                held[item.item.id] = 1
                ok(C.done(item, w), route.name .. ' inventory confirms collection ' .. i)
            end
            eq(#trades, 2, route.name .. ' intermediate trades require manual confirmation')
            for _, trade in ipairs(trades) do
                ok(not C.done(trade, w), route.name .. ' proximity does not complete a trade')
            end
            story.on_packet(0x056, packet_0056(0x0070, {}), 48)
            story.on_packet(0x056, packet_0056(0x00B0, {}), 48)
            ok(not C.done(accept, w), route.name .. ' waits for quest acceptance')
            story.on_packet(0x056, packet_0056(0x0070, { route.quest }), 48)
            ok(C.done(accept, w), route.name .. ' accepted quest ticks acceptance')
            ok(not C.done(turnin, w), route.name .. ' acceptance alone never ticks completion')
            story.on_packet(0x056, packet_0056(0x00B0, { route.quest }), 48)
            ok(C.done(turnin, w), route.name .. ' completed quest ticks final turn-in')
        end
    end
    local support = G.get('Support jobs')
    eq(G.guides['Support jobs - Mhaura'], nil, 'support-job alternatives share one menu entry')
    P.set_guide(support, { index = 7, checked = { [6] = true } }, 'Support jobs - Mhaura')
    eq(P.starting_location, 'Mhaura', 'legacy Mhaura progress retains its town')
    eq(P.step().home, 'Mhaura', 'legacy Mhaura step maps into its combined branch')
    eq(P.step().text, 'Trade one Wild Rabbit Tail to Vera, then finish the dialogue.', 'legacy Mhaura trade cursor is preserved')
    local savedSupport = P.save_state()
    P.set_guide(support, savedSupport, 'Support jobs')
    eq(P.step().text, 'Trade one Wild Rabbit Tail to Vera, then finish the dialogue.', 'new support progress is not migrated twice')
    P.set_guide(support, { index = 10 }, 'Support jobs')
    eq(P.index, #support.steps, 'old Selbina final step maps to shared ending')
    story.quest.current.other = old_current
    story.quest.completed.other = old_completed
    local starter_text = {}
    for _, s in ipairs(G.get('Starting out').steps) do starter_text[#starter_text + 1] = s.text end
    local starter = table.concat(starter_text, '\n')
    ok(not starter:find('At 10 you can take the airship pass', 1, true), 'starter does not promise level-10 airship access')
    ok(not starter:find("Adventurer's Certificate", 1, true), 'starter does not invent a guard certificate reward')
end

-- ---- a whole guide, played through ---------------------------------------------
-- Walk the "Starting out" guide the way a player would and check it ends.
P.set_guide(G.get('Starting out'))
WORLD.main_job_level = 1
local guard = 0
while not P.complete() and guard < 100 do
    guard = guard + 1
    local step = P.step()
    if step == nil then break end
    if step.level ~= nil then
        WORLD.main_job_level = step.level        -- the player levels up
    else
        P.check()                                 -- the player ticks it off
    end
    P.advance()
end
ok(P.complete(), 'the starting guide can be played to the end')
ok(guard < 100, 'and it terminates')

-- ---- the arrow's rotation sense -------------------------------------------------
-- The bug this catches: the screen's y grows downward, so drawing the bearing
-- unnegated mirrors the arrow — left targets get a right-pointing arrow.
do
    local lines = {}
    -- The arrow draws inside its own ImGui window (draggable, HXUI-style), so the stub
    -- needs the window calls too.  The window sits at (0,0) in the stub, so drawn
    -- coordinates are the tip/corner positions the test compares.
    for _, f in ipairs({ 'ImGuiWindowFlags_NoDecoration', 'ImGuiWindowFlags_NoBackground',
        'ImGuiWindowFlags_NoFocusOnAppearing', 'ImGuiWindowFlags_NoNav',
        'ImGuiWindowFlags_NoBringToFrontOnFocus', 'ImGuiWindowFlags_NoMove',
        'ImGuiCond_FirstUseEver' }) do _G[f] = _G[f] or 1 end
    local dl = { AddLine = function(_, a, b, _, width)
        if width == 3 then lines[#lines + 1] = { a[1], a[2], b[1], b[2] } end
    end }
    _G.imgui = {
        GetForegroundDrawList = function() return dl end,
        GetWindowDrawList = function() return dl end,
        SetNextWindowPos = function() end,
        SetNextWindowSize = function() end,
        Begin = function() return true end,
        End = function() end,
        GetWindowPos = function() return 0, 0 end,
        IsWindowHovered = function() return false end,
        IsMouseDown = function() return false end,
    }
    local A = require('ui.arrow')
    local function tip(bearing)
        lines = {}
        A.pos_x, A.pos_y = 100, 100; A.scale = 1.0   -- line width 3 marks the coloured pass
        A.draw(bearing, 10, nil, nil)
        assert(#lines == 4, 'arrow drew 4 coloured lines (' .. tostring(A.last_error) .. ')')
        -- lines: tip->left, tip->right, left->base, right->base.  Return the tip relative
        -- to the base notch, so the test does not care where the window put the arrow.
        return lines[1][1] - lines[3][3], lines[1][2] - lines[3][4]
    end
    local dx, dy = tip(0)
    ok(math.abs(dx) < 1 and dy < 0, 'bearing 0 points up the screen')
    dx, dy = tip(math.pi / 2)
    ok(dx < 0 and math.abs(dy) < 1, 'a bearing to the left points left on screen')
    dx, dy = tip(-math.pi / 2)
    ok(dx > 0, 'a bearing to the right points right on screen')
    _G.imgui = nil
end

-- ---- the generated quest database ----------------------------------------------
local QDB = require('data.quests')
do
    local total, positioned, bad_zone, bad_id = 0, 0, 0, 0
    for area, quests in pairs(QDB.quests) do
        for id, q in pairs(quests) do
            total = total + 1
            if q.zone ~= nil then
                positioned = positioned + 1
                if zones.name[q.zone] == nil then bad_zone = bad_zone + 1 end
            end
            -- The quest log is 256 flags per area; an id outside that could never be read
            -- back out of packet 0x056, so it would be a silently dead step.
            if id < 0 or id > 255 then bad_id = bad_id + 1 end
        end
    end
    ok(total >= 500, ('the quest database has every quest (%d)'):format(total))
    ok(positioned >= 300, ('most quests carry coordinates (%d)'):format(positioned))
    eq(bad_zone, 0, 'every quest zone is a real zone')
    eq(bad_id, 0, 'every quest id fits the 256-flag log')
    local knights = QDB.get('sandoria', 29)
    ok(knights ~= nil and knights.zone == 230, "A Knight's Test is taken in Southern San d'Oria")

    -- The name the client shows, never the header's label around it.
    local bad_npc = {}
    for _, quests in pairs(QDB.quests) do
        for _, q in pairs(quests) do
            local n = q.npc
            if n ~= nil and (n:find('%(') or n:find('_') or n:find(',') or n:find('\\', 1, true)) then
                bad_npc[#bad_npc + 1] = n
            end
        end
    end
    eq(#bad_npc, 0, 'every quest NPC is a shown name: ' .. table.concat(bad_npc, ', '))
    local kuftal = QDB.get('outlands', 195)
    ok(kuftal.npc == 'Datta' and kuftal.zone == 247, 'The Kuftal Tour starts with Datta in Rabao')
    eq(QDB.get('abyssea', 87).x, -848.1, "Altepa Dominion Op #01 is at Nanaa Mihgo's camp")
end

-- ---- generated guides ------------------------------------------------------------
do
    local generated = 0
    for _, g in ipairs(G.list()) do
        if g.name:find('every quest') then
            generated = generated + 1
            eq(#g.errors, 0, ('%s parses cleanly'):format(g.name))
            local seen, dup = {}, 0
            for _, s in ipairs(g.steps) do
                local key = s.quest and (s.quest.area .. s.quest.id) or s.text
                if seen[key] then dup = dup + 1 end
                seen[key] = true
            end
            eq(dup, 0, ('%s lists each quest once'):format(g.name))
        end
    end
    ok(generated >= 10, ('a guide per quest area (%d)'):format(generated))

    -- prerequisites come first
    local sd = G.get("San d'Oria - every quest")
    local pos = {}
    for i, s in ipairs(sd.steps) do if s.quest then pos[s.quest.id] = i end end
    local violations = 0
    for id, i in pairs(pos) do
        local q = QDB.get('sandoria', id)
        if q ~= nil and q.prereq ~= nil and q.prereq[1] == 'sandoria' then
            local pi = pos[q.prereq[2]]
            if pi ~= nil and pi > i then violations = violations + 1 end
        end
    end
    eq(violations, 0, 'a quest never comes before the quest it requires')

    local QuestData = require('data.quests')
    eq(QuestData.canonical_area('aht_urhgan'), 'ahturhgan', 'Aht Urhgan log aliases normalize')
    eq(QuestData.canonical_area('other_areas'), 'other', 'Other Areas log aliases normalize')
    eq(QuestData.canonical_area('crystal_war'), 'wotg', 'Crystal War log aliases normalize')
    ok(QuestData.get('aht_urhgan', 29) ~= nil, 'Aht Urhgan quest ids resolve through the alias')
    ok(QuestData.get('crystal_war', 12) ~= nil, 'Crystal War prerequisite ids resolve')

    local function quest_positions(guide)
        local positions = {}
        for i, step in ipairs(guide.steps) do
            if step.quest then positions[step.quest.area .. ':' .. step.quest.id] = i end
        end
        return positions
    end

    local aht = quest_positions(G.get('Aht Urhgan - every quest'))
    ok(aht['ahturhgan:21'] < aht['ahturhgan:22']
        and aht['ahturhgan:22'] < aht['ahturhgan:23'],
        'Aht Urhgan quest chains follow their prerequisites')
    local aht_guide = G.get('Aht Urhgan - every quest')
    local missing_parent_note
    for i, step in ipairs(aht_guide.steps) do
        if step.kind == 'note' and step.text:find('ahturhgan/28', 1, true) then
            missing_parent_note = i
            break
        end
    end
    ok(missing_parent_note ~= nil and missing_parent_note < aht['ahturhgan:29'],
        'a missing same-area prerequisite is surfaced before its quest')
    local crystal = quest_positions(G.get('Crystal War - every quest'))
    ok(crystal['wotg:12'] < crystal['wotg:13'],
        'Crystal War quest chains follow their aliased prerequisites')

    local outlands = quest_positions(G.get('Outlands - every quest'))
    ok(outlands['bastok:45'] ~= nil and outlands['bastok:45'] < outlands['outlands:195'],
        'Outlands guides surface an external Bastok prerequisite first')
    ok(outlands['windurst:7'] ~= nil and outlands['windurst:7'] < outlands['outlands:3'],
        'Outlands guides surface an external Windurst prerequisite first')
end

-- ---- the generated mission database ---------------------------------------------
do
    local MDB = require('data.missions')
    local total, bad_zone, bad_npc = 0, 0, {}
    for _, missions in pairs(MDB.missions) do
        for _, m in pairs(missions) do
            total = total + 1
            if m.zone ~= nil and zones.name[m.zone] == nil then bad_zone = bad_zone + 1 end
            -- The name the client shows, never a label around it: no step number ("1. Enter
            -- Lower Delkfutt"), no bracketed internal name ("Granite Door (_4fx)"), no
            -- server-side name ("Sluice_Gate_6"), no escaped quote ("Tales\' Beginning").
            local n = m.npc
            if n ~= nil and (n:find('^%d+%.') or n:find('%(') or n:find('_') or n:find('\\', 1, true)) then
                bad_npc[#bad_npc + 1] = n
            end
        end
    end
    ok(total >= 400, ('the mission database has every storyline (%d)'):format(total))
    eq(bad_zone, 0, 'every mission zone is a real zone')
    eq(#bad_npc, 0, 'every mission NPC is a shown name: ' .. table.concat(bad_npc, ', '))
    local rites = MDB.get('cop', 110)
    ok(rites.npc == nil and rites.place == 'Enter Lower Delkfutt',
       'The Rites of Life starts at a place, not an NPC called "1. Enter Lower Delkfutt"')
    eq(MDB.get('adoulin', 66).x, -215.4, "Soul Siphon's Hollowed Pathway is where the server spawns it")

    -- The ids the retired hand-written guide got wrong.  This is the regression.
    local first = MDB.get('sandoria', 0)
    ok(first ~= nil and first.name:find('Orcish Scouts') ~= nil,
       "San d'Oria mission 0 is Smash the Orcish Scouts, not mission 1")
    ok(MDB.get('sandoria', 1).name:find('Bat Hunt') ~= nil, "mission 1 is Bat Hunt")

    local g = G.get("San d'Oria missions - in order")
    ok(g ~= nil, 'the storyline guide is registered')
    eq(#g.errors, 0, 'and parses cleanly')
    eq(g.steps[1].mission.id, 0, 'its first step waits on mission 0')
    for i = 2, #g.steps do
        ok(g.steps[i].mission.id > g.steps[i - 1].mission.id, 'missions are in order')
    end

    -- Only an NPC is announced as "Starts with": the audit reads that phrase back as a name.
    local cop = G.get('Chains of Promathia - in order')
    local rites_step = cop.steps[1]
    eq(rites_step.note, 'First stop: Enter Lower Delkfutt.', 'a place is announced as a place')
    eq(G.npc_of(rites_step, rites), nil, 'and is not taken for an NPC')
end

-- ---- loot, gear and notorious monsters ------------------------------------------
do
    local NM = require('data.nm')
    local GEAR = require('data.gear')
    local VEND = require('data.vendors')
    local L = require('core.lookup')

    ok(#NM.list >= 300, ('the notorious-monster list is populated (%d)'):format(#NM.list))
    local placed, bad_zone, placeholder = 0, 0, 0
    for _, n in ipairs(NM.list) do
        if zones.name[n.zone] == nil then bad_zone = bad_zone + 1 end
        if n.x ~= nil then
            placed = placed + 1
            -- (1,1,1) is LandSandBoat's "a script decides where this spawns". Writing it out
            -- would aim the arrow at the middle of nowhere with full confidence.
            if math.abs(n.x) <= 1 and math.abs(n.z) <= 1 then placeholder = placeholder + 1 end
        end
    end
    eq(bad_zone, 0, 'every notorious monster is in a real zone')
    eq(placeholder, 0, 'no placeholder coordinates survive into the data')
    ok(placed >= 100, ('%d of them have a real spawn point'):format(placed))

    local gear_count = 0
    for id, e in pairs(GEAR.items) do
        gear_count = gear_count + 1
        ok(type(e[1]) == 'string' and e[1] ~= '', 'gear entry has a name')
        break
    end
    for _ in pairs(GEAR.items) do gear_count = gear_count + 1 end
    ok(gear_count >= 400, ('gear with a findable source (%d)'):format(gear_count))

    local sold = 0
    for _ in pairs(VEND.sold_by) do sold = sold + 1 end
    ok(sold >= 1000, ('items somebody sells (%d)'):format(sold))

    -- a real lookup, end to end
    local found = L.find_item('bronze')
    ok(#found > 0, 'searching for bronze gear finds something')
    ok(#found[1].sources > 0, 'and it says where to get it')
    ok(found[1].sources[1].zone ~= nil, 'with a zone the router can use')

    -- jobs are a bitmask; a WAR-only piece must not show up for a WHM
    local war = GEAR.for_slot('body', 99, 1)
    ok(#war > 0, 'body armour exists for a warrior')
    ok(GEAR.fits_job({ 'Fighters Mask', 56, 1, 'head' }, 1), 'job mask 1 (bit 0) is Warrior')
    ok(not GEAR.fits_job({ 'Fighters Mask', 56, 1, 'head' }, 2), 'and not Monk')
    ok(GEAR.fits_job({ 'Temple Crown', 56, 2, 'head' }, 2), 'job mask 2 is Monk')

    -- tracking turns a lookup into an ordinary one-step guide
    local before = P.guide
    L.track(P, { title = 'Test target', text = 'Go here', zone = 230, x = 10, z = -20 })
    eq(P.step().zone, 230, 'tracking builds a step in the right zone')
    eq(P.step().pos.x, 10, 'with the right coordinates')
    eq(P.step().kind, 'run', 'as a run-to step')
    P.set_guide(before or G.get('Starting out'))
end

-- ---- the notorious-monster guides -----------------------------------------------
do
    local nm_guides = 0
    for _, g in ipairs(G.list()) do
        if g.name:find('Notorious monsters') then
            nm_guides = nm_guides + 1
            eq(#g.errors, 0, ('%s parses cleanly'):format(g.name))
            for _, st in ipairs(g.steps) do
                ok(st.pos ~= nil, 'every notorious-monster step has a place to point at')
                ok(st.fixed == true, 'and never completes itself')
            end
        end
    end
    ok(nm_guides >= 5, ('a hunting guide per zone that has notorious monsters (%d)'):format(nm_guides))
end

-- ---- the window fits the screen it is drawn on ---------------------------------
do
    local Win = require('ui.window')
    Win.set_viewport(640, 480)
    local w, h, rows = Win.fit()
    ok(w <= 640 * 0.4, ('at 640x480 the window is a third of the width, not half (%d)'):format(w))
    -- Taller than a third on a short screen, on purpose: below ~190px the window clipped its
    -- own buttons, and with no working mouse there is no way to scroll down to them.
    ok(h >= 190 and h <= 480 * 0.5, ('tall enough to keep the buttons above the fold (%d)'):format(h))
    ok(rows >= 0, 'even if that leaves no room for the upcoming list')
    ok(Win.refit == true, 'a resolution change re-fits once')

    Win.set_viewport(1920, 1080)
    local w2, h2, rows2 = Win.fit()
    ok(w2 > w and w2 <= 420, ('at 1920x1080 it grows, but stays capped (%d)'):format(w2))
    ok(rows2 >= rows, 'and shows at least as many upcoming steps')
    ok(rows2 >= 1, 'a full-size screen always has room for what is next')

    -- an absurd viewport must not produce an absurd window
    Win.set_viewport(320, 200)
    local w3, h3 = Win.fit()
    ok(w3 >= 240 and h3 >= 150, 'a tiny screen still gets a readable window')
end

-- ---- moving the arrow ------------------------------------------------------------
do
    local A = require('ui.arrow')
    A.set_viewport(1920, 1080)
    local x, y = A.move(0.5, 0.28)
    eq(A.pos_x, 960, 'the default arrow sits across the middle')
    ok(math.abs(A.pos_y - 302.4) < 1, 'and a bit above centre')

    A.move(0.25, 0.75)
    eq(A.pos_x, 480, 'moving it left puts it at a quarter of the width')
    eq(A.pos_y, 810, 'and three quarters down')

    -- the position is a fraction, so a resolution change keeps it in the same *place*
    A.set_viewport(640, 480)
    eq(A.pos_x, 160, 'at 640x480 it is still a quarter across')
    eq(A.pos_y, 360, 'and still three quarters down')

    -- and it can never be pushed off the screen
    A.move(-5, 12)
    ok(A.pos_x > 0 and A.pos_x < 640, 'an absurd position is clamped onto the screen')
    ok(A.pos_y > 0 and A.pos_y < 480, 'in both directions')
    A.move(0.5, 0.28)
end

-- The gil itinerary combines leveling, quests, materials and NM opportunities.
do
    require('guides.solo_horizon')
    local merged = G.guides['Solo Guide - HorizonXI']
    ok(merged ~= nil, 'one combined Horizon gil guide registers')
    eq(G.get(nil), nil, 'missing saved guide does not match an absent alias')
    eq(G.guides['Solo EXP - HorizonXI'], nil, 'separate EXP menu entry removed')
    eq(G.guides['Solo Gil - HorizonXI'], nil, 'separate gil menu entry removed')
    eq(G.get('Solo Gil - HorizonXI'), merged, 'saved gil guide name resolves to unified route')
    eq(G.get('Solo EXP - HorizonXI'), merged, 'saved EXP guide name resolves to unified route')
    local starts, quests, nms = {}, {}, 0
    for _, step in ipairs(merged.steps) do
        if step.starting_location then starts[#starts + 1] = step.starting_location end
        ok(step.note and step.note:find('Starting location:', 1, true), 'gil step identifies applicable starting cities')
        ok(step.source and step.source:find('https://horizonffxi.wiki/', 1, true) == 1, 'gil step has a reviewed Horizon wiki source')
        ok(not step.note:find('may differ', 1, true) and not step.note:find('Standard LSB', 1, true), 'gil step uses Horizon instructions instead of generic caveats')
        if step.quest then quests[step.quest.area .. ',' .. step.quest.id] = true end
        if step.text:find('Optional NM', 1, true) then nms = nms + 1 end
        if step.level then
            ok(step.exp_goal and step.gil_goal, 'every leveling camp has separate EXP and gil goals')
        end
    end
    eq(table.concat(starts, ';'), "Windurst;San d'Oria;Bastok", 'three starting-city entry points')
    ok(quests['sandoria,81'] and quests['sandoria,78'], 'San d Oria detours keep correct quest IDs')
    ok(nms >= 6, 'itinerary includes several named NM opportunities')
    for _, nation in ipairs(starts) do
        local covered = {}
        for _, step in ipairs(merged.steps) do
            if (not step.home or step.home == nation) and step.level then
                local lo, hi = step.text:match('Levels (%d+)%-(%d+):')
                ok(lo ~= nil and hi ~= nil, 'level band is explicit')
                for level = tonumber(lo), tonumber(hi) do
                    ok(not covered[level], 'selected city route does not repeat a level band')
                    covered[level] = true
                end
            end
        end
        for level = 1, 75 do ok(covered[level], 'selected city route covers level ' .. level) end
    end
    P.set_guide(merged)
    P.starting_location = 'Windurst'
    local lastWindurst
    for i, step in ipairs(merged.steps) do
        if step.home == 'Windurst' and step.text:find('Creepy Crawlies', 1, true) then lastWindurst = i end
    end
    P.index = lastWindurst
    P.check(); P.advance({})
    ok(not merged.steps[P.index].home, 'finishing Windurst starter branch skips other city branches')
    eq(P.save_state().starting_location, 'Windurst', 'selected origin persists through shared camps')
    eq(P.route_count(), 30, 'displayed route count excludes other city branches')
    local archived = assert(io.open('archive/2026-10-30/solo_gil-quest-only.lua'))
    local oldText = archived:read('*a'); archived:close()
    local oldCount = 0
    for _ in oldText:gmatch('|Q|') do oldCount = oldCount + 1 end
    eq(oldCount, 61, 'superseded quest-only route remains archived with every quest target')
end

print(('\n%d passed, %d failed'):format(pass, fail))
os.exit(fail == 0 and 0 or 1)
