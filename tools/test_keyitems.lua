-- Vanaguide :: tools/test_keyitems.lua -- key items from the server's 0x055 packets when Ashita cannot read them.
--   luajit tools/test_keyitems.lua   (from the repository root)
-- Copyright (c) 2026 Bates LLC.  All rights reserved.
package.path = 'Vanaguide/?.lua;Vanaguide/?/init.lua;' .. package.path
dofile('tools/stubs.lua')
local story = require('core.story')
local U = require('core.util')
local fails = 0
local function eq(a,b,w) if a~=b then fails=fails+1 print('FAIL',w,a,b) end end
local function pkt055(tbl, ids)
  local b = {} for i=1,0x88 do b[i]=0 end
  b[1]=0x55; b[2]=0x44
  for _,id in ipairs(ids) do local bit=id%512; local byte=0x04+math.floor(bit/8); b[byte+1]=b[byte+1]+2^(bit%8) end
  b[0x84+1]=tbl%256; b[0x84+2]=math.floor(tbl/256)
  local s={} for i=1,#b do s[i]=string.char(b[i]) end return table.concat(s)
end
eq(story.has_key_item(112), nil, 'unknown before packet')
eq(U.has_key_item(112), false, 'util false before packet')
story.on_packet(0x055, pkt055(0,{1,65,112,146,511}), 0x88)
for _,k in ipairs({1,65,112,146,511}) do eq(U.has_key_item(k), true, 'ki '..k) end
eq(U.has_key_item(4), false, 'ki 4 absent')
eq(story.has_key_item(600), nil, 'table 1 unknown')
story.on_packet(0x055, pkt055(1,{600}), 0x88)
eq(U.has_key_item(600), true, 'ki 600')
story.on_packet(0x055, pkt055(0,{65}), 0x88)   -- delkeyitem 112 -> table re-sent
eq(U.has_key_item(112), false, 'ki 112 removed')
eq(U.has_key_item(65), true, 'ki 65 kept')
story.on_packet(0x055, string.rep('\0', 0x40), 0x40) -- short packet ignored
eq(U.has_key_item(65), true, 'short packet ignored')
-- 0xFFFF nation switch
local function pffff(nation, cur)
  local b = {} for i=1,0x28 do b[i]=0 end
  local function w32(off,v) for k=0,3 do b[off+k+1]=math.floor(v/256^k)%256 end end
  w32(0x04,nation); w32(0x08,cur); w32(0x24,0xFFFF)
  local s={} for i=1,#b do s[i]=string.char(b[i]) end return table.concat(s)
end
story.on_packet(0x056, pffff(1,0), 0x28)
eq(story.mission_current('bastok'), 0, 'bastok current 0')
eq(story.mission_active('bastok', 0), true, 'bastok MA 0 active')
story.on_packet(0x056, pffff(0,3), 0x28)
eq(story.mission_current('bastok'), nil, 'bastok cleared after switching back')
eq(story.mission_current('sandoria'), 3, 'sandoria current 3')
story.reset()
eq(story.has_key_item(65), nil, 'reset clears key items')
print(fails==0 and 'ki_test ok' or ('ki_test FAILS '..fails))
