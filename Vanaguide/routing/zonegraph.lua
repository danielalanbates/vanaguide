-- Vanaguide :: routing/zonegraph.lua
-- Dijkstra over the zone graph, and the part that makes the graph honest: it learns.
--
-- The seed graph in data/travel.lua only covers what could be written down confidently.
-- Every time the player crosses a zone line, `learn()` records the pair, so the graph fills
-- in from actual play instead of from someone's memory of the map.  Learned edges are saved
-- with the character's settings and merged in on load.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local travel = require('data.travel')

-- The server's own zone-line table, generated into data/zonelines.lua by tools/gen_zonelines.py
-- from LandSandBoat's sql/zonelines.sql: 230 real crossings against the hand-written seed's 76.
-- gen_zonelines.py was written to fill the graph in (its docstring: "nobody should have to
-- discover Whitegate on foot"), but until now nothing required it and the graph ran on the seed
-- alone -- which not only missed 180 quests' worth of zones but carried edges the server data
-- contradicts (a direct Southern<->Port San d'Oria walk that does not exist; the real geometry
-- is the chain Port-Northern-Southern). Wired in here, deduplicated against the seed.
local ok_zl, zonelines = pcall(require, 'data.zonelines')

-- Whether a crossing has a coordinate to walk to, from the same generated source as the edges
-- (data/zonepoints.lua via routing/zonepoints.lua). A "blind" edge -- a phantom seed edge, or a
-- learned one, with no recorded doorway -- can be told to the player as text ("Zone into X") but
-- cannot be pointed at or auto-walked. Routing must therefore PREFER coordinate-backed legs: a
-- walkable chain has to beat a shorter blind hop, or the guide sends the player at a doorway that
-- is not there (the 2026-08-29 run teleported its last leg for exactly this reason).
local ok_zp, zpoints = pcall(require, 'routing.zonepoints')
local function backed(a, b)
    if not ok_zp then return true end   -- no zonepoints module: keep the old, unfiltered behaviour
    return #zpoints.exits(a, b) > 0 or #zpoints.exits(b, a) > 0
end

local Z = { adj = {}, learned = {} }

local function link(a, edge)
    Z.adj[a] = Z.adj[a] or {}
    table.insert(Z.adj[a], edge)
end

local function build()
    Z.adj = {}
    local seen = {}
    -- Add an undirected walk edge once. The generated table and the seed overlap heavily, and a
    -- learned edge can duplicate either; a pair is linked the first time it is seen and skipped
    -- after. `blind` is decided from zonepoints so the router can prefer walkable legs.
    local function add_walk(a, b, learned)
        if a == nil or b == nil or a == b then return end
        local key = math.min(a, b) .. ':' .. math.max(a, b)
        if seen[key] then return end
        seen[key] = true
        local blind = not backed(a, b)
        link(a, { to = b, cost = travel.WALK_COST, kind = 'walk', learned = learned, blind = blind })
        link(b, { to = a, cost = travel.WALK_COST, kind = 'walk', learned = learned, blind = blind })
    end

    -- Generated table first (authoritative and coordinate-matched), then the hand-written seed
    -- for any crossing it lacks -- real zone lines LandSandBoat's table does not carry stay in
    -- the graph (they route as blind text legs), they are just no longer preferred over a
    -- walkable route.
    if ok_zl and zonelines ~= nil and zonelines.walk ~= nil then
        for _, pair in ipairs(zonelines.walk) do add_walk(pair[1], pair[2], false) end
    end
    for _, pair in ipairs(travel.walk) do add_walk(pair[1], pair[2], false) end

    for _, t in ipairs(travel.transit) do
        link(t.from, { to = t.to, cost = t.cost, kind = 'transit', via = t.via, pass = t.pass, blind = false })
        -- Transit entries are written one direction each; nothing is mirrored here on purpose,
        -- because "the airship back" is a different counter in a different city.
    end

    for key in pairs(Z.learned) do
        local a, b = key:match('^(%d+):(%d+)$')
        if a ~= nil then add_walk(tonumber(a), tonumber(b), true) end
    end
end

--- Record a zone transition the player just made.  Returns true if it was new.
function Z.learn(from, to)
    if from == nil or to == nil or from == to then return false end
    local key, back = from .. ':' .. to, to .. ':' .. from
    if Z.learned[key] then return false end
    -- Already in the seed graph?  Then there is nothing to learn.
    for _, e in ipairs(Z.adj[from] or {}) do
        if e.to == to then return false end
    end
    Z.learned[key] = true
    Z.learned[back] = true
    build()
    return true
end

function Z.load_learned(saved)
    Z.learned = saved or {}
    build()
end

function Z.save_learned() return Z.learned end

--- Cheapest route from one zone to another.
--- Returns a list of legs { from, to, kind, via, cost } and the total travel cost, or nil.
---
--- The distance minimised is lexicographic: FIRST the number of blind legs (crossings with no
--- doorway to walk to), THEN the travel cost. A fully walkable route always beats one that
--- contains a blind hop, however much shorter the blind route is -- because a route the guide
--- can point along and auto-walk is strictly more useful than a shorter one it can only name.
--- It is packed into one number, blind * BLIND_WEIGHT + cost, with BLIND_WEIGHT larger than any
--- real total travel cost (a few hundred hops of at most ~600 s each), so ordering by the packed
--- value orders by blind count first. The honest travel cost is recovered as value % BLIND_WEIGHT
--- and is what the caller sees; the blind bias never leaks into the displayed ETA.
local BLIND_WEIGHT = 10000000

function Z.route(from, to)
    if from == nil or to == nil then return nil end
    if from == to then return {}, 0 end

    local dist, prev, visited = { [from] = 0 }, {}, {}
    while true do
        -- Small graph (a few hundred nodes): a linear scan for the nearest unvisited node
        -- is faster in practice than maintaining a heap, and much easier to read.
        local u, best = nil, math.huge
        for node, d in pairs(dist) do
            if not visited[node] and d < best then u, best = node, d end
        end
        if u == nil then return nil end
        if u == to then break end
        visited[u] = true
        for _, e in ipairs(Z.adj[u] or {}) do
            local nd = best + (e.blind and BLIND_WEIGHT or 0) + e.cost
            if dist[e.to] == nil or nd < dist[e.to] then
                dist[e.to] = nd
                prev[e.to] = { from = u, edge = e }
            end
        end
    end

    local legs, node = {}, to
    while node ~= from do
        local p = prev[node]
        if p == nil then return nil end
        table.insert(legs, 1, {
            from = p.from, to = node, kind = p.edge.kind,
            via = p.edge.via, cost = p.edge.cost, pass = p.edge.pass, blind = p.edge.blind,
        })
        node = p.from
    end
    return legs, dist[to] % BLIND_WEIGHT
end

build()
return Z
