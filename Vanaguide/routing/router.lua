-- Vanaguide :: routing/router.lua
-- Turns "the step is over there" into "here is the next thing to do".
--
-- The router answers with a *place*, not a sentence, whenever it can.  Before
-- routing/zonepoints.lua existed it could only do that for a step in the zone you were
-- already standing in; a step three zones away produced "Zone into La Theine Plateau" and
-- an arrow pointing at nothing, for the entire length of the journey.  Now every leg of a
-- route -- a doorway to walk to, a dock to stand on -- has a coordinate, so the arrow, the
-- distance and the line on the ground all work the same whether the target is thirty yalms
-- away or three zones.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local U      = require('core.util')
local graph  = require('routing.zonegraph')
local points = require('routing.zonepoints')

local R = {}

-- Dijkstra runs over a few hundred nodes, which is cheap once and not cheap twice a frame
-- for as long as the player is walking.  The answer only changes when the destination
-- changes, when the player crosses a zone line, or when the graph learns an edge.
local cache = { from = nil, to = nil, version = -1, legs = nil, cost = nil }

local function route(from, to)
    if cache.from == from and cache.to == to and cache.version == graph.version then
        return cache.legs, cache.cost
    end
    local legs, cost = graph.route(from, to)
    cache.from, cache.to, cache.version = from, to, graph.version
    cache.legs, cache.cost = legs, cost
    return legs, cost
end

--- Drop the cached route.  Only needed by the tests, which move the world under it.
function R.forget() cache.from, cache.to, cache.version = nil, nil, -1 end

local function minutes(seconds)
    if seconds == nil then return nil end
    if seconds < 90 then return ('%ds'):format(math.floor(seconds)) end
    return ('%dm'):format(math.floor(seconds / 60 + 0.5))
end

--- Fill in bearing, distance and arrival for a target in the zone the player is in.
local function aim(rec, w, tx, tz, radius)
    if w.x == nil or tx == nil then return rec end
    rec.distance = U.dist(w.x, w.z, tx, tz)
    rec.bearing = U.relative_bearing(w.x, w.z, w.yaw or 0, tx, tz)
    rec.arrived = rec.distance <= (radius or 10)
    return rec
end

--- What should the arrow point at, and what should the window say under it?
--- Returns a table:
---   mode  'here'    the step is in this zone -- bearing/distance are set
---         'travel'  you are somewhere else -- `via` says how to start moving, and
---                   `target` is the doorway or dock to walk to, when one is known
---         'unknown' the step has no place, or no route exists
--- `target` is { x, z, y } in the *current* zone whenever it is set, for both 'here' and
--- 'travel', so a caller that draws a path never has to care which mode it is in.
function R.recommend(step, w)
    if step == nil then return { mode = 'unknown', text = 'No step.' } end
    if w.zone == nil then return { mode = 'unknown', text = 'Not in the world yet.' } end

    local zone = step.zone
    if zone == nil then
        return { mode = 'unknown', text = step.note or 'Do this wherever you are.' }
    end

    if zone == w.zone then
        if step.pos == nil or w.x == nil then
            return { mode = 'here', text = 'In ' .. U.zone_name(zone), distance = nil }
        end
        local rec = { mode = 'here', target = { x = step.pos.x, z = step.pos.z, y = step.pos.y } }
        aim(rec, w, step.pos.x, step.pos.z, step.pos.r)
        rec.text = ('%.0f yalms'):format(rec.distance or 0)
        return rec
    end

    local legs, cost = route(w.zone, zone)
    if legs == nil then
        return {
            mode = 'unknown',
            text = ('Go to %s -- no route known from %s yet.')
                :format(U.zone_name(zone), U.zone_name(w.zone)),
        }
    end
    local first = legs[1]
    if first == nil then
        return { mode = 'travel', legs = legs, eta = cost, text = 'You are there.',
                 destination = zone, hops = 0 }
    end

    local rec = {
        mode = 'travel', legs = legs, eta = cost, destination = zone, hops = #legs,
        leg = first,
    }
    local target, verb = points.leg_target(first, w.x, w.z)
    if target ~= nil then
        rec.target = { x = target.x, z = target.z, y = target.y }
        -- The radius is generous on purpose: a zone line is a trigger volume several yalms
        -- across and the recorded point is one spot inside it, so "arrived" has to mean
        -- "close enough that the doorway is in front of you", not "standing on the pixel".
        aim(rec, w, target.x, target.z, 12)
        if verb == 'board' then
            rec.text = target.via or first.via or 'Board here'
        else
            rec.text = ('Zone into %s'):format(U.zone_name(first.to))
        end
        if rec.distance ~= nil then
            rec.text = ('%s -- %.0f yalms'):format(rec.text, rec.distance)
        end
    else
        -- No recorded coordinate: say the same thing the old router said rather than
        -- inventing a place.  Learned edges land here, and so does any server whose zone
        -- lines are not in the generated table.
        if first.kind == 'transit' then
            rec.text = first.via or ('Travel to ' .. U.zone_name(first.to))
        else
            rec.text = ('Zone into %s'):format(U.zone_name(first.to))
        end
        rec.blind = true
    end
    return rec
