-- Vanaguide :: tools/render_arrow.lua
-- Draws ui/arrow.lua through a fake ImGui draw list and writes docs/arrow-geometry.svg.
--
-- This proves the geometry and the rotation sense of the real drawing code — the same
-- function the game calls, with the same numbers — without a client.  It does NOT prove
-- that ImGui renders it in-game; see docs/VERIFICATION.md.
--
--   luajit tools/render_arrow.lua
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

package.path = 'Vanaguide/?.lua;' .. package.path

local recorded = {}
local draw_list = {
    AddLine = function(_, a, b, colour, width)
        recorded[#recorded + 1] = { a[1], a[2], b[1], b[2], colour, width }
    end,
    AddText = function(_, at, colour, text)
        recorded[#recorded + 1] = { text = text, x = at[1], y = at[2] }
    end,
}
_G.imgui = { GetForegroundDrawList = function() return draw_list end }

local A = require('ui.arrow')

local CASES = {
    { 0,               'ahead' },
    { math.pi / 2,     'left (90 degrees)' },
    { math.pi,         'behind' },
    { -math.pi / 2,    'right (-90 degrees)' },
    { math.pi / 4,     'ahead-left' },
}

local W, H, CELL = 5 * 170, 190, 170
local out = { ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'):format(W, H, W, H) }
out[#out + 1] = ('<rect width="%d" height="%d" fill="#12141a"/>'):format(W, H)

for i, case in ipairs(CASES) do
    local bearing, label = case[1], case[2]
    recorded = {}
    A.pos_x, A.pos_y = (i - 1) * CELL + CELL / 2, 80
    local ok = A.draw(bearing, 42, '42 yalms', label)
    assert(ok, 'arrow refused to draw')
    for _, l in ipairs(recorded) do
        if l.text ~= nil then
            out[#out + 1] = ('<text x="%.1f" y="%.1f" fill="#aab" font-family="monospace" font-size="10">%s</text>')
                :format(l.x + 40, l.y + 10, l.text)
        elseif l[6] == 3 then  -- the coloured pass; the dark outline underneath is skipped
            out[#out + 1] = ('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#4ade80" stroke-width="3" stroke-linecap="round"/>')
                :format(l[1], l[2], l[3], l[4])
        end
    end
    out[#out + 1] = ('<line x1="%.1f" y1="16" x2="%.1f" y2="120" stroke="#33384a" stroke-width="1"/>')
        :format((i - 1) * CELL + CELL / 2, (i - 1) * CELL + CELL / 2)
end
out[#out + 1] = '</svg>'

local f = assert(io.open('docs/arrow-geometry.svg', 'w'))
f:write(table.concat(out, '\n'))
f:close()
print('wrote docs/arrow-geometry.svg  (' .. #CASES .. ' bearings)')
