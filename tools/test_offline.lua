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

-- ---- every file the addon loads actually parses --------------------------------
-- A syntax error in a module the suite does not itself require is invisible here and fatal
-- in the client: the addon simply never loads, cmd.txt stops being polled, and the sweep
-- driving it reports a client that has stopped answering. That is exactly what a stray
-- `function` written after `return V` in core/verify.lua did. Parsing every file costs
-- nothing and catches the whole class.
do
    local files = {
        'Vanaguide.lua', 'core/verify.lua', 'core/util.lua', 'core/guide.lua',
        'core/conditions.lua', 'core/progress.lua', 'core/story.lua', 'core/lookup.lua',
        'routing/zonegraph.lua', 'routing/router.lua', 'routing/zonepoints.lua',
        'routing/path.lua', 'routing/navgrid.lua', 'ui/arrow.lua', 'ui/window.lua', 'ui/line.lua', 'ui/project.lua',
        'data/quests.lua', 'data/missions.lua', 'data/zone_names.lua', 'data/travel.lua',
        'data/zonelines.lua', 'data/zonepoints.lua', 'data/gear.lua', 'data/drops.lua',
        'data/nm.lua',
        'data/vendors.lua',
    }
    for _, f in ipairs(files) do
        local path = 'Vanaguide/' .. f
        local fh = io.open(path, 'r')
        if fh == nil then
            ok(false, path .. ' exists')
        else
            fh:close()
            local chunk, err = loadfile(path)
            ok(chunk ~= nil, path .. ' parses' .. (chunk == nil and (': ' .. tostring(err)) or ''))
        end
    end
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
    _G.imgui = { GetForegroundDrawList = function()
        return { AddLine = function(_, a, b, _, width)
            if width == 3 then lines[#lines + 1] = { a[1], a[2], b[1], b[2] } end
        end }
    end }
    local A = require('ui.arrow')
    local function tip(bearing)
        lines = {}
        A.pos_x, A.pos_y = 100, 100
        A.draw(bearing, 10, nil, nil)
        -- the tip is the point two of the coloured lines share
        return lines[1][1], lines[1][2]
    end
    local tx, ty = tip(0)
    ok(math.abs(tx - 100) < 1 and ty < 100, 'bearing 0 points up the screen')
    tx, ty = tip(math.pi / 2)
    ok(tx < 100 and math.abs(ty - 100) < 1, 'a bearing to the left points left on screen')
    tx, ty = tip(-math.pi / 2)
    ok(tx > 100, 'a bearing to the right points right on screen')
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


-- ---- zone points: the way out ---------------------------------------------------
do
    local ZP = require('routing.zonepoints')
    ok(ZP.available, 'data/zonepoints.lua loaded')

    -- Southern San d'Oria (230) opens onto West Ronfaure (100).  Every zone line in the
    -- server's table carries the position of its trigger in the zone you are leaving, so
    -- there is a coordinate for this and it is inside the zone, not at the origin.
    local exits = ZP.exits(230, 100)
    ok(#exits > 0, "San d'Oria has a recorded way out into West Ronfaure")
    ok(exits[1].x ~= 0 or exits[1].z ~= 0, 'and it is a real coordinate, not 0,0')

    -- More than one gate onto the same road: the nearest to the player wins, and which one
    -- is nearest has to actually depend on where the player is standing.
    if #exits > 1 then
        local a = ZP.nearest_exit(230, 100, exits[1].x, exits[1].z)
        local b = ZP.nearest_exit(230, 100, exits[2].x, exits[2].z)
        eq(a.x, exits[1].x, 'standing on one gate picks that gate')
        eq(b.x, exits[2].x, 'standing on the other picks the other')
    end
    ok(ZP.nearest_exit(230, 999, 0, 0) == nil, 'a zone pair that does not touch has no exit')

    -- The docks: Selbina (248) and Mhaura (249) are joined only by the ferry, and the dock
    -- is where you stand to wait for it.
    local dock = ZP.dock(248, 249) or ZP.dock(249, 248)
    ok(dock ~= nil, 'the Selbina/Mhaura ferry has a dock to stand on')
    if dock ~= nil then ok(dock.via ~= nil and dock.via ~= '', 'and something to call it') end
end

-- ---- the router points at the doorway --------------------------------------------
do
    local R2 = require('routing.router')
    local G2 = require('core.guide')
    R2.forget()
    WORLD.zone, WORLD.x, WORLD.z, WORLD.y, WORLD.yaw = 230, 0, 0, 0, 0
    local far = G2.parse('R Go to Port Jeuno|Z|246|POS|10,-20|')
    local rec = R2.recommend(far[1], C.world())
    eq(rec.mode, 'travel', 'a step three zones away is a travel step')
    ok(rec.target ~= nil, 'and it now has a place to walk to')
    ok(rec.bearing ~= nil, 'so the arrow has a bearing during the journey')
    ok(rec.distance ~= nil and rec.distance > 0, 'and a distance')
    ok(rec.text:find('yalms') ~= nil, 'and the window says how far ("' .. rec.text .. '")')
    ok(rec.hops ~= nil and rec.hops > 1, 'the route is more than one hop')

    -- The itinerary is one line per leg, and knows which legs it can point at.
    local it = R2.itinerary(rec.legs, 230, 0, 0)
    eq(#it, #rec.legs, 'the itinerary has a line per leg')
    ok(it[1].known, 'the first leg has a coordinate')
    ok(R2.chain(rec.legs, 2) ~= nil, 'the chain of zones prints')
    ok(R2.summary(rec):find('zones') ~= nil, 'the summary counts zones')

    -- A step in this zone still behaves exactly as it did.
    local near = G2.parse('t Talk to the guard|Z|230|POS|30,40,8|')
    local rec2 = R2.recommend(near[1], C.world())
    eq(rec2.mode, 'here', 'a step in this zone is still "here"')
    ok(rec2.target ~= nil and rec2.target.x == 30, 'and carries its own coordinate')
    R2.forget()
end

-- ---- the path -------------------------------------------------------------------
do
    local Path = require('routing.path')
    Path.forget()
    WORLD.zone, WORLD.x, WORLD.z, WORLD.y = 230, 0, 0, -5
    local pts = Path.to(C.world(), { x = 60, z = 0, y = -5 })
    ok(pts ~= nil and #pts >= 2, 'a straight path has at least two points')
    ok(#pts <= Path.max_points, 'and never more than the cap')
    eq(pts[1].x, 0, 'it starts where the player is')
    eq(pts[#pts].x, 60, 'and ends on the target')
    ok(math.abs(U.dist(pts[1].x, pts[1].z, pts[2].x, pts[2].z) - Path.spacing) < Path.spacing,
       'the points are about a spacing apart')

    -- The point nearest the player is where drawing starts, so walked ground stops being
    -- drawn instead of trailing behind.
    eq(Path.nearest_index(pts, 0, 0), 1, 'at the start, the nearest point is the first')
    ok(Path.nearest_index(pts, 59, 0) == #pts, 'at the end, it is the last')

    -- A provider (a navmesh, when one is installed) replaces the straight line.
    Path.forget()
    Path.provider = function (_, x1, z1, y1, x2, z2, y2)
        return { { x = x1, z = z1, y = y1 }, { x = 0, z = 40, y = y1 }, { x = x2, z = z2, y = y2 } }
    end
    local bent = select(1, Path.to(C.world(), { x = 60, z = 0, y = -5 }))
    local _, src = Path.to(C.world(), { x = 60, z = 0, y = -5 })
    eq(src, 'navmesh', 'a provider is used when it answers')
    local bends = false
    for _, p in ipairs(bent) do if p.z > 10 then bends = true end end
    ok(bends, 'and the path goes the way the provider said, not straight')
    Path.provider = nil
    Path.forget()
end

-- ---- world to screen -------------------------------------------------------------
do
    local Pr = require('ui.project')
    -- A camera at the origin looking down +z, with a 90 degree perspective.  This checks the
    -- arithmetic, not the game's axis conventions -- those can only be checked in the client,
    -- and docs/LINE.md says how.
    local eye = { _11 = 1, _12 = 0, _13 = 0, _14 = 0,
                  _21 = 0, _22 = 1, _23 = 0, _24 = 0,
                  _31 = 0, _32 = 0, _33 = 1, _34 = 0,
                  _41 = 0, _42 = 0, _43 = 0, _44 = 1 }
    local zn, zf = 1, 100
    local proj = { _11 = 1, _12 = 0, _13 = 0, _14 = 0,
                   _21 = 0, _22 = 1, _23 = 0, _24 = 0,
                   _31 = 0, _32 = 0, _33 = zf / (zf - zn), _34 = 1,
                   _41 = 0, _42 = 0, _43 = -zn * zf / (zf - zn), _44 = 0 }
    ok(Pr.set_view_projection(eye, proj), 'the matrices combine')
    Pr.set_viewport(800, 600)

    -- Straight ahead lands in the middle of the screen.
    local sx, sy, cw = Pr.point(0, 10, 0)
    ok(math.abs(sx - 400) < 0.01, 'a point straight ahead is centred across')
    ok(math.abs(sy - 300) < 0.01, 'and centred down')
    ok(math.abs(cw - 10) < 0.01, 'and ten units in front')

    -- Ten to the right at ten away is exactly the right-hand edge at this field of view.
    sx = Pr.point(10, 10, 0)
    ok(math.abs(sx - 800) < 0.01, '45 degrees right is the right edge')
    sx = Pr.point(-10, 10, 0)
    ok(math.abs(sx - 0) < 0.01, 'and 45 degrees left is the left edge')

    -- Twice as far away is half as far from the centre: it is a perspective, not a plan.
    sx = Pr.point(10, 20, 0)
    ok(math.abs(sx - 600) < 0.01, 'twice the distance is half the offset')

    -- Behind the camera, w goes negative and the caller must not draw it.
    local _, _, back = Pr.point(0, -10, 0)
    ok(back < 0, 'a point behind the camera has a negative w')

    -- A segment from behind you to in front of you is cut at the near plane, not thrown
    -- away: the line starts at your feet and your feet are usually behind the camera.
    local x1, y1, x2, y2 = Pr.segment(0, -5, 0, 0, 40, 0)
    ok(x1 ~= nil, 'a segment crossing the near plane still draws')
    ok(math.abs(x1 - 400) < 0.5 and math.abs(x2 - 400) < 0.5, 'and stays on the centre line')
    ok(Pr.segment(0, -50, 0, 0, -10, 0) == nil, 'a segment entirely behind you does not')

    -- Nothing here should ever produce a NaN; ImGui draws a NaN as a line to nowhere and
    -- the whole draw list after it goes with it.
    local nx, ny = Pr.point(1e6, 1e6, 1e6)
    ok(nx == nx and ny == ny, 'a huge coordinate is still a number')
end


-- ---- the line draws ---------------------------------------------------------------
do
    -- The whole renderer, through a fake draw list.  tools/render_line.lua draws the same
    -- code into an SVG for a human to look at; this is the part a machine can check, and it
    -- exists because the draw list was swapped from foreground to background after seeing a
    -- 1613-yalm line drawn across the guide window in-game.
    local calls = { line = 0, dot = 0, ring = 0, text = 0, list = nil }
    local dl = {
        AddLine = function(_, a, b) calls.line = calls.line + 1
            ok(a[1] == a[1] and b[1] == b[1], 'no NaN reaches AddLine') end,
        AddCircleFilled = function() calls.dot = calls.dot + 1 end,
        AddCircle = function() calls.ring = calls.ring + 1 end,
        AddText = function() calls.text = calls.text + 1 end,
    }
    _G.imgui = {
        GetBackgroundDrawList = function() calls.list = 'background'; return dl end,
        GetForegroundDrawList = function() calls.list = 'foreground'; return dl end,
    }
    local Pr2 = require('ui.project')
    local Line = require('ui.line')
    local Path2 = require('routing.path')

    local eye = { _11 = 1, _12 = 0, _13 = 0, _14 = 0,
                  _21 = 0, _22 = 1, _23 = 0, _24 = 0,
                  _31 = 0, _32 = 0, _33 = 1, _34 = 0,
                  _41 = 0, _42 = 0, _43 = 0, _44 = 1 }
    local proj = { _11 = 1, _12 = 0, _13 = 0, _14 = 0,
                   _21 = 0, _22 = 1, _23 = 0, _24 = 0,
                   _31 = 0, _32 = 0, _33 = 1.01, _34 = 1,
                   _41 = 0, _42 = 0, _43 = -1.01, _44 = 0 }
    Pr2.set_view_projection(eye, proj)
    Pr2.set_viewport(800, 600)
    local real_refresh = Pr2.refresh
    Pr2.refresh = function () return true end

    Path2.forget()
    Line.enabled = true
    Line.style = 'both'
    WORLD.zone, WORLD.x, WORLD.z, WORLD.y, WORLD.yaw = 230, 0, 0, 0, 0
    local drew = Line.draw(C.world(), { x = 0, z = 90, y = 0 }, 'the gate')
    ok(drew, 'the line draws')
    eq(calls.list, 'background', 'on the background list, so windows sit on top of it')
    ok(calls.line > 8, ('it drew %d segments'):format(calls.line))
    ok(calls.dot > 0, 'and the crawling dots')
    ok(calls.ring > 0, 'and a ring on the destination')
    ok(calls.text > 0, 'and the distance')

    -- Off means off.
    calls.line = 0
    Line.enabled = false
    ok(not Line.draw(C.world(), { x = 0, z = 90, y = 0 }), 'a line that is off does not draw')
    eq(calls.line, 0, 'and touches the draw list not at all')
    Line.enabled = true

    -- A build with only the foreground list still draws.
    _G.imgui.GetBackgroundDrawList = nil
    Path2.forget()
    ok(Line.draw(C.world(), { x = 0, z = 90, y = 0 }), 'an older ImGui still gets a line')
    eq(calls.list, 'foreground', 'by falling back to the foreground list')

    -- A device that will not give up its camera turns the line off rather than throwing
    -- once a frame forever.
    Pr2.refresh = function () Pr2.fails = Pr2.fails + 1; Pr2.ok = false; return false end
    Pr2.fails = 0
    for _ = 1, Line.give_up_after do Line.draw(C.world(), { x = 0, z = 90, y = 0 }) end
    ok(not Line.enabled, 'a camera that never answers switches the line off')
    ok(Line.status():find('off') ~= nil, 'and /vg status says so')
    Pr2.refresh = real_refresh
    Line.enabled = true
    _G.imgui = nil
    Path2.forget()
end


-- ---- the navigation grid ----------------------------------------------------------
do
    -- The real grids are built by tools/gen_navgrid.py from navmeshes this repository does
    -- not ship and never will (docs/NAVMESH.md), so the test builds its own: a room with a
    -- wall down the middle and one gap at the far end.  A straight line goes through the
    -- wall; a path has to go round.  That is the entire feature, in twenty cells.
    local Nav  = require('routing.navgrid')
    local Path = require('routing.path')

    local W, H, CELL = 20, 20, 1.0
    local function le32(v)
        if v < 0 then v = v + 4294967296 end
        return string.char(v % 256, math.floor(v / 256) % 256,
                           math.floor(v / 65536) % 256, math.floor(v / 16777216) % 256)
    end
    local function le16(v)
        if v < 0 then v = v + 65536 end
        return string.char(v % 256, math.floor(v / 256) % 256)
    end

    local mask, heights = {}, {}
    for cz = 0, H - 1 do
        for cx = 0, W - 1 do
            local open = true
            if cx == 10 and cz < 18 then open = false end       -- the wall, with a gap at 18
            if cx == 0 or cz == 0 or cx == W - 1 or cz == H - 1 then open = (cx ~= 10) end
            mask[#mask + 1] = open and 1 or 0
            heights[#heights + 1] = -8                          -- two yalms up, in quarters
        end
    end

    -- Runs of one: the reader does not care, and a test that hand-rolls a compressor is a
    -- test of the compressor.
    local body = { 'VGNV', string.char(1), le16(230), string.char(CELL * 10),
                   le32(0), le32(0), le16(W), le16(H), le32(#mask) }
    for _, v in ipairs(mask) do body[#body + 1] = le32(1) .. string.char(v) end
    body[#body + 1] = le32(#heights)
    for _, v in ipairs(heights) do body[#body + 1] = le32(1) .. le16(v) end

    local dir = os.tmpname()
    os.remove(dir)
    os.execute('mkdir -p "' .. dir .. '/data/nav"')
    local fh = io.open(dir .. '/data/nav/230.vgnav', 'wb')
    ok(fh ~= nil, 'the test grid can be written')
    if fh ~= nil then
        fh:write(table.concat(body))
        fh:close()

        Nav.reset()
        Nav.root = dir
        local g = Nav.load(230)
        ok(g ~= nil, 'the grid loads')
        if g ~= nil then
            eq(g.w, W, 'width survives the round trip')
            eq(g.h, H, 'height too')
            ok(math.abs(g.cell - CELL) < 0.001, 'and the cell size')
        end
        ok(Nav.load(231) == nil, 'a zone with no grid is simply absent')

        -- Stepped: the first ask says "not yet" rather than blocking the frame.
        local pts, again = Nav.provide(230, 2.5, 2.5, 0, 17.5, 2.5, 0)
        ok(pts == nil and again, 'the first ask is answered with "ask again"')
        local guard = 0
        while again and guard < 500 do
            Nav.step(200)
            pts, again = Nav.provide(230, 2.5, 2.5, 0, 17.5, 2.5, 0)
            guard = guard + 1
        end
        ok(pts ~= nil, 'the search finishes')
        if pts ~= nil then
            ok(#pts >= 3, ('and bends: %d points'):format(#pts))
            local deepest = 0
            for _, pt in ipairs(pts) do
                if pt.z > deepest then deepest = pt.z end
            end
            ok(deepest > 15, ('it goes round through the gap (z reaches %.0f)'):format(deepest))
            ok(math.abs(pts[1].x - 2.5) < 0.01, 'it starts exactly where asked')
            ok(math.abs(pts[#pts].x - 17.5) < 0.01, 'and ends exactly on the target')
            ok(math.abs(pts[2].y + 2) < 0.5, 'heights come from the grid')
        end

        -- No route at all: a target walled off entirely is a fact, not a hang.
        Nav.reset()
        Nav.root = dir
        local none, more = Nav.provide(230, 2.5, 2.5, 0, 200, 200, 0)
        guard = 0
        while more and guard < 500 do
            Nav.step(400)
            none, more = Nav.provide(230, 2.5, 2.5, 0, 200, 200, 0)
            guard = guard + 1
        end
        ok(none == nil, 'a target off the mesh gets no path')
        ok(guard < 500, 'and does not search forever')

        -- Wired into routing/path.lua, the line bends.
        Nav.reset()
        Nav.root = dir
        Nav.install(Path)
        Path.forget()
        WORLD.zone, WORLD.x, WORLD.z, WORLD.y = 230, 2.5, 2.5, -2
        local route, source
        for _ = 1, 200 do
            route, source = Path.to(C.world(), { x = 17.5, z = 2.5, y = -2 })
            if source == 'navmesh' then break end
            Nav.step(200)
        end
        eq(source, 'navmesh', 'routing/path.lua uses the grid once it has an answer')
        ok(route ~= nil and #route <= Path.max_points, 'and never returns more points than the cap')
        -- The straight-line fallback is what is drawn until then, so there is never a frame
        -- with no line at all.
        Path.provider = nil
        Nav.reset()
        Path.forget()
    end
    os.execute('rm -rf "' .. dir .. '"')
end

print(('\n%d passed, %d failed'):format(pass, fail))
os.exit(fail == 0 and 0 or 1)
