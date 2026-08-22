-- Vanaguide :: guides/generated.lua
-- One guide per quest-log area, built at load time from data/quests.lua — every quest the
-- server implements, in an order you can actually follow.
--
-- Ordering: a quest never appears before the quest it requires (a topological sort over the
-- prerequisite links), then by the level the script checks for, then by quest id, which is
-- roughly the order the game itself lists them.  Quests whose script states no coordinates
-- still appear — they simply have no arrow, and say so.
--
-- These are generated, not authored.  A hand-written guide beats them for any one storyline,
-- because it knows what to do between accepting and finishing; what these give you is
-- completion: nothing in an area is missed, and every entry ticks itself off the moment the
-- server says you finished it.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local G = require('core.guide')
local Q = require('data.quests')
local MI = require('data.missions')
local NM = require('data.nm')

local AREA_TITLE = {
    sandoria = "San d'Oria", bastok = 'Bastok', windurst = 'Windurst', jeuno = 'Jeuno',
    other = 'Other areas', outlands = 'Outlands', ahturhgan = 'Aht Urhgan',
    wotg = 'Crystal War', abyssea = 'Abyssea', adoulin = 'Adoulin', coalition = 'Coalition',
}

--- Prerequisites first, then level, then id.
local function ordered(area)
    local list = Q.area(area)
    local by_id, done, out = {}, {}, {}
    for _, e in ipairs(list) do by_id[e.id] = e end

    table.sort(list, function(a, b)
        local la = a.quest.level or 0
        local lb = b.quest.level or 0
        if la ~= lb then return la < lb end
        return a.id < b.id
    end)

    local function emit(entry)
        if entry == nil or done[entry.id] then return end
        -- Marked before recursing, not after: two quests in the data name each other as a
        -- prerequisite (Bastok 4 and 5 do), and marking afterwards lets that pair bounce
        -- back and forth until the depth limit, emitting both a dozen times.
        done[entry.id] = true
        -- A prerequisite in the same area is emitted first.  Cross-area prerequisites are
        -- left alone: reordering another area's guide from this one would be worse than a
        -- step that waits.
        local pre = entry.quest.prereq
        if pre ~= nil and pre[1] == area then emit(by_id[pre[2]]) end
        out[#out + 1] = entry
    end

    for _, entry in ipairs(list) do emit(entry) end
    return out
end

local function build(area)
    local entries = ordered(area)
    if #entries == 0 then return nil end

    local steps = {}
    for _, entry in ipairs(entries) do
        local q = entry.quest
        local line = { 'C ' .. q.name }
        line[#line + 1] = ('|Q|%s,%d|'):format(area, entry.id)
        if q.zone ~= nil then
            line[#line + 1] = ('|Z|%d|'):format(q.zone)
            if q.x ~= nil then line[#line + 1] = ('|POS|%.1f,%.1f,8|'):format(q.x, q.z) end
        end
        if q.level ~= nil then
            line[#line + 1] = ('|N|Level %d. Ask %s.|'):format(q.level, q.npc or 'the quest giver')
        elseif q.npc ~= nil then
            line[#line + 1] = ('|N|Ask %s.|'):format(q.npc)
        else
            line[#line + 1] = '|N|No location recorded for this one yet.|'
        end
        steps[#steps + 1] = table.concat(line)
    end

    return G.register({
        name = ('%s — every quest'):format(AREA_TITLE[area] or area),
        author = 'generated from server data',
        desc = ('All %d quests in the %s log, prerequisites first.'):format(#entries, AREA_TITLE[area] or area),
        steps = table.concat(steps, '\n'),
    })
end

local STORY_TITLE = {
    sandoria = "San d'Oria missions", bastok = 'Bastok missions',
    windurst = 'Windurst missions', zilart = 'Rise of the Zilart',
    cop = 'Chains of Promathia', toau = 'Treasures of Aht Urhgan',
    wotg = 'Wings of the Goddess', acp = 'A Crystalline Prophecy',
    amk = "A Moogle Kupo d'Etat", asa = 'A Shantotto Ascension',
    adoulin = 'Seekers of Adoulin', rov = 'Rhapsodies of Vana\'diel',
    tvr = 'The Voracious Resurgence', campaign = 'Campaign', assault = 'Assault',
}

--- Missions are linear, so the guide is simply the storyline in order.  `M|area,id|`
--- completes when the server's current-mission number passes the id, which is why these
--- ids are generated rather than remembered — being one out means waiting forever.
local function build_missions(area)
    local entries = MI.area(area)
    if #entries == 0 then return nil end
    local steps = {}
    for _, entry in ipairs(entries) do
        local m = entry.mission
        local title = m.label and ('%s: %s'):format(m.label, m.name) or m.name
        local line = { 'C ' .. title, ('|M|%s,%d|'):format(area, entry.id) }
        if m.zone ~= nil then
            line[#line + 1] = ('|Z|%d|'):format(m.zone)
            if m.x ~= nil then line[#line + 1] = ('|POS|%.1f,%.1f,8|'):format(m.x, m.z) end
        end
        line[#line + 1] = ('|N|%s|'):format(m.npc and ('Starts with ' .. m.npc .. '.')
            or 'No location recorded for this one yet.')
        steps[#steps + 1] = table.concat(line)
    end
    return G.register({
        name = ('%s — in order'):format(STORY_TITLE[area] or area),
        author = 'generated from server data',
        desc = ('All %d missions in the %s storyline.'):format(#entries, STORY_TITLE[area] or area),
        steps = table.concat(steps, '\n'),
    })
end

--- Notorious monsters, one guide per zone that has any with a known spot.  Hunting is not a
--- sequence, so these are `FIXED`: nothing auto-completes, the list stays put, and each entry
--- is a place the arrow can take you.
local function build_nms(zone, list)
    local steps = {}
    table.sort(list, function(a, b) return (a.lo or 0) < (b.lo or 0) end)
    for _, n in ipairs(list) do
        if n.x ~= nil then
            steps[#steps + 1] = ('K %s (level %d-%d)|Z|%d|POS|%.1f,%.1f,20|FIXED||N|%s|')
                :format(n.name, n.lo, n.hi, zone, n.x, n.z,
                        (#n.loot > 0) and ('%d recorded drops'):format(#n.loot) or 'no drops recorded')
        end
    end
    if #steps == 0 then return nil end
    return G.register({
        name = ('Notorious monsters — %s'):format(require('core.util').zone_name(zone)),
        author = 'generated from server data',
        desc = ('%d notorious monsters with a known spawn in this zone.'):format(#steps),
        steps = table.concat(steps, '\n'),
    })
end

local M = { areas = {}, storylines = {} }
for area in pairs(Q.quests) do M.areas[#M.areas + 1] = area end
table.sort(M.areas)
for _, area in ipairs(M.areas) do build(area) end

do
    local by_zone = {}
    for _, n in ipairs(NM.list) do
        if n.x ~= nil then
            by_zone[n.zone] = by_zone[n.zone] or {}
            table.insert(by_zone[n.zone], n)
        end
    end
    local zones_with = {}
    for zone in pairs(by_zone) do zones_with[#zones_with + 1] = zone end
    table.sort(zones_with)
    for _, zone in ipairs(zones_with) do build_nms(zone, by_zone[zone]) end
    M.nm_zones = zones_with
end

for area in pairs(MI.missions) do M.storylines[#M.storylines + 1] = area end
table.sort(M.storylines)
for _, area in ipairs(M.storylines) do build_missions(area) end

return M
