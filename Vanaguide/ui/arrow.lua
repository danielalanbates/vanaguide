-- Vanaguide :: ui/arrow.lua
-- The arrow.  It points at whatever the router recommends and says how far away it is.
--
-- It is drawn with plain lines on ImGui's foreground draw list rather than a texture,
-- because that is the one drawing primitive every Ashita build on every renderer this
-- project supports has been seen to do (the Mac port runs the client through DXVK, where
-- fancier paths are not guaranteed).  Everything below is guarded: if a call is missing,
-- the arrow quietly stops drawing instead of throwing once per frame.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

--- Ashita v4 exposes ImGui as a *module*, not a global: `require('imgui')`. Reading _G.imgui
--- gave nil in-game, so the window and the arrow silently never drew while every command
--- worked — measured 2026-08-22, `/vg status` reporting `imgui=false`. Cached on first use so
--- the offline harness can still inject a fake by setting `A.imgui_module`.
local A_imgui
local function imgui_module()
    if A_imgui ~= nil then return A_imgui end
    if _G.imgui ~= nil then A_imgui = _G.imgui; return A_imgui end
    local ok, m = pcall(require, 'imgui')
    if ok then A_imgui = m end
    return A_imgui
end
local A = {
    screen = { w = 1280, h = 720 },
    calibration = 1,     -- see docs/ARROW.md: +1 or -1, whichever makes it point right
    offset = 0,          -- radians added to the bearing, for the same reason
    scale = 0.6,         -- 1.0 was the original size; /vg arrow size <n> changes it
    locked = true,       -- ImGuiWindowFlags_NoMove; /vg arrow unlock to drag it

    -- Where the arrow sits, as a fraction of the screen.
    --
    -- It used to sit low, which put it in the busiest part of the screen: the chat log, the
    -- party list and the target bar all live down there, and the one thing you are meant to
    -- glance at was competing with all of them. Daniel asked for it at the top, under the
    -- game's command bar (2026-08-25), which is empty screen on every layout.
    rel_x = 0.5,
    rel_y = 0.12,
}

-- ImGui packs colours as 0xAABBGGRR -- alpha, blue, green, red -- not ARGB. Written the
-- other way round, the "far" blue came out orange in-game (measured 2026-08-22).
local COL_NEAR  = 0xFF33DD33   -- green
local COL_MID   = 0xFF33DDDD   -- yellow-ish
local COL_FAR   = 0xFFFF9933   -- blue
local COL_SHELL = 0x88000000

local function colour_for(distance)
    if distance == nil then return COL_FAR end
    if distance <= 15 then return COL_NEAR end
    if distance <= 60 then return COL_MID end
    return COL_FAR
end

local function rotate(cx, cy, x, y, a)
    local c, s = math.cos(a), math.sin(a)
    return cx + x * c - y * s, cy + x * s + y * c
end

