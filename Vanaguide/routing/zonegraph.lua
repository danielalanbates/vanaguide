-- Vanaguide :: routing/zonegraph.lua
-- Dijkstra over the zone graph, and the part that makes the graph honest: it learns.
--
-- Generated zone lines and directed doorway coordinates are the primary seed. The older
-- hand-written travel table fills gaps only where the generated data cannot contradict it.
-- Observed crossings remain saved with the character's settings and merged in on load.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local travel = require('data.travel')
local points = require('routing.zonepoints')
local function optional(name)
    local ok, mod = pcall(require, name)
    return ok and mod or nil
end
local lines = optional('data.zonelines')
local pdata = optional('data.zonepoints')

-- The router caches by this version; rebuilds must invalidate even a cached nil route.
local Z = { adj = {}, learned = {}, suspect = {}, version = 0 }
local seen = {}

local function link(a, edge)
    local key = a .. ':' .. edge.to .. ':' .. edge.kind
    local have = seen[key]
    if have then
        if edge.cost < have.cost then
            for k, v in pairs(edge) do have[k] = v end
        end
        return
    end
    seen[key] = edge
    Z.adj[a] = Z.adj[a] or {}
    table.insert(Z.adj[a], edge)
end

local function walk(a, b)
    link(a, { to = b, cost = travel.WALK_COST, kind = 'walk' })
end

local function build()
    Z.adj, Z.suspect, seen = {}, {}, {}
    -- The generated pair list is a fallback when directional coordinate data is absent.
    -- A known one-way exit must not acquire an invented return edge from a pair's mirror.
    for _, pair in ipairs((lines and lines.walk) or {}) do
        local a, b = pair[1], pair[2]
        if not points.covered(a) then walk(a, b) end
        if not points.covered(b) then walk(b, a) end
    end
    -- Includes ordinary zone lines and event doors, in precisely their recorded direction.
    for from, rows in pairs((pdata and pdata.exit) or {}) do
        for _, row in ipairs(rows) do
            if from ~= row[1] then walk(from, row[1]) end
        end
    end
    for _, pair in ipairs(travel.walk) do
        local a, b = pair[1], pair[2]
        if points.contradicted(a, b) then
            -- e.g. Port San d'Oria has a real Northern exit, not a West Ronfaure gate.
            Z.suspect[#Z.suspect + 1] = { a, b }
        elseif not (points.covered(a) and points.covered(b)) then
            walk(a, b)
            walk(b, a)
        end
    end
    local transit = {}
    for _, t in ipairs(travel.transit) do
        link(t.from, { to = t.to, cost = t.cost, kind = 'transit', via = t.via, pass = t.pass })
        transit[t.from .. ':' .. t.to] = true
    end
    -- Keep authored pass requirements and wait costs; generated routes fill missing pairs.
    for _, t in ipairs((lines and lines.transit) or {}) do
        if not transit[t.from .. ':' .. t.to] then
            link(t.from, { to = t.to, cost = t.cost, kind = 'transit', via = t.via, pass = t.pass })
        end
    end
    for key in pairs(Z.learned) do
        local a, b = key:match('^(%d+):(%d+)$')
        if a ~= nil then
            a, b = tonumber(a), tonumber(b)
            link(a, { to = b, cost = travel.WALK_COST, kind = 'walk', learned = true })
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
--- Returns a list of legs { from, to, kind, via, cost } and the total cost, or nil.
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
            from = p.from, to = node, kind = p.edge.kind,
            via = p.edge.via, cost = p.edge.cost, pass = p.edge.pass,
        })
        node = p.from
    end
    return legs, dist[to]
end

build()
return Z
