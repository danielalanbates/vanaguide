-- Copyright (c) 2026 Bates LLC. All rights reserved.
-- Synthetic maps only: no client, server or proprietary navigation data.
package.path = 'Vanaguide/?.lua;' .. package.path
local nav = require('routing.navgrid')
local sight
for i=1,50 do
    local name, value = debug.getupvalue(nav.provide, i)
    if not name then break end
    if name == 'line_of_sight' then sight = value; break end
end
assert(sight, 'smoothing visibility function found')
local function grid(blocked, raised)
    local mask, heights = {}, {}
    for z=0,2 do for x=0,2 do
        local key = x .. ',' .. z
        mask[#mask+1] = string.char(blocked == key and 0 or 1)
        heights[#heights+1] = string.char(raised == key and 80 or 0, 0)
    end end
    return {w=3,h=3,layers=1,step=3,mask=table.concat(mask),height=table.concat(heights)}
end
assert(sight(grid(),0,0,2,2,0), 'open diagonal remains visible')
assert(sight(grid(),2,2,0,0,0), 'reverse open diagonal remains visible')
for _, side in ipairs({'1,0','0,1','2,1','1,2'}) do
    assert(not sight(grid(side),0,0,2,2,0), 'blocked corner '..side)
    assert(not sight(grid(side),2,2,0,0,0), 'reverse blocked corner '..side)
end
assert(not sight(grid(nil,'1,0'),0,0,2,2,0), 'unclimbable side floor blocks corner')
assert(sight(grid('0,1'),0,0,2,0,0), 'unrelated wall does not block cardinal run')
assert(not sight(grid('1,0'),0,0,2,0,0), 'wall on cardinal run blocks visibility')
print('13 navigation smoothing checks passed')
