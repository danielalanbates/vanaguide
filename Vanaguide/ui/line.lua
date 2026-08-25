-- Vanaguide :: ui/line.lua
-- The line on the ground.
--
-- An arrow tells you a direction.  A line tells you a *route*: it bends around the corner
-- before you get to the corner, and you can see at a glance whether the next thing is up the
-- road or through the gate on the left.  That is the one piece of Zygor this project did not
-- have, and it is the thing people mean when they say a guide "just shows you where to go".
--
-- Optional, and off is a real option: `/vg line off`.  It draws on ImGui's *background* draw
-- list -- over the game, under every ImGui window -- so a long path does not scribble across
-- the guide window it is meant to explain; seen in-game at 640x480, where a 1613-yalm line
-- crossed the step text.  There is no depth buffer either way, so the line is visible
-- *through* terrain: a feature when you are working out where a path goes behind a hill, a
-- distraction when you are not.
--
-- It costs one GetTransform pair per frame and about forty AddLine calls.  If the device
-- will not hand over its matrices (the Mac port's d3d8 -> d3d8to9 -> DXVK chain was untested
-- when this was written), the line turns itself off after a few tries and `/vg status` says
-- why, rather than throwing once a frame forever.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local Pr   = require('ui.project')
local Path = require('routing.path')
local U    = require('core.util')

--- See ui/arrow.lua: ImGui is a module in Ashita v4, not a global.
local cached_imgui
local function imgui_module()
    if cached_imgui ~= nil then return cached_imgui end
    if _G.imgui ~= nil then cached_imgui = _G.imgui; return cached_imgui end
    local ok, m = pcall(require, 'imgui')
    if ok then cached_imgui = m end
    return cached_imgui
end

-- ImGui packs colour as 0xAABBGGRR -- alpha, blue, green, red.  Written as ARGB the "far"
-- blue comes out orange, which is how ui/arrow.lua found out.
-- Muted on purpose. The first pass used fully saturated primaries, and on the ground at
-- speed that reads as a neon stripe painted over the world rather than a hint about where to
-- walk -- "the line is too bold colored" (Daniel, 2026-08-25). These are the same three hues
-- pulled toward the background: still instantly distinguishable from each other and from
-- Vana'diel's greens and greys, without shouting over the game.
local COL_NEAR  = 0x6FBF6F
local COL_MID   = 0x7FC8C8
local COL_FAR   = 0xC89A6F
local COL_SHELL = 0x44000000   -- a lighter shell, to match the lighter line

local L = {
    enabled = true,
    style = 'both',        -- 'solid' | 'dots' | 'both'
    width = 4,             -- pixels at the player's feet; tapers with distance
    alpha = 0.55,   -- was 0.85; see the colour note above
    -- Give up after this many consecutive frames where the device would not answer.  Three
    -- is enough to be sure and few enough that nobody sees three bad frames.
    give_up_after = 3,
    off_reason = nil,
    -- How high above the recorded ground the line floats, in yalms.  FFXI's height axis
    -- points down, so this is subtracted.  Half a yalm is enough to clear a paving stone
    -- and little enough that the line still reads as lying on the road.
    lift = 0.5,
}

local function with_alpha(rgb, a)
    local alpha = math.floor(math.max(0, math.min(1, a)) * 255)
    return alpha * 0x1000000 + rgb
end

local function colour_for(distance)
    if distance == nil then return COL_FAR end
    if distance <= 15 then return COL_NEAR end
    if distance <= 60 then return COL_MID end
    return COL_FAR
end

