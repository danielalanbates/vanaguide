-- Vanaguide :: tools/render_line.lua
-- Draws ui/line.lua through a fake ImGui draw list and a hand-built camera, and writes
-- docs/line-geometry.svg.
--
-- The same trick tools/render_arrow.lua uses, and for the same reason: it is the real
-- drawing code with real numbers, so the picture catches a mirrored axis or a line that
-- wanders off to the horizon before anybody has to launch a client.  It does NOT prove the
-- game's own view matrix looks like the one built here; see docs/LINE.md for the in-game
-- check.
--
-- The camera is a left-handed look-at, with "up" written as (0,-1,0) because FFXI's height
-- axis points down -- the same reason ui/line.lua *subtracts* its lift.
--
--   luajit tools/render_line.lua
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

package.path = 'Vanaguide/?.lua;' .. package.path

local recorded = {}
local draw_list = {
    AddLine = function(_, a, b, colour, width)
        recorded[#recorded + 1] = { kind = 'line', a[1], a[2], b[1], b[2], colour, width }
    end,
    AddCircleFilled = function(_, at, r, colour)
        recorded[#recorded + 1] = { kind = 'dot', at[1], at[2], r, colour }
    end,
    AddCircle = function(_, at, r, colour, _, width)
        recorded[#recorded + 1] = { kind = 'ring', at[1], at[2], r, colour, width }
    end,
    AddText = function(_, at, colour, text)
        recorded[#recorded + 1] = { kind = 'text', at[1], at[2], colour, text = text }
    end,
}
_G.imgui = { GetForegroundDrawList = function() return draw_list end }

local Pr   = require('ui.project')
local Path = require('routing.path')
local Line = require('ui.line')

local W, H = 640, 400

-- ---- a camera ------------------------------------------------------------------
local function normalize(v)
    local l = math.sqrt(v[1] * v[1] + v[2] * v[2] + v[3] * v[3])
    return { v[1] / l, v[2] / l, v[3] / l }
end
local function cross(a, b)
    return { a[2] * b[3] - a[3] * b[2], a[3] * b[1] - a[1] * b[3], a[1] * b[2] - a[2] * b[1] }
end
local function dot(a, b) return a[1] * b[1] + a[2] * b[2] + a[3] * b[3] end

--- Look-at, in D3D world order (x, height, z).
---
--- FFXI's world is right-handed with the height axis pointing *down*: LandSandBoat converts
--- to Detour, which is right-handed Y-up, by negating y and z, and negating two axes leaves
--- the handedness alone.  So screen-right is forward x up, not up x forward -- writing it the
--- left-handed way round produced a mirrored picture where a path bending right bent left,
--- which is exactly the bug tools/render_arrow.lua was built to catch for the arrow.
---
--- The resulting camera basis (right, up, forward) is left-handed, which is what the
--- left-handed projection matrix below expects.
local function look_at(eye, at, up)
    local z = normalize({ at[1] - eye[1], at[2] - eye[2], at[3] - eye[3] })
    local x = normalize(cross(z, up))
    local y = cross(x, z)
    return {
        _11 = x[1], _12 = y[1], _13 = z[1], _14 = 0,
        _21 = x[2], _22 = y[2], _23 = z[2], _24 = 0,
        _31 = x[3], _32 = y[3], _33 = z[3], _34 = 0,
        _41 = -dot(x, eye), _42 = -dot(y, eye), _43 = -dot(z, eye), _44 = 1,
    }
end

local function perspective(fov_y, aspect, zn, zf)
    local h = 1 / math.tan(fov_y / 2)
    return {
        _11 = h / aspect, _12 = 0, _13 = 0, _14 = 0,
        _21 = 0, _22 = h, _23 = 0, _24 = 0,
        _31 = 0, _32 = 0, _33 = zf / (zf - zn), _34 = 1,
        _41 = 0, _42 = 0, _43 = -zn * zf / (zf - zn), _44 = 0,
    }
end

-- The player stands at the origin; the camera is eight yalms behind and four above, which is
-- roughly where FFXI puts it.  Height is negative-up, hence the minus signs.
local eye = { 0, -4, -8 }
local at  = { 0, -1.2, 4 }
Pr.set_viewport(W, H)
assert(Pr.set_view_projection(look_at(eye, at, { 0, -1, 0 }),
                              perspective(math.rad(52), W / H, 0.2, 800)))

-- ---- the paths to draw ---------------------------------------------------------
local CASES = {
    {
        name = 'straight ahead, 90 yalms',
        world = { zone = 230, x = 0, z = 0, y = 0, yaw = 0 },
        target = { x = 0, z = 90, y = 0 },
        provider = nil,
    },
    {
        name = 'around a corner (a provider bends it)',
        world = { zone = 230, x = 0, z = 0, y = 0, yaw = 0 },
        target = { x = 45, z = 70, y = 0 },
        provider = function (_, x1, z1, y1, x2, z2, y2)
            return {
                { x = x1, z = z1, y = y1 },
                { x = 0,  z = 34, y = y1 },
                { x = 20, z = 46, y = y1 - 1 },
                { x = x2, z = z2, y = y2 },
            }
        end,
    },
    {
        name = 'starting behind the camera, climbing',
        world = { zone = 230, x = 0, z = 0, y = 0, yaw = 0 },
        target = { x = -30, z = 60, y = -14 },
        provider = nil,
    },
}

local function svg_colour(c)
    -- ImGui packs 0xAABBGGRR.
    local r = c % 256
    local g = math.floor(c / 256) % 256
    local b = math.floor(c / 65536) % 256
    local a = math.floor(c / 16777216) % 256
    return ('rgba(%d,%d,%d,%.2f)'):format(r, g, b, a / 255)
end

-- Where the ground disappears: project a point a very long way off, on the ground.
local _, horizon = Pr.point(0, 100000, 0)

local out = {}
for i, case in ipairs(CASES) do
    Path.forget()
    Path.provider = case.provider
    recorded = {}
    Line.enabled = true
    -- The device is never asked: the matrices are already set, and refresh() would only
    -- fail.  Standing in for it keeps the drawing code exactly as the game runs it.
    Pr.refresh = function () return true end
    assert(Line.draw(case.world, case.target, 'the gate'), 'the line refused to draw: ' .. case.name)

    local body = { ('<rect width="%d" height="%d" fill="#0e1016"/>'):format(W, H),
                   ('<text x="10" y="20" fill="#8892a6" font-family="monospace" font-size="12">%s</text>')
                       :format(case.name),
                   -- The horizon, computed rather than guessed: a ground point at infinity.
                   -- With the camera pitched down it sits *above* the middle of the screen,
                   -- and anything standing on the ground has to draw below it.
                   ('<line x1="0" y1="%.0f" x2="%d" y2="%.0f" stroke="#22262f" stroke-width="1"/>')
                       :format(horizon, W, horizon) }
    for _, d in ipairs(recorded) do
        if d.kind == 'line' then
            body[#body + 1] = ('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f" stroke-linecap="round"/>')
                :format(d[1], d[2], d[3], d[4], svg_colour(d[5]), d[6])
        elseif d.kind == 'dot' then
            body[#body + 1] = ('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>')
                :format(d[1], d[2], d[3], svg_colour(d[4]))
        elseif d.kind == 'ring' then
            body[#body + 1] = ('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" stroke-width="%.1f"/>')
                :format(d[1], d[2], d[3], svg_colour(d[4]), d[5] or 1)
        elseif d.kind == 'text' then
            body[#body + 1] = ('<text x="%.1f" y="%.1f" fill="%s" font-family="monospace" font-size="12">%s</text>')
                :format(d[1], d[2] + 10, svg_colour(d[3]), d.text)
        end
    end
    out[i] = table.concat(body, '\n')
end
Path.provider = nil

-- Side by side rather than stacked: three panels one above the other make a picture nobody
-- can look at without scrolling, and the point of it is to be looked at.
local total_w = W * #CASES
local svg = { ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">')
                  :format(total_w, H, total_w, H) }
for i, body in ipairs(out) do
    svg[#svg + 1] = ('<g transform="translate(%d,0)">%s</g>'):format((i - 1) * W, body)
end
svg[#svg + 1] = '</svg>'

local f = assert(io.open('docs/line-geometry.svg', 'w'))
f:write(table.concat(svg, '\n'))
f:close()
print(('wrote docs/line-geometry.svg  (%d paths)'):format(#CASES))
