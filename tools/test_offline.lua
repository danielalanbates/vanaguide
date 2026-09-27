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
eq(steps[3].item.count, 3, 'item count')
ok(select(2, G.parse('q nonsense|Z|230|'))[1] ~= nil, 'bad verb reported')

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
story.on_packet(0x056, packet_0056(0x0090, { 5, 12 }), 48)     -- completed, San d'Oria
ok(story.quest_done('sandoria', 5), 'quest flag 5 read from packet')
ok(story.quest_done('sandoria', 12), 'quest flag 12 read from packet')
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
ok(graph.learn(230, 299), 'a new zone line is learned')
ok(not graph.learn(230, 299), 'and only learned once')
ok(graph.route(230, 299) ~= nil, 'learning opens the route')

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
ok(shipped >= 3, 'at least three guides ship')

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
end

-- ---- the generated mission database ---------------------------------------------
do
    local MDB = require('data.missions')
    local total, bad_zone = 0, 0
    for _, missions in pairs(MDB.missions) do
        for _, m in pairs(missions) do
            total = total + 1
            if m.zone ~= nil and zones.name[m.zone] == nil then bad_zone = bad_zone + 1 end
        end
    end
    ok(total >= 400, ('the mission database has every storyline (%d)'):format(total))
    eq(bad_zone, 0, 'every mission zone is a real zone')

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

print(('\n%d passed, %d failed'):format(pass, fail))
os.exit(fail == 0 and 0 or 1)
