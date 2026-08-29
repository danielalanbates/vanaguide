-- Vanaguide :: core/walk.lua
-- The character follows its own line.
--
-- Everything else in this addon *describes* the way: an arrow, a line, a distance.  This
-- walks it.  Each frame the player entity is moved a run-speed step along the path the
-- guide is drawing, facing the way it is going, until it stands beside the target.  The
-- client sees its own position change and reports it to the server as it would a keypress,
-- so the server, other players and zone lines all see an ordinary running character.
--
-- It exists so the guide can be *tested* the way it is meant to be used -- a character
-- accepting quests, listening to the narrator, and following the arrow from one to the
-- next on our own LandSandBoat world -- not for play on anyone else's server, where moving
-- a character by writing its position is a bannable offence.  tools/guided_walk.sh refuses
-- any server that is not 127.0.0.1, and so does this: Walk.start checks the same thing.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local U    = require('core.util')
local Path = require('routing.path')

-- A wall clock.  os.clock() is CPU time, which under this client runs faster than the wall
-- and skips about; GetTickCount is what the game itself walks by.
local ffi_ok, ffi = pcall(require, 'ffi')
if ffi_ok then pcall(ffi.cdef, 'unsigned long GetTickCount(void);') end
local function now_s()
    if ffi_ok then
        local ok, t = pcall(function () return ffi.C.GetTickCount() end)
        if ok and t ~= nil then return tonumber(t) / 1000 end
    end
    return os.clock()
end

local W = {
    active = false,
    speed = 5.0,        -- yalms per second: FFXI's run speed is 40 units, about 5 yalms/s
    arrive = 2.5,       -- stop this close to the target
    target = nil,       -- { x, z, y }
    label = nil,
    last = nil,         -- os.clock() of the previous step
    walked = 0,
    reason = nil,       -- why the last walk stopped
    -- The client keeps its own collision: a path corner that clips a pillar by a hand's
    -- breadth is a wall the entity will not be written through.  When the position stops
    -- changing while we keep stepping, aim further down the path and sidestep, alternating
    -- sides, until it moves again.
    stuck_since = nil,
    stuck_pos = nil,
    nudge = 0,
    stuck_limit = 8,    -- seconds without progress before giving up
    -- How the character is moved.  Measured 2026-08-28 on this client: the local player's
    -- position is owned by the game's own controller and every entity write ('pos', 'delta',
    -- 'move') is overwritten the same frame; only the yaw survives.  Synthetic input never
    -- reaches the client either (winecursor's counter does not move).  What does work is the
    -- server: 'server' mode asks it, a few times a second, to put the character a run-speed
    -- step further along the path (`!pos`, a GM command that exists only on our own world),
    -- and the client is told where it now stands.  The character slides rather than runs --
    -- there is no animation without input -- but it follows the line, crosses zone lines,
    -- and arrives.  The other modes are kept so the next person can re-measure rather than
    -- re-discover.
    mode = 'server',
    tick = 0.25,        -- seconds between server steps in 'server' mode
    last_tick = nil,
}

local function player_index()
    local ok, idx = pcall(function ()
        return AshitaCore:GetMemoryManager():GetParty():GetMemberTargetIndex(0)
    end)
    if ok and idx ~= nil and idx > 0 then return idx end
    return nil
end

function W.start(target, label)
    if target == nil or target.x == nil then
        W.reason = 'nothing to walk to'
        return false
    end
    W.active, W.target, W.label = true, { x = target.x, z = target.z, y = target.y }, label
    W.last, W.walked, W.reason = nil, 0, nil
    W.stuck_since, W.stuck_pos, W.nudge = nil, nil, 0
    W.last_wp, W.last_tick = nil, nil
    return true
end

function W.stop(reason)
    if W.active then
        W.reason = reason or 'stopped'
        if W.mode == 'server' then
            pcall(function () AshitaCore:GetChatManager():QueueCommand(-1, '!walkto stop') end)
        end
    end
    W.active, W.last, W.last_wp, W.last_tick = false, nil, nil, nil
end

