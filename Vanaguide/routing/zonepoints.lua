-- Vanaguide :: routing/zonepoints.lua
-- The doorway, not just the door's existence.
--
-- routing/zonegraph.lua can say "San d'Oria touches West Ronfaure".  That plans a journey and
-- it does not walk one: for the whole length of a trip the arrow had nothing to point at and
-- the window said the same five words at the start of the road and at the end of it.  This
-- module answers the question the player is actually asking -- *which way is out* -- from
-- data/zonepoints.lua, generated from the server's own zone line table.
--
-- Two zones can touch in more than one place.  Nothing here guesses which one is meant; it
-- returns the nearest to where the player is standing, which is right whenever the player is
-- anywhere near either, and no worse than a coin toss when they are not.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local U = require('core.util')

local ok_points, data = pcall(require, 'data.zonepoints')
if not ok_points then data = nil end

local Z = { available = (data ~= nil) }

--- Every recorded crossing out of `from` into `to`, as { x, z, y } in `from`'s coordinates.
function Z.exits(from, to)
    if data == nil or from == nil or to == nil then return {} end
    local rows = data.exit[from]
    if rows == nil then return {} end
    local out = {}
    for _, r in ipairs(rows) do
        if r[1] == to then out[#out + 1] = { x = r[2], z = r[3], y = r[4] } end
    end
    return out
end

--- The crossing out of `from` into `to` nearest to (x, z), or nil if none is recorded.
--- `x` and `z` may be nil -- before the player has a position, the first one is as good a
--- guess as any and is better than refusing to answer.
function Z.nearest_exit(from, to, x, z)
    local rows = Z.exits(from, to)
    if #rows == 0 then return nil end
    if x == nil or z == nil then return rows[1] end
    local best, best_d
    for _, r in ipairs(rows) do
        local d = U.dist2(x, z, r.x, r.z)
        if best_d == nil or d < best_d then best, best_d = r, d end
    end
    return best
end

--- Where you stand to board the boat or airship from `from` towards `to`.
--- Returns { x, z, y, via } or nil.
function Z.dock(from, to)
    if data == nil or from == nil or to == nil then return nil end
    local byfrom = data.dock[from]
    if byfrom == nil then return nil end
    local r = byfrom[to]
    if r == nil then return nil end
    return { x = r[1], z = r[2], y = r[3], via = r[4] }
end

--- The point to walk to for the first leg of a route, whatever kind of leg it is.
--- Returns a point and a verb ('walk' or 'board'), or nil when the data has no answer.
function Z.leg_target(leg, x, z)
    if leg == nil then return nil end
    if leg.kind == 'transit' then
        local d = Z.dock(leg.from, leg.to)
        if d ~= nil then return d, 'board' end
        return nil
    end
    local e = Z.nearest_exit(leg.from, leg.to, x, z)
    if e ~= nil then return e, 'walk' end
    return nil
end

--- Is this zone one the generated table knows about at all?  The distinction matters: the
--- table lists no crossing between two zones either because they do not touch, or because
--- the server has not implemented that zone.  Only the first is evidence.
function Z.covered(zone)
    return data ~= nil and zone ~= nil and data.exit[zone] ~= nil
end

--- True when both zones are in the generated table and neither lists the other.  That is the
--- server saying, as plainly as a table can, that these two do not touch -- which is worth
--- knowing, because data/travel.lua was written from memory and memory has San d'Oria's
--- three wards joined in a triangle when they are actually a chain.
function Z.contradicted(a, b)
    if not (Z.covered(a) and Z.covered(b)) then return false end
    if #Z.exits(a, b) > 0 or #Z.exits(b, a) > 0 then return false end
    return true
end

--- How many crossings are known out of this zone.  Used by /vg status and the tests.
function Z.count(from)
    if data == nil then return 0 end
    local rows = data.exit[from]
    return rows and #rows or 0
end

return Z