end

--- A one-line description of a whole route, for `/vg route` and the window.
function R.describe(legs)
    if legs == nil then return 'no route' end
    if #legs == 0 then return 'you are already there' end
    local out = {}
    for _, leg in ipairs(legs) do
        if leg.kind == 'transit' then
            out[#out + 1] = leg.via
        else
            out[#out + 1] = U.zone_name(leg.to)
        end
    end
    return table.concat(out, ' -> ')
end

--- The route as lines a human reads one at a time, for `/vg route`.
--- Each entry is { n, text, kind, known } -- `known` is false when the leg has no recorded
--- coordinate, which is the honest way to say "I can get you there but not point at it".
function R.itinerary(legs, from, x, z)
    local out = {}
    if legs == nil then return out end
    local here = from
    for i, leg in ipairs(legs) do
        local target = points.leg_target(leg, (i == 1) and x or nil, (i == 1) and z or nil)
        local text
        if leg.kind == 'transit' then
            text = leg.via or ('travel to ' .. U.zone_name(leg.to))
        else
            text = ('%s -> %s'):format(U.zone_name(here), U.zone_name(leg.to))
        end
        if target ~= nil and i == 1 and x ~= nil then
            text = ('%s (%.0f yalms)'):format(text, U.dist(x, z, target.x, target.z))
        end
        out[#out + 1] = { n = i, text = text, kind = leg.kind, known = target ~= nil }
        here = leg.to
    end
    return out
end

--- The zones you pass through, short enough for a narrow window: the first few by name and
--- then a count.  A full chain across a continent is eleven names and wraps to four lines.
function R.chain(legs, max_names)
    if legs == nil or #legs == 0 then return nil end
    max_names = max_names or 3
    local out = {}
    for i = 1, math.min(max_names, #legs) do
        local leg = legs[i]
        out[#out + 1] = (leg.kind == 'transit') and (leg.via or 'transit') or U.zone_name(leg.to)
    end
    local rest = #legs - math.min(max_names, #legs)
    local text = table.concat(out, ' > ')
    if rest > 0 then text = ('%s > +%d more'):format(text, rest) end
    return text
end

--- "3 zones, about 5m" -- the line the window prints under the step.
function R.summary(rec)
    if rec == nil or rec.hops == nil then return nil end
    if rec.hops == 0 then return nil end
    local eta = minutes(rec.eta)
    if eta == nil then return ('%d zones to %s'):format(rec.hops, U.zone_name(rec.destination)) end
    return ('%d zones to %s, about %s'):format(rec.hops, U.zone_name(rec.destination), eta)
end

return R
