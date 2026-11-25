-- Vanaguide :: tools/route_check.lua
-- For every guide, can the router get from each step's zone to the next one?  One JSON line per
-- zone change:  luajit tools/route_check.lua > routes.jsonl   (from the repository root)
-- Copyright (c) 2026 Bates LLC.  All rights reserved.
package.path = 'Vanaguide/?.lua;Vanaguide/?/init.lua;' .. package.path
dofile('tools/stubs.lua')
local G = require('core.guide')
require('guides.init')
local graph = require('routing.zonegraph')
for gi, guide in ipairs(G.list()) do
    local prev = nil
    for si, s in ipairs(guide.steps or {}) do
        if s.zone ~= nil then
            if prev ~= nil and prev ~= s.zone then
                local legs, cost = graph.route(prev, s.zone)
                print(('{"guide":%d,"step":%d,"from":%d,"to":%d,"ok":%s,"hops":%s,"cost":%s}')
                    :format(gi, si, prev, s.zone, legs and 'true' or 'false',
                            legs and #legs or 'null', cost and ('%.0f'):format(cost) or 'null'))
            end
            prev = s.zone
        end
    end
end