--- Draw the path to `target`.  `w` is the world snapshot; `target` is { x, z, y } in the
--- current zone, or nil for "nothing to draw".  Returns true if anything was drawn.
function L.draw(w, target, label)
    if not L.enabled then return false end
    local imgui = imgui_module()
    if imgui == nil or (imgui.GetBackgroundDrawList == nil and imgui.GetForegroundDrawList == nil) then
        L.off_reason = 'no ImGui draw list'
        return false
    end
    if w == nil or target == nil or w.x == nil then return false end

    if not Pr.refresh() then
        if Pr.fails >= L.give_up_after then
            L.enabled = false
            L.off_reason = 'the device would not give up its camera: ' .. tostring(Pr.reason)
        end
        return false
    end

    local points = Path.to(w, target)
    if points == nil or #points < 2 then return false end

    -- Start from the point the player is nearest, and put their own feet in front of it, so
    -- the line always begins under the player and never trails behind them.
    local start = Path.nearest_index(points, w.x, w.z)
    local live = { { x = w.x, z = w.z, y = w.y or points[start].y } }
    for i = start + 1, #points do live[#live + 1] = points[i] end
    if #live < 2 then live[#live + 1] = { x = target.x, z = target.z, y = target.y or w.y or 0 } end

    local total = U.dist(w.x, w.z, target.x, target.z)
    local rgb = colour_for(total)
    local ok = pcall(function ()
        -- Background, not foreground: windows draw on top of the line.  Older ImGui builds
        -- have only the foreground list, so fall back rather than refuse to draw.
        local dl = (imgui.GetBackgroundDrawList ~= nil) and imgui.GetBackgroundDrawList()
                                                        or imgui.GetForegroundDrawList()
        local n = #live
        local lift = L.lift
        -- Widths are in pixels, and a pixel is a different amount of screen on a 640x480 test
        -- world and a 4K one.  Scale by the height so the line is the same *thickness* on
        -- both, the way ui/arrow.lua positions itself by fraction rather than by pixel.
        local scale = math.max(0.5, math.min(3, Pr.height / 720))

        if L.style ~= 'dots' then
            for i = 1, n - 1 do
                local a, b = live[i], live[i + 1]
                local x1, y1, x2, y2 = Pr.segment(a.x, a.z, (a.y or 0) - lift,
                                                  b.x, b.z, (b.y or 0) - lift)
                if x1 ~= nil then
                    -- Near segments are wide and opaque, far ones thin and faint: the line
                    -- reads as going away from you rather than as a flat streak.
                    local t = (i - 1) / math.max(1, n - 1)
                    local wide = L.width * scale * (1 - 0.6 * t)
                    local fade = L.alpha * (1 - 0.45 * t)
                    dl:AddLine({ x1, y1 }, { x2, y2 }, COL_SHELL, wide + 2 * scale)
                    dl:AddLine({ x1, y1 }, { x2, y2 }, with_alpha(rgb, fade), wide)
                end
            end
        end

        if L.style ~= 'solid' and dl.AddCircleFilled ~= nil then
            -- Dots that crawl towards the target.  Direction is otherwise ambiguous on a
            -- line, and a still line and a moving one are read differently: one is scenery.
            local phase = (os.clock() * 1.4) % 1
            for i = 1, n do
                local p = live[i]
                local sx, sy, cw = Pr.point(p.x, p.z, (p.y or 0) - lift)
                if cw > 0.05 and Pr.on_screen(sx, sy) then
                    local t = (i - 1) / math.max(1, n - 1)
                    local pulse = ((i / 3) + phase) % 1
                    local r = (2.2 + 2.2 * (1 - pulse)) * (1 - 0.5 * t) * scale
                    dl:AddCircleFilled({ sx, sy }, r,
                        with_alpha(rgb, L.alpha * (1 - 0.4 * t) * (0.35 + 0.65 * (1 - pulse))), 8)
                end
            end
        end

        -- The destination itself: a ring on the ground with a post standing out of it, so it
        -- is findable when the ring is edge-on, plus how far away it is.
        local last = live[n]
        local gx, gy, gw = Pr.point(last.x, last.z, (last.y or 0) - lift)
        if gw > 0.05 then
            local top_x, top_y = Pr.point(last.x, last.z, (last.y or 0) - lift - 2.4)
            if dl.AddCircle ~= nil then
                dl:AddCircle({ gx, gy }, 9 * scale, COL_SHELL, 16, 4 * scale)
                dl:AddCircle({ gx, gy }, 9 * scale, with_alpha(rgb, L.alpha), 16, 2 * scale)
            end
            dl:AddLine({ gx, gy }, { top_x, top_y }, COL_SHELL, 4 * scale)
            dl:AddLine({ gx, gy }, { top_x, top_y }, with_alpha(rgb, L.alpha), 2 * scale)
            if dl.AddText ~= nil then
                local text = ('%.0f'):format(total)
                if label ~= nil and label ~= '' then text = text .. 'y  ' .. label
                else text = text .. 'y' end
                -- Keep the label on the screen.  A destination near the right edge otherwise
                -- writes its name off the side of the monitor, which is where the one piece
                -- of information the player wanted goes.  ~7px per character at ImGui's
                -- default font; erring wide is free, erring narrow loses the last word.
                local tx = math.min(top_x + 6, Pr.width - (#text * 7 + 8))
                local ty = math.max(4, math.min(top_y - 8, Pr.height - 18))
                dl:AddText({ math.max(4, tx), ty }, with_alpha(rgb, 1), text)
            end
        end
    end)
    if not ok then
        L.enabled = false
        L.off_reason = 'the draw list refused a call'
        return false
    end
    return true
end

--- `/vg line on|off` and friends.  Returns a sentence to print.
function L.set(what, value)
    if what == 'on' then
        L.enabled = true
        L.off_reason = nil
        Pr.fails = 0
        return 'line on'
    elseif what == 'off' then
        L.enabled = false
        L.off_reason = 'turned off'
        return 'line off'
    elseif what == 'style' then
        if value ~= 'solid' and value ~= 'dots' and value ~= 'both' then
            return 'style is solid, dots or both'
        end
        L.style = value
        return 'line style ' .. value
    elseif what == 'width' then
        local n = tonumber(value)
        if n == nil then return 'width takes a number of pixels' end
        L.width = math.max(1, math.min(12, n))
        return ('line width %d'):format(L.width)
    end
    return nil
end

--- `/vg line probe` -- the numbers, so the projection can be checked without a screenshot.
---
--- A script driving this client can read `/vg tee`'s file and cannot read the screen, so the
--- only way to prove the camera maths in-game is to print points whose answers are known in
--- advance.  Three of them:
---
---   feet     where the player is standing.  A third-person camera sits behind and above the
---            player, so this must land near the middle across and in the lower half down,
---            with w equal to roughly the camera distance -- a few yalms, not hundreds.
---   ahead    twenty yalms the way the player faces.  Must be *higher* on the screen than
---            feet (a smaller y) and have a larger w.  If it is lower, the height axis is
---            upside down; if it is off to one side, the heading maths is wrong.
---   above    five yalms straight up.  Must be higher on the screen than feet and within a
---            few pixels of it across.  Five and not twenty: the camera sits about five
---            yalms from the player and pitched down, so a point twenty yalms up is *behind*
---            it and comes back with a negative w -- correct, and useless as a check.
---
--- Anything else -- w negative, coordinates in the millions, all three identical -- means the
--- device is not giving out the camera and the line should stay off.
function L.probe(w, print_fn)
    local say = print_fn or print
    say(('viewport %dx%d'):format(Pr.width, Pr.height))
    if not Pr.refresh() then
        say('GetTransform failed: ' .. tostring(Pr.reason))
        return false
    end
    say('GetTransform ok')
    if w == nil or w.x == nil then say('no position'); return false end
    local yaw = w.yaw or 0
    -- core/util.lua: yaw is 0 = east, growing counter-clockwise, and z is the second
    -- horizontal axis, so "ahead" is +x by cos and -z by sin.
    local ax, az = w.x + 20 * math.cos(yaw), w.z - 20 * math.sin(yaw)
    local cases = {
        { 'feet ', w.x, w.z, w.y or 0 },
        { 'ahead', ax, az, w.y or 0 },
        { 'above', w.x, w.z, (w.y or 0) - 5 },
    }
    for _, c in ipairs(cases) do
        local sx, sy, cw = Pr.point(c[2], c[3], c[4])
        say(('%s world %.1f,%.1f,%.1f -> screen %.0f,%.0f  w=%.2f')
            :format(c[1], c[2], c[3], c[4], sx, sy, cw))
    end
    return true
end

function L.status()
    if not L.enabled then
        return 'line: off' .. (L.off_reason and (' (' .. L.off_reason .. ')') or '')
    end
    return ('line: on, %s, camera %s (%d frames), path %s')
        :format(L.style, Pr.ok and 'ok' or ('failing: ' .. tostring(Pr.reason)),
                Pr.frames, Path.source)
end

return L
