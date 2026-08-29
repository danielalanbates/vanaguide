-----------------------------------
-- func: walkto
-- desc: Moves the player toward a point at run speed, a small step every 200 ms, until it
--       arrives or !walkto stop is issued.  Written for testing guide addons on a local
--       world (Vanaguide): the client on this Mac cannot be driven by input or memory, so
--       the server walks the character instead.  Local worlds only; never ship elsewhere.
-- usage: !walkto <x> <y> <z> [speed yalms/s]   |   !walkto stop
-----------------------------------

local commandObj = {}

commandObj.cmdprops =
{
    permission = 1,
    parameters = 's'
}

local function error(player, msg)
    player:printToPlayer(msg)
    player:printToPlayer('!walkto <x> <y> <z> [speed]  |  !walkto stop')
end

local function walkStep(player, tx, ty, tz, speed, gen, last)
    if player == nil or player:getLocalVar('walkto_gen') ~= gen then return end
    local px, py, pz = player:getXPos(), player:getYPos(), player:getZPos()
    local dx, dz = tx - px, tz - pz
    local d = math.sqrt(dx * dx + dz * dz)
    -- The timer's real period is coarser than asked: measured ~400 ms for a 200 ms request,
    -- and os.clock() here is CPU time, which is useless for pacing (it made 5 yalms/s come
    -- out at 1.4).  Size the hop for the period that was measured.
    local now = 0
    local hop = speed * 0.8
    if d <= hop then
        player:setPos(tx, ty, tz, player:getRotPos())
        player:setLocalVar('walkto_gen', 0)
        player:printToPlayer(('walkto: arrived (%.1f, %.1f, %.1f)'):format(tx, ty, tz))
        return
    end
    local nx, nz = px + dx / d * hop, pz + dz / d * hop
    local ny = py + (ty - py) * (hop / d)
    -- Face the way we are going.  FFXI rotation is 0..255, 0 = east, counter-clockwise.
    local rot = math.floor((math.atan2(-dz, dx) / (2 * math.pi)) * 256) % 256
    player:setPos(nx, ny, nz, rot)
    player:timer(200, function(p) walkStep(p, tx, ty, tz, speed, gen, now) end)
end

commandObj.onTrigger = function(player, arg)
    if arg == nil then error(player, 'where to?') return end
    local args = utils.splitArg(arg)
    if args[1] == 'stop' then
        player:setLocalVar('walkto_gen', 0)
        player:printToPlayer('walkto: stopped')
        return
    end
    local x, y, z = tonumber(args[1]), tonumber(args[2]), tonumber(args[3])
    local speed = tonumber(args[4] or '') or 5
    if x == nil or y == nil or z == nil then error(player, 'x y z, please') return end
    local gen = (player:getLocalVar('walkto_gen') % 100000) + 1
    player:setLocalVar('walkto_gen', gen)
    walkStep(player, x, y, z, speed, gen)
end

return commandObj
