-- Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
-- Exercise the real path and walker with synthetic positions; no game or real timer.
package.path = 'Vanaguide/?.lua;Vanaguide/?/init.lua;' .. package.path
local clock, commands, running = 0, {}, 0
package.loaded.ffi = {cdef=function() end,C={GetTickCount=function() return clock end}}
AshitaCore = {
    GetMemoryManager=function() return {
        GetParty=function() return {GetMemberTargetIndex=function() return 1 end} end,
        GetAutoFollow=function() return setmetatable({}, {__index=function(_,name)
            return function(_,v) if name=='SetIsAutoRunning' then running=v end end
        end}) end,
    } end,
    GetChatManager=function() return {QueueCommand=function(_,_,text) commands[#commands+1]=text end} end,
}
local Path=require('routing.path')
local Walk=require('core.walk')
local route={{x=0,z=0,y=0},{x=0,z=100,y=0},{x=100,z=100,y=0},{x=100,z=0,y=0}}
Path.provider=function() return route end
Walk.server_nudges=false
assert(Walk.start({x=100,z=0,y=0},'detour'))
-- This valid route initially runs away from the target for 15s. Direct target distance
-- increases, but the remaining navigation route decreases with every observed stride.
for i=1,151 do
    clock=i*100
    Walk.update({x=0,z=(i-1)*0.5,y=0,zone=232})
end
assert(Walk.active and running==1,'a progressing navmesh detour must not be declared stuck')
assert(#commands==0,'strict detours must need no server assistance')

-- A client bouncing half a yalm against a wall is not progressing down the route.
assert(Walk.start({x=100,z=0,y=0},'blocked'))
Path.forget()
for i=1,121 do
    clock=(151+i)*100
    Walk.update({x=0,z=(i%2)*0.5,y=0,zone=232})
end
assert(not Walk.active and Walk.reason:find('stuck') and running==0,
       'wall bounce must still stop and release autorun')
assert(#commands==0,'a blocked strict run must never send a nudge')
print('4 detour/wall-bounce regressions passed')

-- A blocked navmesh follower must keep the first corridor leg. Skipping later
-- corners or sidestepping outside the route defeats collision-aware planning.
local deltas={}
AshitaCore.GetMemoryManager=function() return {
 GetParty=function() return {GetMemberTargetIndex=function() return 1 end} end,
 GetAutoFollow=function() return setmetatable({}, {__index=function(_,name)
  return function(_,value) deltas[name]=value end
 end}) end,
} end
Path.forget()
assert(Walk.start({x=100,z=0,y=0},'blocked corridor'))
for i=1,40 do
 clock=(400+i)*100
 Walk.update({x=0,z=0,y=0,zone=232})
end
assert(Walk.active,'test samples recovery before terminal stuck timeout')
assert(math.abs(deltas.SetFollowDeltaX)<1e-9 and deltas.SetFollowDeltaY>0,
 'navmesh recovery must keep the corridor heading instead of skipping corners or sidestepping')
Walk.stop('fixture complete')
print('navmesh recovery corridor check passed')