--- One frame.  `w` is the world snapshot (x, z, y, zone, yaw).  Returns true on arrival.
function W.update(w)
    if not W.active then return false end
    if w == nil or w.x == nil or w.zone == nil then W.last = nil; return false end
    local idx = player_index()
    if idx == nil then W.last = nil; return false end

    local now = now_s()
    local dt = (W.last ~= nil) and (now - W.last) or 0
    W.last = now
    if dt <= 0 or dt > 0.5 then return false end     -- a hitch or a zone: skip, do not leap

    -- Progress check: has the entity actually gone anywhere since we last looked?
    if W.stuck_pos == nil or U.dist(w.x, w.z, W.stuck_pos.x, W.stuck_pos.z) > 0.3 then
        W.stuck_pos, W.stuck_since = { x = w.x, z = w.z }, now
        if W.nudge ~= 0 and U.dist(w.x, w.z, W.stuck_pos.x, W.stuck_pos.z) > 3 then W.nudge = 0 end
    elseif now - W.stuck_since > W.stuck_limit then
        W.stop(('stuck at (%.1f, %.1f)'):format(w.x, w.z))
        return false
    end
    local stuck = (now - W.stuck_since) > 0.4
    if stuck then
        -- Each half-second stuck: aim one point further and swing to the other side.
        local n = math.floor((now - W.stuck_since) / 0.5)
        W.nudge = (n % 2 == 0) and n or -n
    end

    local t = W.target
    local remaining = U.dist(w.x, w.z, t.x, t.z)
    if remaining <= W.arrive then
        W.stop('arrived')
        return true
    end

    -- Follow the drawn path when there is one; otherwise straight at the target.
    local points = Path.to(w, t)
    local nx, nz, ny = t.x, t.z, t.y
    if points ~= nil and #points >= 2 then
        local i = Path.nearest_index(points, w.x, w.z)
        -- Aim past the nearest point so a point already reached does not pin us in place.
        local j = i
        while j < #points and U.dist(w.x, w.z, points[j].x, points[j].z) < 1.5 do j = j + 1 end
        if stuck then j = math.min(#points, j + math.abs(W.nudge)) end
        if W.mode == 'server' then
            -- Aim at the far end of the straight stretch ahead, not the next sample: the
            -- server walks a straight line anyway, and one command per corner is quieter
            -- than one every six yalms.  A point counts as "on the stretch" while every
            -- sample between here and it lies within a yalm of the straight line to it.
            local k = j
            while k < #points do
                local cx, cz = points[k + 1].x, points[k + 1].z
                if U.dist(w.x, w.z, cx, cz) > 60 then break end
                local vx, vz = cx - w.x, cz - w.z
                local vl = math.sqrt(vx * vx + vz * vz)
                if vl < 1e-3 then break end
                local straight = true
                for m = j, k do
                    local px, pz = points[m].x - w.x, points[m].z - w.z
                    local off = math.abs(px * vz - pz * vx) / vl
                    if off > 1.0 then straight = false; break end
                end
                if not straight then break end
                k = k + 1
            end
            j = k
        end
        nx, nz, ny = points[j].x, points[j].z, points[j].y
    end

    local dx, dz = nx - w.x, nz - w.z
    if stuck and W.nudge ~= 0 then
        -- Sidestep: a perpendicular shove of a couple of yalms, side chosen by the nudge sign.
        local d0 = math.sqrt(dx * dx + dz * dz)
        if d0 > 1e-3 then
            local side = (W.nudge > 0) and 1 or -1
            dx = dx + (-dz / d0) * 2.5 * side
            dz = dz + ( dx / d0) * 2.5 * side
        end
    end
    local d = math.sqrt(dx * dx + dz * dz)
    if d < 1e-3 then return false end
    local step = math.min(d, W.speed * dt)
    local x, z = w.x + dx / d * step, w.z + dz / d * step
    -- Height follows the path's own sample so stairs and bridges are climbed, not tunnelled.
    local y = w.y or 0
    if ny ~= nil then y = y + (ny - y) * math.min(1, step / math.max(d, 1e-3)) end
    -- FFXI yaw: 0 faces east (+x), counter-clockwise; z points south on the screen.
    local yaw = math.atan2(-dz, dx)

    -- Ashita's entity names the axes the way FFXI's memory does: X, then Y for the *other
    -- horizontal* axis (this addon's z), then Z for the height (this addon's y).  core/util
    -- reads them in exactly that order; write them back the same way.
    if W.mode == 'server' then
        -- One `!walkto` per waypoint: the server (scripts/commands/walkto.lua, local world
        -- only) then moves the character toward it at run speed on its own timer, and the
        -- client is told where it stands.  Re-issued when the waypoint changes, and every
        -- few seconds regardless, in case the server's walk ended early.
        local same = W.last_wp ~= nil and W.last_wp.x == nx and W.last_wp.z == nz
        if same and W.last_tick ~= nil and now - W.last_tick < 3 then
            W.walked = W.walked + W.speed * dt
            return false
        end
        W.last_tick, W.last_wp = now, { x = nx, z = nz }
        local okc = pcall(function ()
            AshitaCore:GetChatManager():QueueCommand(-1,
                ('!walkto %.2f %.2f %.2f %.1f'):format(nx, ny or (w.y or 0), nz, W.speed))
        end)
        if not okc then W.stop('could not ask the server'); return false end
        return false
    end

    local ok = pcall(function ()
        local e = AshitaCore:GetMemoryManager():GetEntity()
        e:SetLocalPositionYaw(idx, yaw)
        if W.mode == 'delta' then
            -- The client's own integrator: a per-frame displacement it adds itself.
            e:SetMoveDeltaX(idx, dx / d * step)
            e:SetMoveDeltaY(idx, dz / d * step)
            e:SetMoveDeltaZ(idx, (ny or y) - (w.y or 0))
        elseif W.mode == 'move' then
            e:SetMoveX(idx, dx / d * step)
            e:SetMoveY(idx, dz / d * step)
        else
            e:SetLocalPositionX(idx, x)
            e:SetLocalPositionY(idx, z)
            e:SetLocalPositionZ(idx, y)
            e:SetLastPositionX(idx, x)
            e:SetLastPositionY(idx, z)
            e:SetLastPositionZ(idx, y)
        end
    end)
    if not ok then W.stop('the entity would not take a position'); return false end
    W.walked = W.walked + step
    return false
end

function W.status()
    if W.active then
        local t = W.target
        return ('walk: to (%.1f, %.1f)%s, %.0f yalms walked')
            :format(t.x, t.z, W.label and (' ' .. W.label) or '', W.walked)
    end
    return 'walk: idle' .. (W.reason and (' (' .. W.reason .. ')') or '')
end

return W
