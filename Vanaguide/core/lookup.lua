-- Vanaguide :: core/lookup.lua
-- "Where do I get this?" — items, gear and notorious monsters, turned into something the
-- arrow can point at.
--
-- A guide is a list of steps, so a lookup answer is just a one-step guide built on the spot:
-- pick a result, and the router and the arrow treat it exactly like any guide step.  That is
-- why there is no second navigation path in this addon.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local U      = require('core.util')
local G      = require('core.guide')
local gear   = require('data.gear')
local drops  = require('data.drops')
local vendors = require('data.vendors')
local nm     = require('data.nm')
local quests = require('data.quests')

local L = { last = {} }

--- Everywhere this item can be got, best first: notorious monsters, then ordinary drops by
--- rate, then merchants by price.
function L.sources(item_id)
    local out = {}
    for _, s in ipairs(drops.sources_for(item_id)) do
        out[#out + 1] = {
            kind = s.nm and 'nm' or 'drop', name = s.mob, zone = s.zone,
            x = s.x, z = s.z, rate = s.rate,
            text = ('%s%s in %s (%.1f%%)'):format(s.nm and 'NM ' or '', s.mob,
                                                  U.zone_name(s.zone), s.rate),
        }
    end
    for _, v in ipairs(vendors.sources_for(item_id)) do
        out[#out + 1] = {
            kind = 'vendor', name = v.npc, zone = v.zone, x = v.x, z = v.z, price = v.price,
            text = ('%s in %s (%d gil)'):format(v.npc, U.zone_name(v.zone), v.price),
        }
    end
    -- A quest reward is a source too, and often the only one: nothing drops or sells the
    -- artifact pieces, and "do this quest" is a better answer than "no source known".
    for _, q in ipairs(quests.awarding(item_id)) do
        out[#out + 1] = {
            kind = 'quest', name = q.quest.name, zone = q.quest.zone,
            x = q.quest.x, z = q.quest.z, quest = { area = q.area, id = q.id },
            -- Plain hyphen, not an em dash: FFXI's chat font has no glyph for it and prints
            -- a pair of garbage characters instead (seen in-game 2026-08-22).
            text = ('quest "%s"%s'):format(q.quest.name,
                q.quest.zone and (' - starts in ' .. U.zone_name(q.quest.zone)) or ''),
        }
    end

    table.sort(out, function(a, b)
        local rank = { nm = 1, drop = 2, quest = 3, vendor = 4 }
        if rank[a.kind] ~= rank[b.kind] then return rank[a.kind] < rank[b.kind] end
        return (a.rate or 0) > (b.rate or 0)
    end)
    return out
end

--- Search gear by name.  Returns { name, id, level, slot, rare, ex, sources }.
function L.find_item(text)
    local out = {}
    for _, item in ipairs(gear.find(text)) do
        item.sources = L.sources(item.id)
        out[#out + 1] = item
    end
    return out
end

--- Gear for a slot that this character can wear right now, best-level first.
function L.gear_for(slot, level, job)
    local out = {}
    for _, item in ipairs(gear.for_slot(slot, level, job)) do
        if #out >= 12 then break end
        item.sources = L.sources(item.id)
        if #item.sources > 0 then out[#out + 1] = item end
    end
    return out
end

--- Notorious monsters, either in a zone or by name.
function L.nms(where)
    if type(where) == 'number' then return nm.in_zone(where) end
    if where == nil or where == '' then return nm.in_zone(U.zone() or -1) end
    return nm.find(where)
end

--- Build a one-step guide that points at a place, and make it the active guide.
--- `P` is passed in rather than required, so this module stays loadable by the offline tests
--- without dragging the progress cursor along.
function L.track(P, opts)
    local line = { 'R ' .. (opts.text or 'Go here') }
    if opts.zone ~= nil then
        line[#line + 1] = ('|Z|%d|'):format(opts.zone)
        if opts.x ~= nil then line[#line + 1] = ('|POS|%.1f,%.1f,%d|'):format(opts.x, opts.z, opts.radius or 15) end
    end
    if opts.note ~= nil then line[#line + 1] = ('|N|%s|'):format(opts.note) end

    local guide = G.register({
        name = 'Tracking: ' .. (opts.title or opts.text or '?'),
        author = 'you',
        desc = 'A single place, from a lookup.',
        steps = table.concat(line),
    })
    P.set_guide(guide, nil)
    return guide
end

return L
