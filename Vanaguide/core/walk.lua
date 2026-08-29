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
    -- 'follow' (2026-08-29): the client's *own* auto-run controller, the one `/follow` and the
    -- numpad autorun use.  Ashita exposes it as IAutoFollow: a delta vector plus an
    -- IsAutoRunning flag, and the client then runs the character along that vector itself --
    -- with the run animation, its own collision and the ordinary movement packets, on any
    -- world, with no server help and no input.  This is what Windower's `ffxi.run()` does
    -- and what every walking bot on that side is built on.  Tried after 'server' shipped;
    -- measured below in docs/WALK.md.
    mode = 'follow',
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
    W.last_wp, W.last_tick, W.aim, W.nudges, W.best_remaining = nil, nil, nil, 0, nil
    return true
end

function W.stop(reason)
    if W.active then
        W.reason = reason or 'stopped'
        if W.mode == 'server' then
            pcall(function () AshitaCore:GetChatManager():QueueCommand(-1, '!walkto stop') end)
        elseif W.mode == 'follow' then
            W.run(nil)
        end
    end
    W.active, W.last, W.last_wp, W.last_tick = false, nil, nil, nil
end

--- Point the client's auto-run at a direction (a displacement in addon axes), or stop it.
function W.run(dx, dz, dy)
    pcall(function ()
        local f = AshitaCore:GetMemoryManager():GetAutoFollow()
        if dx == nil then
            f:SetIsAutoRunning(0)
            f:SetFollowDeltaX(0); f:SetFollowDeltaY(0); f:SetFollowDeltaZ(0)
            return
        end
        -- No entity to follow: the delta alone steers.  Memory axes: X, then Y for the other
        -- horizontal axis (this addon's z), then Z for height (this addon's y) -- see below.
        f:SetFollowTargetIndex(0); f:SetFollowTargetServerId(0)
        f:SetFollowDeltaX(dx); f:SetFollowDeltaY(dz); f:SetFollowDeltaZ(dy or 0)
        f:SetIsAutoRunning(1)
    end)
end