--- Draw the arrow.  `bearing` is radians relative to the way the player faces, 0 = ahead.
--- Returns false when it could not draw, so the caller can stop asking.
function A.draw(bearing, distance, label, sub)
    local imgui = imgui_module()
    if imgui == nil or imgui.GetForegroundDrawList == nil then return false end

    -- The draw used to be wrapped in a bare pcall, so any mistake inside it -- a missing
    -- ImGui flag constant, a bad argument -- showed up as an arrow that simply was not there,
    -- with nothing anywhere to say why. Keep the last error so `/vg arrow` can report it.

    local ok, err = pcall(function()
        -- The arrow is drawn inside a real ImGui window, not straight onto the foreground
        -- draw list, and that is the whole reason it can be dragged.
        --
        -- This is how HXUI does every one of its HUD pieces (addons/HXUI/expbar.lua and its
        -- siblings): an undecorated, transparent, auto-sized ImGui window, with
        -- ImGuiWindowFlags_NoMove added only while positions are locked. Unlocked, ImGui's own
        -- window dragging moves it -- and ImGui drags from `io.MousePos` / `io.MouseDown`,
        -- which is the ONE input path that works under wine here. The other path, the WNDPROC
        -- 'mouse' event that libs/primitives.lua and libs/fonts.lua rely on, is dead on this
        -- build: winecursor posts messages and Ashita never raises the event
        -- (HorizonXI-on-Mac docs/MOUSE.md). That is exactly why HXUI's bars can be dragged
        -- and `timers`/`tparty` cannot.
        --
        -- Position persistence comes free with it: ImGui writes `[Window][Vanaguide Arrow]
        -- Pos=` into config/imgui.ini itself, so there is no save code here and no
        -- `/vg arrow move 50 12` to type.
        local W, H = 150, 110          -- room for the arrow plus its two lines of text
        local flags = bit.bor(
            ImGuiWindowFlags_NoDecoration,
            ImGuiWindowFlags_NoBackground,
            ImGuiWindowFlags_NoFocusOnAppearing,
            ImGuiWindowFlags_NoNav,
            ImGuiWindowFlags_NoBringToFrontOnFocus);
        if (A.locked ~= false) then
            flags = bit.bor(flags, ImGuiWindowFlags_NoMove);
        end

        -- Only place it ourselves the first time. After that ImGui remembers, and forcing the
        -- position every frame would undo the drag on the very next one.
        imgui.SetNextWindowPos(
            { (A.pos_x or (A.screen.w / 2)) - W / 2, (A.pos_y or (A.screen.h * A.rel_y)) - H / 2 },
            ImGuiCond_FirstUseEver);
        imgui.SetNextWindowSize({ W, H }, ImGuiCond_FirstUseEver);

        if (not imgui.Begin('Vanaguide Arrow', true, flags)) then imgui.End(); return; end

        -- While unlocked the window is invisible and unhittable without something to grab, so
        -- give it a faint frame -- the same courtesy HXUI's unlocked bars get.
        local wx, wy = imgui.GetWindowPos();
        local dl = imgui.GetWindowDrawList();
        if (A.locked == false) then
            dl:AddRect({ wx, wy }, { wx + W, wy + H }, 0x66FFFFFF, 4.0);
        end

        local cx, cy = wx + W / 2, wy + 44

        -- Screen angle.  Zero bearing draws straight up.  The screen's y grows *downward*,
        -- so a positive (leftward) bearing has to become a negative screen rotation or the
        -- arrow comes out mirrored — verified by tools/render_arrow.lua.
        local a = -(bearing or 0) * A.calibration + A.offset
        local colour = colour_for(distance)

        -- The arrow's shape is written at its original size and then scaled, so `A.scale`
        -- is the only number to change.  It was hard-coded pixels until 2026-08-25, which
        -- meant "make it smaller" had no answer and a 2560-wide window got the same arrow
        -- as a 640-wide one.
        local k = A.scale or 1.0
        local tipx, tipy = rotate(cx, cy, 0, -34 * k, a)
        local lx, ly     = rotate(cx, cy, -20 * k, 16 * k, a)
        local rx, ry     = rotate(cx, cy, 20 * k, 16 * k, a)
        local bx, by     = rotate(cx, cy, 0, 4 * k, a)

        -- Keep the outline readable when the arrow is small: a 6px shell around a 3px line
        -- swallows the line entirely once k drops much below a half.
        local shell_w = math.max(2.5, 6 * k)
        local line_w  = math.max(1.5, 3 * k)
        dl:AddLine({ tipx, tipy }, { lx, ly }, COL_SHELL, shell_w)
        dl:AddLine({ tipx, tipy }, { rx, ry }, COL_SHELL, shell_w)
        dl:AddLine({ lx, ly }, { bx, by }, COL_SHELL, shell_w)
        dl:AddLine({ rx, ry }, { bx, by }, COL_SHELL, shell_w)

        dl:AddLine({ tipx, tipy }, { lx, ly }, colour, line_w)
        dl:AddLine({ tipx, tipy }, { rx, ry }, colour, line_w)
        dl:AddLine({ lx, ly }, { bx, by }, colour, line_w)
        dl:AddLine({ rx, ry }, { bx, by }, colour, line_w)

        if dl.AddText ~= nil then
            -- The text rides under the arrow, so it follows the arrow's size down.
            local ty = cy + 22 * k + 6
            if label ~= nil then dl:AddText({ cx - 60, ty }, colour, label) end
            if sub ~= nil then dl:AddText({ cx - 60, ty + 16 }, 0xFFCCCCCC, sub) end
        end

        -- Remember where the drag left it, so /vg arrow still reports a real position.
        A.pos_x, A.pos_y = wx + W / 2, wy + 44
        A.rel_x = A.pos_x / math.max(1, A.screen.w)
        A.rel_y = A.pos_y / math.max(1, A.screen.h)
        imgui.End()
    end)
    A.last_error = (not ok) and tostring(err) or nil
    return ok
end

--- Remember the viewport so the arrow sits in the same place at any resolution.
---
--- Position is stored as a *fraction* of the screen, not pixels: the same 0.5, 0.28 puts the
--- arrow in the same place on a 640x480 test world and a 4K one, and a resolution change
--- cannot leave it off the edge.
function A.set_viewport(w, h)
    if w ~= nil and w > 0 then A.screen.w = w end
    if h ~= nil and h > 0 then A.screen.h = h end
    A.pos_x = (A.rel_x or 0.5) * A.screen.w
    A.pos_y = (A.rel_y or 0.12) * A.screen.h
end

--- Move the arrow. `x` and `y` are fractions of the screen (0.5, 0.28 is the default), so a
--- position set at one resolution still makes sense at another.
function A.move(x, y)
    if x ~= nil then A.rel_x = math.max(0.02, math.min(0.98, x)) end
    if y ~= nil then A.rel_y = math.max(0.02, math.min(0.98, y)) end
    A.set_viewport(A.screen.w, A.screen.h)
    return A.rel_x or 0.5, A.rel_y or 0.12
end

return A
