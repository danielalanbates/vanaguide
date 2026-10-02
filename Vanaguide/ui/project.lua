-- Vanaguide :: ui/project.lua
-- World coordinates to screen pixels, so something can be drawn *in the world* rather than
-- in a corner of it.
--
-- The camera's matrices are not in FFXI's memory anywhere this project is willing to poke;
-- they are in the Direct3D device, and the device will hand them over:
-- `IDirect3DDevice8::GetTransform(D3DTS_VIEW)` and `D3DTS_PROJECTION`.  That is the same
-- call `targetlines` (Jyouya) makes every frame to draw its arcs, and the arithmetic below
-- is the arithmetic in its `helpers.lua`, rewritten in plain Lua numbers instead of ffi
-- vectors: this addon runs with the JIT off (Ashita 4.3 + Wine, see Vanaguide.lua), so
-- forty `ffi.new` allocations a frame is forty allocations a frame, and the same maths over
-- sixteen local numbers costs nothing.
--
-- Whether GetTransform answers at all under the Mac port's d3d8 -> d3d8to9 -> DXVK chain was
-- an open question when this was written (docs/PATHWAYS.md item 5).  Everything here is
-- guarded and counts its failures, so the answer is "the line quietly does not draw", never
-- "the addon throws once a frame".
--
-- AXES.  D3D world space here is (x, height, z) -- the client's own order, confirmed by
-- targetlines reading x at actor+0x678, the height at +0x67C and z at +0x680 and passing
-- them in that order.  Everything else in this project writes (x, z, y) with the height
-- last (core/util.lua), so the swap happens at this boundary and nowhere else.  FFXI's
-- height axis points *down*: a smaller y is higher up.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local Pr = {
    width = 1280, height = 720,
    ok = false,          -- did the last refresh produce matrices?
    fails = 0,           -- consecutive failures; the caller gives up after enough
    frames = 0,          -- successful refreshes, for /vg status
    reason = 'not tried',
}

-- The combined view * projection matrix, as sixteen numbers.  Row-vector convention: a point
-- is a row and multiplies from the left, which is what Direct3D's fixed pipeline uses and
-- what the matrices come out of the device as.
local m11, m12, m13, m14 = 1, 0, 0, 0
local m21, m22, m23, m24 = 0, 1, 0, 0
local m31, m32, m33, m34 = 0, 0, 1, 0
local m41, m42, m43, m44 = 0, 0, 0, 1

function Pr.set_viewport(w, h)
    if w ~= nil and w > 0 then Pr.width = w end
    if h ~= nil and h > 0 then Pr.height = h end
end

--- Combine a view and a projection matrix.  Either may be an ffi D3DMATRIX or a plain table
--- with the same `_11` .. `_44` field names, which is how the offline tests drive it.
function Pr.set_view_projection(v, p)
    if v == nil or p == nil then return false end
    local a11, a12, a13, a14 = v._11, v._12, v._13, v._14
    local a21, a22, a23, a24 = v._21, v._22, v._23, v._24
    local a31, a32, a33, a34 = v._31, v._32, v._33, v._34
    local a41, a42, a43, a44 = v._41, v._42, v._43, v._44
    local b11, b12, b13, b14 = p._11, p._12, p._13, p._14
    local b21, b22, b23, b24 = p._21, p._22, p._23, p._24
    local b31, b32, b33, b34 = p._31, p._32, p._33, p._34
    local b41, b42, b43, b44 = p._41, p._42, p._43, p._44
    if a11 == nil or b11 == nil then return false end

    m11 = a11 * b11 + a12 * b21 + a13 * b31 + a14 * b41
    m12 = a11 * b12 + a12 * b22 + a13 * b32 + a14 * b42
    m13 = a11 * b13 + a12 * b23 + a13 * b33 + a14 * b43
    m14 = a11 * b14 + a12 * b24 + a13 * b34 + a14 * b44

    m21 = a21 * b11 + a22 * b21 + a23 * b31 + a24 * b41
    m22 = a21 * b12 + a22 * b22 + a23 * b32 + a24 * b42
    m23 = a21 * b13 + a22 * b23 + a23 * b33 + a24 * b43
    m24 = a21 * b14 + a22 * b24 + a23 * b34 + a24 * b44

    m31 = a31 * b11 + a32 * b21 + a33 * b31 + a34 * b41
    m32 = a31 * b12 + a32 * b22 + a33 * b32 + a34 * b42
    m33 = a31 * b13 + a32 * b23 + a33 * b33 + a34 * b43
    m34 = a31 * b14 + a32 * b24 + a33 * b34 + a34 * b44

    m41 = a41 * b11 + a42 * b21 + a43 * b31 + a44 * b41
    m42 = a41 * b12 + a42 * b22 + a43 * b32 + a44 * b42
    m43 = a41 * b13 + a42 * b23 + a43 * b33 + a44 * b43
    m44 = a41 * b14 + a42 * b24 + a43 * b34 + a44 * b44

    Pr.ok = true
    Pr.fails = 0
    Pr.frames = Pr.frames + 1
    Pr.reason = 'ok'
    return true