--- One frame.  `w` is the world snapshot (x, z, y, zone, yaw).  Returns true on arrival.
function W.update(w)
    if not W.active then return false end
    if w == nil or w.x == nil or w.zone == nil then
        -- Zoning: no position for a while.  Nothing here is stuck; forget the progress
        -- check so the load time is not counted against the walk.
        W.last, W.stuck_pos, W.stuck_since = nil, nil, nil
        return false
    end
    if W.zone_seen ~= w.zone then
        W.zone_seen = w.zone
        W.stuck_pos, W.stuck_since, W.last_wp, W.last_tick = nil, nil, nil, nil
    end
    local idx = player_index()
    if idx == nil then W.last = nil; return false end

    local now = now_s()
    local dt = (W.last ~= nil) and (now - W.last) or 0
    W.last = now
    if dt <= 0 or dt > 0.5 then return false end     -- a hitch or a zone: skip, do not leap

    -- Progress check: has the entity actually gone anywhere since we last looked?
    -- Progress means the target got nearer, not that the position changed: a runner
    -- pressed against a wall bounces half a yalm either way all day (measured 2026-08-29).
    local t = W.target
    local remaining = U.dist(w.x, w.z, t.x, t.z)
    if W.stuck_pos == nil or (W.mode ~= 'follow' and U.dist(w.x, w.z, W.stuck_pos.x, W.stuck_pos.z) > 0.3)
       or (W.mode == 'follow' and remaining < (W.best_remaining or math.huge) - 0.5) then
        W.stuck_pos, W.stuck_since = { x = w.x, z = w.z }, now
        W.best_remaining = remaining
        if W.nudge ~= 0 and U.dist(w.x, w.z, W.stuck_pos.x, W.stuck_pos.z) > 3 then W.nudge = 0 end
    elseif now - W.stuck_since > W.stuck_limit then
        W.stop(('stuck at (%.1f, %.1f)'):format(w.x, w.z))
        return false
    end
    -- The client's own runner turns before it moves, so give it longer before calling
    -- the walk stuck; the entity writes are instant and need no such grace.
    local stuck = (now - W.stuck_since) > ((W.mode == 'follow') and 2.5 or 0.4)
    if stuck then
        -- Each half-second stuck: aim one point further and swing to the other side.
        local n = math.floor((now - W.stuck_since) / 0.5)
        W.nudge = (n % 2 == 0) and n or -n
    end

    if remaining <= W.arrive then
        W.stop('arrived')
        return true
    end

    -- Follow the drawn path when there is one; otherwise straight at the target.  The last
    -- few yalms go to the target itself, height included: a gate's trigger area is a box
    -- a couple of yalms tall, and arriving at the grid's idea of the floor can miss it.
    local points = (remaining > 4) and Path.to(w, t) or nil
    local nx, nz, ny = t.x, t.z, t.y
    if points ~= nil and #points >= 2 then
        local i = Path.nearest_index(points, w.x, w.z, w.y)
        -- Aim past the nearest point so a point already reached does not pin us in place.
        local j = i
        while j < #points and U.dist(w.x, w.z, points[j].x, points[j].z) < 1.5 do j = j + 1 end
        if stuck then j = math.min(#points, j + math.abs(W.nudge)) end
        if W.mode == 'server' or W.mode == 'follow' then
            -- Aim at the far end of the straight stretch ahead, not the next sample: the
            -- server walks a straight line anyway, and one command per corner is quieter
            -- than one every six yalms.  A point counts as "on the stretch" while every
            -- sample between here and it lies within a yalm of the straight line to it.
            -- The client's runner also goes straight at its aim, so the stretch is kept
            -- short for it: a corner cut by six yalms is a wall.
            local k = j
            local far = (W.mode == 'server') and 60 or 6
            while k < #points do
                local cx, cz = points[k + 1].x, points[k + 1].z
                if U.dist(w.x, w.z, cx, cz) > far then break end
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

    if W.mode == 'follow' then
        -- Hand the client a displacement several yalms long in the direction of the next
        -- waypoint and let it run.  Re-aimed every frame, so corners are taken as the path
        -- turns; the sidestep above is already folded into dx/dz.
        -- Horizontal only.  Measured 2026-08-29: a vertical component the client cannot
        -- run up (the grid's floor and the entity's disagree by a few yalms on stairs and
        -- ramps) makes it cancel auto-run outright; left at 0 it climbs by its own collision.
        -- Re-aimed every frame: the runner steers toward wherever the delta points now,
        -- so corners are taken as the path turns.
        local reach = math.min(d, 6)
        W.run(dx / d * reach, dz / d * reach, 0)
        -- Where the client cannot get through -- a stair the grid routes across a floor
        -- boundary, a doorway a hand too narrow -- the local world's server carries it a
        -- few yalms along the path (`!walkto`, as 'server' mode does for the whole way),
        -- and the runner takes over again.  Never fires on a hosted world: nothing there
        -- answers `!walkto`, and Walk.start is gated behind /vg walk allow anyway.
        if stuck and (W.last_tick == nil or now - W.last_tick > 3) then
            local ax, az, ay = nx, nz, ny
            if points ~= nil and #points >= 2 then
                local i = Path.nearest_index(points, w.x, w.z, w.y)
                local k = math.min(#points, i + 3)
                ax, az, ay = points[k].x, points[k].z, points[k].y
            end
            W.last_tick, W.nudges = now, (W.nudges or 0) + 1
            pcall(function ()
                AshitaCore:GetChatManager():QueueCommand(-1,
                    ('!walkto %.2f %.2f %.2f %.1f'):format(ax, ay or (w.y or 0), az, W.speed))
            end)
        end
        W.walked = W.walked + W.speed * dt
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
        return ('walk: to (%.1f, %.1f)%s, %.0f yalms walked%s')
            :format(t.x, t.z, W.label and (' ' .. W.label) or '', W.walked,
                    ((W.nudges or 0) > 0) and (', ' .. W.nudges .. ' server nudges') or '')
    end
    return 'walk: idle' .. (W.reason and (' (' .. W.reason .. ')') or '')
end

return W
