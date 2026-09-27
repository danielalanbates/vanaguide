-- Vanaguide :: routing/zonegraph.lua
-- Dijkstra over the zone graph, and the part that makes the graph honest: it learns.
--
-- The graph is built from these sources, most trusted first:
--
--   data/zonelines.lua   GENERATED from a LandSandBoat checkout (tools/gen_zonelines.py):
--                        every doorway, cave mouth and city gate in the server's zone line
--                        table; the ferries and airships in its transport table; and the NPC
--                        events that move a player (tools/lsbtravel.py) -- Cavernous Maws to
--                        the [S] and Abyssea zones, the Adoulin waypoints, the Promyvion and
--                        Al'Taieu gates, Ra'Kaznar's transporters.  Home Points are there as
--                        a network (any one to any other): one hub node in the graph, folded
--                        out of every route Z.route returns, and priced as a last resort
--                        because no table knows which ones this character has touched.
--   data/zonepoints.lua  GENERATED too; besides the coordinates it carries the city doors
--                        that are event trigger areas rather than zone lines (the Chateau,
--                        Heavens Tower).  Those are one-way in the data and linked one way.
--   data/travel.lua      hand-written: the airships with their pass flag, and a seed walk
--                        list from before the generated table existed.  A seed pair the
--                        generated table covers both ends of and does not list is
--                        *contradicted* -- the server will not move a player across it -- so
--                        it is kept out of the graph and listed in Z.suspect for
--                        `/vg graph suspect`.
--   learned              every time the player crosses a zone line, `learn()` records the
--                        pair, so the graph fills in from actual play -- custom servers and
--                        anything the tables miss.  Saved with the character's settings.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local travel = require('data.travel')

local function optional(name)
    local ok, mod = pcall(require, name)
    if ok then return mod end
    return nil
end

local lines  = optional('data.zonelines')
local pdata  = optional('data.zonepoints')

-- Network hubs are nodes too; their keys are strings, so they can never be a zone id.
local HUB = 'net:'

-- Z.version changes every time the graph is rebuilt, so the router's route cache knows
-- when an answer it is holding has gone stale (a learned edge can open a shorter way).
local Z = { adj = {}, learned = {}, suspect = {}, version = 0 }

local seen = {}

-- One edge per (from, to, kind); a cheaper duplicate replaces a dearer one.  The same pair
-- arrives from several sources -- a zone line, a door row, a seed pair -- and a list with
-- three copies of every edge only makes the Dijkstra slower.
local function link(a, edge)
    local key = a .. ':' .. edge.to .. ':' .. edge.kind
    local have = seen[key]
    if have ~= nil then
        if edge.cost < have.cost then
            for k, v in pairs(edge) do have[k] = v end
        end
        return
    end
    seen[key] = edge
    Z.adj[a] = Z.adj[a] or {}
    table.insert(Z.adj[a], edge)
end

local function walk(a, b, extra)
    local e = { to = b, cost = travel.WALK_COST, kind = 'walk' }
    for k, v in pairs(extra or {}) do e[k] = v end
    link(a, e)
end

-- Does the generated data know this zone at all?  Only a zone it knows can contradict.
local function covered(zone)
    return pdata ~= nil and pdata.exit ~= nil and pdata.exit[zone] ~= nil
end

local function exits_to(from, to)
    local rows = pdata and pdata.exit and pdata.exit[from]
    if rows == nil then return false end
    for _, r in ipairs(rows) do
        if r[1] == to then return true end
    end
    return false
end

