-- Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
-- Real shipped graph/coordinate fixtures only; no client, server or guessed geometry.
package.path = 'Vanaguide/?.lua;Vanaguide/?/init.lua;tools/?.lua;' .. package.path
require('stubs')
local checks = 0
local function check(value, message)
    assert(value, message)
    checks = checks + 1
end
local graph = require('routing.zonegraph')
local points = require('routing.zonepoints')
local router = require('routing.router')

local direct = graph.route(232, 231)
check(direct and #direct == 1 and direct[1].to == 231,
       'Port San d\'Oria must use its recorded direct Northern San d\'Oria crossing')
local target = points.leg_target(direct[1], 0, 0)
check(target and math.abs(target.x + 111.8) < 0.01 and math.abs(target.z + 136.5) < 0.01,
       'the route must use the existing generated exit coordinate')
local rec = router.recommend({zone=231,pos={x=-1,z=1}}, {zone=232,x=0,z=0,yaw=0})
check(rec.target and rec.distance and rec.bearing and not rec.blind,
       'cross-zone recommendations must provide a bearing and distance to the real doorway')
local via_north = graph.route(232, 230)
check(via_north and #via_north == 2 and via_north[1].to == 231,
       'the contradicted handwritten Port-to-South shortcut must not win')
local out = graph.route(232, 100)
check(out and #out == 2 and out[1].to == 231,
       'the contradicted handwritten Port-to-West-Ronfaure shortcut must not win')
local adoulin = graph.route(256, 257)
check(adoulin and #adoulin == 1, 'generated crossings must be loaded beyond the base cities')
local door = graph.route(231, 233)
check(door and #door == 1 and points.leg_target(door[1]), 'recorded event doors join the graph')
local air = graph.route(232, 246)
check(air and #air == 1 and air[1].pass == true and air[1].cost == 420,
       'generated transit must not replace authored pass requirements or wait costs')

-- router.recommend caches a route by graph.version. A new real observation must invalidate it.
local old = router.recommend({zone=299}, {zone=232,x=0,z=0,yaw=0})
check(old.mode == 'unknown')
local version = graph.version
check(graph.learn(232, 299))
check(type(version) == 'number' and graph.version > version, 'learning must version the graph')
local learned = router.recommend({zone=299}, {zone=232,x=0,z=0,yaw=0})
check(learned.mode == 'travel' and learned.leg.to == 299,
       'a cached unreachable answer must be replaced after learning')

local function fixture(travel, lines, data)
    package.loaded['routing.zonegraph'] = nil
    package.loaded['routing.zonepoints'] = nil
    package.loaded['data.travel'] = travel
    package.loaded['data.zonelines'] = lines
    package.loaded['data.zonepoints'] = data
    return require('routing.zonegraph')
end
local directed = fixture({WALK_COST=90,walk={{1,2}},transit={}}, {walk={{1,2}}},
                         {exit={[1]={{2,0,0,0}},[2]={}},dock={}})
check(directed.route(1,2), 'recorded one-way exits remain available')
check(not directed.route(2,1), 'neither generated nor handwritten pairs may invent a return doorway')
local fallback = fixture({WALK_COST=90,walk={{999,998}},transit={}}, {walk={{10,11}}},
                         {exit={},dock={}})
check(fallback.route(10,11) and fallback.route(11,10), 'generated pairs work without coordinate coverage')
check(fallback.route(999,998), 'uncovered custom seed zones remain routable')
print(checks .. ' generated-route regressions passed')
