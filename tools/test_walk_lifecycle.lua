-- Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
-- Execute the real addon callbacks with inert platform/UI/settings dependencies.
-- No filesystem, game, window, packet delivery or real timer is accessed.
package.path = 'Vanaguide/?.lua;Vanaguide/?/init.lua;' .. package.path
local handlers, running, step = {}, 0, {text='fixture',zone=232,pos={x=100,z=0}}
addon = {}
T = function(t) return t end
function string.args(text)
    local out={} for word in text:gmatch('%S+') do out[#out+1]=word end return out
end
function string.any(text,...)
    for i=1,select('#',...) do if text==select(i,...) then return true end end return false
end
local noop=function() end
local util={dist=function(x,z,a,b) return math.sqrt((x-a)^2+(z-b)^2) end,
            print=noop,zone=function() return 232 end,heading=function() return 0 end}
package.loaded['common']=true
package.loaded['settings']={load=function(t) return t end,save=noop,register=noop}
package.loaded['core.util']=util
package.loaded['core.story']={on_packet=noop,reset=noop}
package.loaded['core.guide']={}
package.loaded['core.conditions']={world=function() return {x=0,z=0,y=0,zone=232,yaw=0} end}
package.loaded['core.progress']={guide={name='fixture'},index=1,step=function() return step end,
    advance=function() return 0 end,save_state=function() return {} end}
package.loaded['routing.zonegraph']={save_learned=function() return {} end}
package.loaded['routing.router']={recommend=function() return {mode='here',target={x=100,z=0}} end}
for _,name in ipairs({'core.lookup','core.verify','ui.arrow','ui.line','ui.project','routing.zonepoints'}) do
    package.loaded[name]=setmetatable({}, {__index=function() return noop end})
end
package.loaded['ui.window']={open={true},draw=noop}
package.loaded['routing.path']={to=function() return nil end,forget=noop}
package.loaded['routing.navgrid']={step=noop}
package.loaded['guides.init']=true
package.loaded.ffi={cdef=noop,C={GetTickCount=function() return 100 end}}
ashita={events={register=function(_,name,callback) handlers[name]=callback end}}
AshitaCore={GetInstallPath=function() return 'inert-fixture' end,
    GetMemoryManager=function() return {
        GetAutoFollow=function() return setmetatable({}, {__index=function(_,name)
            return function(_,v) if name=='SetIsAutoRunning' then running=v end end
        end}) end,
    } end,
    GetPacketManager=function() return {AddOutgoingPacket=noop,AddIncomingPacket=noop} end}
-- pump_commands and optional chat captures must not touch even a dummy file.
io.open=function() return nil end
dofile('Vanaguide/Vanaguide.lua')
local Walk=require('core.walk')
local function command(text) handlers.vg_command({command=text}) end
command('/vg walk allow')
command('/vg walk auto')
command('/vg walk auto')
command('/vg walk stop')
local incoming={id=0x032,size=16,data=string.rep('\0',16)}
handlers.vg_packet_in(incoming)
assert(not incoming.blocked,'restarting auto walking must still restore the original cutscene setting')

command('/vg walk auto')
Walk.run(5,0,0)
step=nil
handlers.vg_present()
assert(not Walk.active and running==0,'finishing the guide must release autorun')
incoming={id=0x032,size=16,data=string.rep('\0',16)}
handlers.vg_packet_in(incoming)
assert(not incoming.blocked,'finishing the guide must restore normal cutscenes')

step={text='fixture',zone=232,pos={x=100,z=0}}
command('/vg walk auto')
Walk.run(5,0,0)
handlers.vg_unload()
assert(not Walk.active and running==0,'unloading the addon must release autorun')
print('4 addon walking lifecycle regressions passed')
