-- Vanaguide :: tools/test_line_target.lua
-- The line leads to ONE point of interest at a time, and only the first stretch of it shows.
--   luajit tools/test_line_target.lua        (from the repository root; exits non-zero on failure)
-- Copyright (c) 2026 Bates LLC.  All rights reserved.
package.path = 'Vanaguide/?.lua;Vanaguide/?/init.lua;' .. package.path
dofile('tools/stubs.lua')

local pass, fail = 0, 0
local function ok(c, what) if c then pass = pass + 1 else fail = fail + 1; print('FAIL: ' .. what) end end

-- A fake ImGui that records what is drawn.  Screen space == world space (x, z), so every
-- recorded point can be measured in yalms from the player.
local drawn = { lines = {}, rings = {}, dots = {} }
local dl = {
    AddLine = function(_, a, b) drawn.lines[#drawn.lines + 1] = { a, b } end,
    AddCircleFilled = function(_, c) drawn.dots[#drawn.dots + 1] = c end,
    AddCircle = function(_, c) drawn.rings[#drawn.rings + 1] = c end,
    AddText = function() end,
}
_G.imgui = { GetBackgroundDrawList = function() return dl end }

local Pr = require('ui.project')
Pr.refresh = function() return true end
Pr.width, Pr.height = 100000, 100000
Pr.point = function(x, z) return x, z, 1 end
Pr.segment = function(ax, az, _, bx, bz) return ax, az, bx, bz end
Pr.on_screen = function() return true end

local U    = require('core.util')
local Path = require('routing.path')
local L    = require('ui.line')
local R    = require('routing.router')

local function reset() drawn.lines, drawn.rings, drawn.dots = {}, {}, {} end
local function farthest(px, pz)
    local m = 0
    for _, s in ipairs(drawn.lines) do
        for _, p in ipairs(s) do m = math.max(m, U.dist(px, pz, p[1], p[2])) end
    end
    for _, p in ipairs(drawn.dots) do m = math.max(m, U.dist(px, pz, p[1], p[2])) end
    return m
end

-- 1. One target from the router: the step marker in its zone ...
local step = { kind = 'talk', text = 't', zone = 230, pos = { x = 100, z = 0, r = 8 } }
R.forget()
local rec = R.recommend(step, { zone = 230, x = 0, z = 0, y = 0 })
ok(rec.mode == 'here' and rec.target and rec.target.x == 100 and rec.target.z == 0,
   'in the step zone the only target is the step marker')

-- ... and the next zone line when the step is somewhere else, never the step marker itself.
R.forget()
local rec2 = R.recommend(step, { zone = 231, x = 0, z = 0, y = 0 })
ok(rec2.mode == 'travel', 'another zone means travel mode')
ok(rec2.target == nil or not (rec2.target.x == 100 and rec2.target.z == 0),
   'from another zone the line does not aim at the far-away step marker')

-- 2. Straight line to a far target: nothing drawn past the horizon, no ring at the horizon.
L.enabled, L.style, L.horizon = true, 'both', 40
Path.provider = nil
reset()
L.draw({ zone = 230, x = 0, z = 0, y = 0 }, { x = 100, z = 0 }, 'far')
ok(#drawn.lines > 0 and #drawn.dots > 0, 'far target: line and dots are drawn')
ok(farthest(0, 0) <= 40.5, ('far target: nothing drawn beyond 40 yalms (got %.1f)'):format(farthest(0, 0)))
ok(#drawn.rings == 0, 'far target: no destination ring out at the horizon')

-- 3. Near target: the whole line shows and the ring marks it.
Path.to(nil, nil) -- no-op, keeps the module warm
reset()
L.draw({ zone = 230, x = 0, z = 0, y = 0 }, { x = 20, z = 0 }, 'near')
ok(#drawn.rings > 0, 'near target: the destination ring is drawn')
ok(farthest(0, 0) <= 20.5, 'near target: the line ends at the target')

-- 4. A bent navmesh route: still cut at 40 yalms of *route*, and all of it heads to one place.
Path.provider = function(_, x1, z1, _, x2, z2)
    return { { x = x1, z = z1, y = 0 }, { x = 0, z = 30, y = 0 }, { x = x2, z = z2, y = 0 } }
end
reset()
L.draw({ zone = 231, x = 0, z = 0, y = 0 }, { x = 200, z = 30 }, 'bent')
ok(#drawn.lines > 0, 'bent route: drawn')
ok(farthest(0, 0) <= 40.5, ('bent route: cut within 40 yalms (got %.1f)'):format(farthest(0, 0)))
ok(#drawn.rings == 0, 'bent route: no ring before the target is within reach')

print(('%d passed, %d failed'):format(pass, fail))
os.exit(fail == 0 and 0 or 1)
