-- Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
-- Offline walking contracts: no game, memory writes, server, input or wall-clock sleeps.
package.path = 'Vanaguide/?.lua;Vanaguide/?/init.lua;' .. package.path
local clock, commands, running, deltas = 0, {}, {}, {}
package.loaded.ffi = { cdef = function() end, C = { GetTickCount = function() return clock end } }
package.loaded['core.util'] = { dist = function(x, z, a, b) return math.sqrt((x-a)^2 + (z-b)^2) end }
package.loaded['routing.path'] = { to = function() return nil end }
AshitaCore = {
    GetMemoryManager = function() return {
        GetParty = function() return { GetMemberTargetIndex = function() return 1 end } end,
        GetAutoFollow = function() return setmetatable({}, { __index = function(_, name)
            return function(_, value) if name == 'SetIsAutoRunning' then running[#running+1] = value end; deltas[name] = value end
        end }) end,
    } end,
    GetChatManager = function() return { QueueCommand = function(_, _, text) commands[#commands+1] = text end } end,
}
local function fresh(nudges)
    package.loaded['core.walk'] = nil
    clock, commands, running = 0, {}, {}
    local walk = require('core.walk')
    walk.server_nudges = nudges
    assert(walk.start({x=100,z=0}, 'fixture'))
    return walk
end
local w = { x=0,z=0,y=0,zone=232 }
local strict = fresh(false)
for i=1,95 do clock=i*100; strict.update(w) end
assert(#commands == 0, 'strict walking must never ask the server to carry the character')
assert(not strict.active and strict.reason:find('stuck'), 'a blocked strict run must stop')
assert(#running > 0 and running[#running] == 0, 'stopping must release autorun')
local assisted = fresh(true)
for i=1,95 do clock=i*100; assisted.update(w) end
assert(#commands > 0, 'the existing assisted mode remains available')
assert(assisted.status():find('server nudges'), 'idle status must retain evidence of assisted movement')
local arrived = fresh(false)
clock=100; arrived.update(w)
clock=200
assert(arrived.update({x=99,z=0,y=0,zone=232}), 'arrival is determined by the observed position')
assert(not arrived.active and arrived.reason == 'arrived' and running[#running] == 0)
local cancelled = fresh(false)
clock=100; cancelled.update(w); clock=200; cancelled.update(w)
local state = { walk_auto=true, walk_wait={zone=232}, walk_back=true, walk_event_auto_was=false }
local event = { auto=true }
cancelled.cancel(state, event)
assert(not cancelled.active and running[#running] == 0, 'cancellation releases the client runner')
assert(not state.walk_auto and state.walk_wait == nil and not state.walk_back, 'crossing retries must not restart a cancelled walk')
assert(event.auto == false and state.walk_event_auto_was == nil, 'the prior event setting, including false, is restored')
cancelled.cancel(state, event)
assert(event.auto == false, 'repeated stop does not change the restored event setting')
print('11 walking contract checks passed')

-- Recovery must be perpendicular to the original heading, including diagonal headings.
local diagonal = fresh(false)
diagonal.target = {x=100,z=100}
clock=100; diagonal.update(w)
clock=200; diagonal.update(w)
clock=2800; diagonal.update(w) -- hitch only resets the frame clock
clock=2900; diagonal.update(w)
local dx, dz = deltas.SetFollowDeltaX, deltas.SetFollowDeltaY
local expected_x, expected_z = 100 + 2.5/math.sqrt(2), 100 - 2.5/math.sqrt(2)
assert(math.abs(dx/dz - expected_x/expected_z) < 1e-10, 'sidestep must use both original heading components')
print('diagonal recovery geometry passed')

local stationary = fresh(false)
for i=1,95 do clock=i*100; stationary.update(w) end
assert(stationary.observed==0 and stationary.walked>0, 'stationary commands are not observed movement')
assert(stationary.diagnostics():find('observed=0.0'), 'stopped diagnostics retain observed distance')
local measured=fresh(false)
clock=100; measured.update(w)
clock=200; measured.update({x=3,z=4,y=0,zone=232})
assert(measured.observed==5, 'observed distance comes from position samples')
clock=300; measured.update({x=100,z=100,y=0,zone=231})
assert(measured.observed==5, 'zone changes are not walking distance')
print('observed walking distance checks passed')
