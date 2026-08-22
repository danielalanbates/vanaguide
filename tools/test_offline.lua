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

print(('\n%d passed, %d failed'):format(pass, fail))
os.exit(fail == 0 and 0 or 1)