end

--- Ask the device for this frame's camera.  Returns true when it answered.
--- `device_fn` is injectable so the tests never touch d3d8.
function Pr.refresh(device_fn)
    local ok, err = pcall(function ()
        local d3d = require('d3d8')
        local ffi = require('ffi')
        local C = ffi.C
        local dev = (device_fn ~= nil) and device_fn() or d3d.get_device()
        if dev == nil then error('no device') end
        local rv, view = dev:GetTransform(C.D3DTS_VIEW)
        local rp, proj = dev:GetTransform(C.D3DTS_PROJECTION)
        if rv ~= 0 or rp ~= 0 or view == nil or proj == nil then
            error(('GetTransform returned %s/%s'):format(tostring(rv), tostring(rp)))
        end
        if not Pr.set_view_projection(view, proj) then error('matrix had no fields') end
    end)
    if not ok then
        Pr.ok = false
        Pr.fails = Pr.fails + 1
        Pr.reason = tostring(err)
    end
    return Pr.ok
end

--- One point.  Takes guide axes (x, z horizontal, y height) and returns screen x, screen y
--- and the clip-space w.  **w <= 0 means the point is behind the camera** and the screen
--- coordinates are meaningless -- they mirror, which is how a line to a target behind you
--- ends up drawn across the sky.
function Pr.point(x, z, y)
    local cx = x * m11 + y * m21 + z * m31 + m41
    local cy = x * m12 + y * m22 + z * m32 + m42
    local cw = x * m14 + y * m24 + z * m34 + m44
    if cw == 0 then return 0, 0, 0 end
    local inv = 1 / cw
    return (cx * inv + 1) * 0.5 * Pr.width, (1 - cy * inv) * 0.5 * Pr.height, cw
end

-- Anything closer than this to the camera plane projects to enormous coordinates; the near
-- plane is where a segment gets cut rather than where it gets thrown away, so a path that
-- starts at your own feet still draws the part of itself you can see.
local NEAR = 0.05

--- A segment, clipped against the near plane.
--- Returns x1, y1, x2, y2 in screen pixels, or nil when the whole segment is behind you.
function Pr.segment(ax, az, ay, bx, bz, by)
    local _, _, aw = Pr.point(ax, az, ay)
    local _, _, bw = Pr.point(bx, bz, by)
    if aw <= NEAR and bw <= NEAR then return nil end
    if aw <= NEAR or bw <= NEAR then
        -- w is linear in the point, so the crossing is a plain interpolation.
        local t = (NEAR - aw) / (bw - aw)
        local cx = ax + (bx - ax) * t
        local cz = az + (bz - az) * t
        local cy = ay + (by - ay) * t
        if aw <= NEAR then ax, az, ay = cx, cz, cy else bx, bz, by = cx, cz, cy end
    end
    local sx1, sy1 = Pr.point(ax, az, ay)
    local sx2, sy2 = Pr.point(bx, bz, by)
    return sx1, sy1, sx2, sy2
end

--- True when the projected point is somewhere on the screen (with a margin, so a marker
--- half off the edge still draws).
function Pr.on_screen(sx, sy, margin)
    margin = margin or 64
    return sx > -margin and sy > -margin
       and sx < Pr.width + margin and sy < Pr.height + margin
end

return Pr