local function build()
    Z.adj, Z.suspect, seen = {}, {}, {}

    -- 1. Zone lines, undirected: each side of a doorway is its own row in the server table,
    --    and "these two zones touch" is what a route needs.
    for _, pair in ipairs((lines and lines.walk) or {}) do
        walk(pair[1], pair[2])
        walk(pair[2], pair[1])
    end

    -- 2. Doors that are event trigger areas, one way as the data has them.
    for from, rows in pairs((pdata and pdata.exit) or {}) do
        for _, r in ipairs(rows) do
            if r[1] ~= from then walk(from, r[1]) end
        end
    end

    -- 3. The hand-written seed, minus what the server's table contradicts.
    for _, pair in ipairs(travel.walk) do
        local a, b = pair[1], pair[2]
        if covered(a) and covered(b) and not exits_to(a, b) and not exits_to(b, a) then
            Z.suspect[#Z.suspect + 1] = { a, b }
        else
            walk(a, b)
            walk(b, a)
        end
    end

    -- 4. Transit.  The hand-written entries go first: they carry the pass flag and a cost
    --    that reflects the wait.  A generated ferry or airship fills in only where no
    --    hand-written entry already covers the same two zones.
    local have = {}
    for _, t in ipairs(travel.transit) do
        -- Transit entries are written one direction each; nothing is mirrored here on
        -- purpose, because "the airship back" is a different counter in a different city.
        link(t.from, { to = t.to, cost = t.cost, kind = 'transit', via = t.via, pass = t.pass,
                       needs = t.needs })
        have[t.from .. ':' .. t.to] = true
    end
    for _, t in ipairs((lines and lines.transit) or {}) do
        if not have[t.from .. ':' .. t.to] then
            link(t.from, { to = t.to, cost = t.cost, time = t.time, kind = 'transit', via = t.via,
                           net = t.net })
        end
    end

    -- 5. Networks (Home Points): any member to any other, joined through one hub node so the
    --    graph holds two edges per zone instead of one per pair.  Z.route folds the two legs
    --    through the hub back into one, so nothing outside this file ever sees it.
    for name, n in pairs((lines and lines.network) or {}) do
        local hub = HUB .. name
        for zone, via in pairs(n.via or {}) do
            link(zone, { to = hub, cost = n.cost, time = n.time, kind = 'transit', net = name })
            link(hub, { to = zone, cost = 0, time = 0, kind = 'transit', net = name, via = via })
        end
    end

    -- 6. What this character has walked across.
    for key in pairs(Z.learned) do
        local a, b = key:match('^(%d+):(%d+)$')
        if a ~= nil then
            a, b = tonumber(a), tonumber(b)
            walk(a, b, { learned = true })
        end
    end

    Z.version = Z.version + 1
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
    -- Two zones that both have a Home Point and do not touch: that was a warp, not a zone
    -- line.  Learning it would put a walk between them that nobody can walk.
    for _, n in pairs((lines and lines.network) or {}) do
        if n.via ~= nil and n.via[from] ~= nil and n.via[to] ~= nil then return false end
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

--- Seconds a route really takes: the sum of its legs' `time`, not the price it was chosen by.
function Z.eta(legs)
    if legs == nil then return nil end
    local t = 0
    for _, leg in ipairs(legs) do t = t + (leg.time or leg.cost or 0) end
    return t
end

--- Cheapest route from one zone to another.
--- Returns a list of legs { from, to, kind, via, cost, time } and the total cost, or nil.
--- `cost` is the router's price and includes the last-resort penalties; `time` is the
--- seconds a leg really takes, for anything that shows the player an estimate.
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
            local nd = best + e.cost
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
            from = p.from, to = node, kind = p.edge.kind, net = p.edge.net,
            via = p.edge.via, cost = p.edge.cost, time = p.edge.time or p.edge.cost,
            pass = p.edge.pass, needs = p.edge.needs,
        })
        node = p.from
    end
    -- Fold "zone -> hub -> zone" into the one warp it is.
    for i = #legs - 1, 1, -1 do
        local a, b = legs[i], legs[i + 1]
        if type(a.to) == 'string' and a.to == b.from then
            legs[i] = {
                from = a.from, to = b.to, kind = 'transit', net = a.net,
                via = b.via, cost = a.cost + b.cost, time = a.time + b.time,
            }
            table.remove(legs, i + 1)
        end
    end
    return legs, dist[to]
end

build()
return Z
