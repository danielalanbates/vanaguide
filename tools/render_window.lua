-- Vanaguide :: tools/render_window.lua
-- Records the widget calls ui/window.lua makes for a given world state and draws them to
-- docs/window-layout.svg.
--
-- This is NOT a screenshot: ImGui is faked, and the picture is this script's approximation
-- of how ImGui would lay the widgets out.  What it *does* prove is the content — every line
-- of text and every button below came out of the real ui/window.lua, driven by the real
-- progress cursor and router, for the world state named at the top of each panel.
--
--   luajit tools/render_window.lua
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

package.path = 'Vanaguide/?.lua;' .. package.path
dofile('tools/stubs.lua')

local G = require('core.guide')
local P = require('core.progress')
local C = require('core.conditions')
local U = require('core.util')
local Window = require('ui.window')
require('guides.init')

local ops
local function push(kind, text, colour) ops[#ops + 1] = { kind = kind, text = text, colour = colour } end

local fake = {}
fake.Begin = function(title) push('title', title); return true end
fake['End'] = function() end
fake.Text = function(s) push('text', s) end
fake.TextWrapped = function(s) push('text', s) end
fake.PushTextWrapPos = function() end
fake.PopTextWrapPos = function() end
fake.TextColored = function(c, s) push('text', s, c) end
fake.Separator = function() push('rule') end
fake.Button = function(s) push('button', s); return false end
fake.SameLine = function() if ops[#ops] ~= nil then ops[#ops].same_line = true end end
fake.SetNextWindowSize = function() end
_G.imgui = fake
_G.ImGuiCond_FirstUseEver = 4

local function frame(label)
    ops = {}
    Window.draw((function () local w = C.world(); w.yaw = WORLD.yaw; return w end)())
    return { label = label, ops = ops }
end

-- Two states worth looking at: the step is here, and the step is a continent away.
P.set_guide(G.get("San d'Oria — Rank 1"))
WORLD.zone, WORLD.x, WORLD.z, WORLD.yaw = 230, -20, 40, 0
local a = frame("in Southern San d'Oria, on step 1")

P.check(1); P.check(2); P.check(3); P.advance()
WORLD.zone = 246                                   -- Port Jeuno: the step is far away now
local b = frame('in Port Jeuno, four steps in')

local PANEL_W, PANEL_H, PAD = 400, 300, 20
local W = PAD + (PANEL_W + PAD) * 2
local H = PANEL_H + PAD * 3
local out = { ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'):format(W, H, W, H) }
out[#out + 1] = ('<rect width="%d" height="%d" fill="#0f1116"/>'):format(W, H)

local function wrap(s, width)
    local lines, line = {}, ''
    for word in tostring(s):gmatch('%S+') do
        if line == '' then line = word
        elseif #line + #word + 1 <= width then line = line .. ' ' .. word
        else lines[#lines + 1] = line; line = '    ' .. word end
    end
    if line ~= '' then lines[#lines + 1] = line end
    return lines
end

local function esc(s)
    return (tostring(s):gsub('&', '&amp;'):gsub('<', '&lt;'):gsub('>', '&gt;'))
end

for i, panel in ipairs({ a, b }) do
    local x0 = PAD + (i - 1) * (PANEL_W + PAD)
    local y0 = PAD * 2
    out[#out + 1] = ('<text x="%d" y="%d" fill="#8891a8" font-family="monospace" font-size="12">%s</text>')
        :format(x0, PAD + 4, esc(panel.label))
    out[#out + 1] = ('<rect x="%d" y="%d" width="%d" height="%d" rx="6" fill="#1b1f2a" stroke="#333a4d"/>')
        :format(x0, y0, PANEL_W, PANEL_H)
    local y, bx = y0 + 26, nil
    for _, op in ipairs(panel.ops) do
        if op.kind == 'title' then
            out[#out + 1] = ('<rect x="%d" y="%d" width="%d" height="22" rx="6" fill="#232a3a"/>'):format(x0, y0, PANEL_W)
            out[#out + 1] = ('<text x="%d" y="%d" fill="#dde3f0" font-family="sans-serif" font-size="12">%s</text>')
                :format(x0 + 10, y0 + 16, esc(op.text))
        elseif op.kind == 'rule' then
            out[#out + 1] = ('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333a4d"/>'):format(x0 + 8, y, x0 + PANEL_W - 8, y)
            y = y + 14
        elseif op.kind == 'button' then
            local bxx = bx or (x0 + 10)
            out[#out + 1] = ('<rect x="%d" y="%d" width="%d" height="20" rx="4" fill="#2c3448" stroke="#3d4763"/>')
                :format(bxx, y - 12, 22 + #op.text * 7)
            out[#out + 1] = ('<text x="%d" y="%d" fill="#cfd6e6" font-family="sans-serif" font-size="11">%s</text>')
                :format(bxx + 11, y + 2, esc(op.text))
            bx = bxx + 32 + #op.text * 7
            if not op.same_line then y = y + 26; bx = nil end
        else
            local col = '#c9d1e0'
            if op.colour ~= nil then
                col = ('#%02x%02x%02x'):format(op.colour[1] * 255, op.colour[2] * 255, op.colour[3] * 255)
            end
            -- ImGui wraps at the window edge; wrap here too, or the picture would show a
            -- tidiness the real window does not have.
            for _, chunk in ipairs(wrap(op.text, 56)) do
                out[#out + 1] = ('<text x="%d" y="%d" fill="%s" font-family="sans-serif" font-size="12">%s</text>')
                    :format(x0 + 10, y, col, esc(chunk))
                y = y + 17
            end
            y = y + 1
            bx = nil
        end
    end
end
out[#out + 1] = '</svg>'
local f = assert(io.open('docs/window-layout.svg', 'w'))
f:write(table.concat(out, '\n'))
f:close()
print('wrote docs/window-layout.svg')
