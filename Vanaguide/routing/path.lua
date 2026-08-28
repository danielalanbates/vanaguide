-- Vanaguide :: routing/path.lua
-- The list of points between here and there.
--
-- The arrow says which way; a path says which way *for the next two hundred yalms*, which is
-- the difference between a compass and a guide.  Two sources, in order:
--
--   1. a provider, if one is installed -- routing/navgrid.lua walks the server's own
--      navigation mesh and comes back with a route that goes around the wall;
--   2. a straight line, subdivided, which is what you get with no navmesh installed and is
--      exactly as good as the arrow was.
--
-- Recomputing is not free (see routing/navgrid.lua: A* over tens of thousands of cells with
-- the JIT off), so it happens when something has actually changed -- a new target, a new
-- zone, or the player has walked far enough that the old path no longer starts where they
-- are -- and never on a frame just because a frame happened.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local U = require('core.util')

local Path = {
    -- Set by routing/navgrid.lua when a mesh for this zone is available.
    -- provider(zone, x1, z1, y1, x2, z2, y2) -> { {x=,z=,y=}, ... } or nil
    provider = nil,
    -- How far apart the drawn points are.  Six yalms is about two seconds of running, which
    -- is close enough that the line reads as continuous and sparse enough that a two hundred
    -- yalm path is thirty points and not two hundred.
    spacing = 6,
    max_points = 80,
    -- Diagnostics, for /vg status.
    source = 'none',
    computed = 0,
}

local cache = {
    zone = nil, tx = nil, tz = nil, ax = nil, az = nil, points = nil, source = 'none',
}

--- Fill in the points between two ends, at most `max_points` of them.
local function subdivide(x1, z1, y1, x2, z2, y2, spacing, max_points)
    local d = U.dist(x1, z1, x2, z2)
    local n = math.max(1, math.min(max_points - 1, math.floor(d / spacing)))
    local out = {}
    for i = 0, n do
        local t = i / n
        out[#out + 1] = {
            x = x1 + (x2 - x1) * t,
            z = z1 + (z2 - z1) * t,
            y = y1 + (y2 - y1) * t,
        }
    end
    return out
end

--- Resample a coarse route -- the corners a navmesh gives back -- into evenly spaced points.
---
--- The spacing widens rather than the path being cut short.  An earlier version stopped at
--- `max_points` and returned what it had, which draws a confident line that ends in a field
--- three hundred yalms from anywhere -- the one failure mode worse than no line at all.
local function resample(route, spacing, max_points)
    if route == nil or #route < 2 then return route end
    local total = 0
    for i = 2, #route do
        total = total + U.dist(route[i - 1].x, route[i - 1].z, route[i].x, route[i].z)
    end
    if total > spacing * (max_points - 1) then
        spacing = total / (max_points - 1)
    end
    local out = { { x = route[1].x, z = route[1].z, y = route[1].y } }
    for i = 2, #route do
        local a, b = route[i - 1], route[i]
        local d = U.dist(a.x, a.z, b.x, b.z)
        local n = math.max(1, math.floor(d / spacing))
        for k = 1, n do
            local t = k / n
            out[#out + 1] = {
                x = a.x + (b.x - a.x) * t,
                z = a.z + (b.z - a.z) * t,
                y = (a.y or 0) + ((b.y or 0) - (a.y or 0)) * t,
            }
        end
    end
    return out
end

--- The path from where the player is to `target`, or nil when there is nothing to draw.
--- `target` is { x, z, y } in the player's current zone; `y` may be nil, in which case the
--- player's own height is used for the whole path, which is right on one floor and wrong in
--- a tower -- see docs/LINE.md.
function Path.to(w, target)
    if w == nil or target == nil or w.x == nil or w.zone == nil then return nil end
    if target.x == nil or target.z == nil then return nil end

    local moved = (cache.ax == nil) or (U.dist(w.x, w.z, cache.ax, cache.az) > 12)
    local retargeted = (cache.tx == nil)
        or (math.abs(target.x - cache.tx) > 2) or (math.abs(target.z - cache.tz) > 2)
    if cache.points ~= nil and cache.zone == w.zone and not moved and not retargeted
        and not cache.pending then
        return cache.points, cache.source
    end

    local ty = target.y or w.y or 0
    local points, source, pending = nil, 'straight', false
    if Path.provider ~= nil then
        -- The provider may not have an answer yet: routing/navgrid.lua searches a few hundred
        -- cells a frame rather than stalling the client, and says "ask again" until it is
        -- done.  The straight line is drawn in the meantime, so there is never a frame with
        -- no line at all -- it just straightens out for a third of a second and then bends.
        local ok, route, again = pcall(Path.provider, w.zone, w.x, w.z, w.y or 0,
                                       target.x, target.z, ty)
        if ok and route ~= nil and #route >= 2 then
            points = resample(route, Path.spacing, Path.max_points)
            source = 'navmesh'
        elseif ok and again then
            pending = true
        end
    end
    if points == nil then
        points = subdivide(w.x, w.z, w.y or 0, target.x, target.z, ty,
                           Path.spacing, Path.max_points)
    end

    cache.zone, cache.tx, cache.tz = w.zone, target.x, target.z
    cache.ax, cache.az = w.x, w.z
    cache.points, cache.source, cache.pending = points, source, pending
    Path.source = source
    Path.computed = Path.computed + 1
    return points, source
end

--- Which point of a path the player is standing nearest.  The line is drawn from there
--- forward, so the part already walked stops being drawn instead of trailing behind and
--- pointing backwards.
function Path.nearest_index(points, x, z)
    if points == nil or #points == 0 or x == nil then return 1 end
    local best, best_d = 1, nil
    for i = 1, #points do
        local d = U.dist2(x, z, points[i].x, points[i].z)
        if best_d == nil or d < best_d then best, best_d = i, d end
    end
    return best
end

--- Throw the cached path away.  Called when the step changes, and by the tests.
function Path.forget()
    cache.zone, cache.tx, cache.tz, cache.ax, cache.az, cache.points = nil, nil, nil, nil, nil, nil
    cache.pending = false
end

return Path
