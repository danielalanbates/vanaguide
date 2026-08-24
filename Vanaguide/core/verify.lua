-- Vanaguide :: core/verify.lua
-- Stand where a guide sends you and check that what it promised is actually there.
--
-- The quest database says "Ambrotien, at (93.4, -57.3) in Southern San d'Oria". That is
-- generated from server scripts, and a generator can be confidently wrong: a stale comment,
-- a mis-parsed header, an NPC that moved between eras. The only way to know is to put a
-- character on the spot and look.
--
-- FFXI's entity table holds only what is loaded near the player, which is what makes this
-- worth doing rather than querying a database: if the NPC shows up in the table while you
-- stand on the coordinates, the coordinates are right, and if it does not, either the spot
-- or the name is wrong. Results are appended to `addons/Vanaguide/verify.csv`, because
-- hundreds of these are read by a script, not by a person squinting at chat.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local U        = require('core.util')
local quests   = require('data.quests')
local missions = require('data.missions')

local V = {}

local MAX_ENTITY = 2303

-- How close counts as having arrived. The teleport is exact when it works at all, so this
-- is a tolerance for float noise, not for walking.
local ARRIVED = 3.0

local function normalize(s)
    return (tostring(s or ''):lower():gsub('[^%a%d]', ''))
end

local function install_path()
    local ok, p = pcall(function() return AshitaCore:GetInstallPath() end)
    if not ok or p == nil or p == '' then return 'C:\\HorizonXI' end
    return (p:gsub('[\\/]$', ''))
end

--- Append one line. Binary mode: Lua on Windows would otherwise turn every newline into
--- CRLF, and this file is read on the Mac side.
function V.log(name, line)
    local f = io.open(('%s\\addons\\Vanaguide\\%s'):format(install_path(), name), 'ab')
    if f == nil then return false end
    f:write(line, '\n')
    f:close()
    return true
end

--- Every named entity currently loaded, with its distance from the player.
--- `Type` 0 is a PC, 1 a monster, 2 an NPC; only NPCs and monsters are interesting here.
---
--- The player's own entity is skipped. It is always at distance zero, so leaving it in made
--- every miss ever recorded say "nearest Test" -- a field that looked like evidence and
--- carried none.
function V.nearby(px, pz)
    local mm = AshitaCore:GetMemoryManager()
    local ents = mm:GetEntity()
    local me = -1
    pcall(function() me = mm:GetParty():GetMemberTargetIndex(0) end)
    local out = {}
    for i = 0, MAX_ENTITY do
        local ok, name = pcall(function() return ents:GetName(i) end)
        if i ~= me and ok and name ~= nil and name ~= '' then
            local x = ents:GetLocalPositionX(i)
            local z = ents:GetLocalPositionY(i)     -- Ashita's Y is the second horizontal axis
            if x ~= nil and (x ~= 0 or z ~= 0) then
                out[#out + 1] = {
                    index = i, name = name, x = x, z = z,
                    dist = (px ~= nil) and U.dist(px, pz, x, z) or nil,
                }
            end
        end
    end
    table.sort(out, function(a, b) return (a.dist or 1e9) < (b.dist or 1e9) end)
    return out
end

--- Check one quest or mission against the world the player is standing in.
--- Returns a result table; `ok` is true when its own NPC is loaded nearby.
---
--- Missions are the same shape as quests -- a name, somebody to talk to, somewhere they
--- stand -- so the check is identical and only the table differs. What is not identical is
--- the key: `sandoria` is both a quest area and a mission storyline, with ids that overlap,
--- so `kind` travels with every row from here to the ledger.
function V.entry(kind, area, id)
    local q = (kind == 'mission') and missions.get(area, id) or quests.get(area, id)
    local px, pz = U.position()
    local zone = U.zone()
    local r = {
        kind = kind or 'quest',
        area = area, id = id, name = q and q.name or '?',
        npc = q and q.npc or '', want_zone = q and q.zone or nil,
        want_x = q and q.x or nil, want_z = q and q.z or nil,
        zone = zone, x = px, z = pz,
        ok = false, why = '', dist = nil, nearest = '', entities = nil,
    }

    if q == nil then r.why = 'no such ' .. (kind or 'quest') .. ' in the database'; return r end
    if q.zone == nil then r.why = 'the database has no location for it'; return r end
    if zone == nil or px == nil then r.why = 'not in the world'; return r end
    if zone ~= q.zone then
        r.why = ('standing in %d, quest is in %d'):format(zone, q.zone)
        return r
    end
    -- A mission that begins by walking into a place has a zone and no spot in it. Being in
    -- the right zone is the whole of what can be checked, and it has just been checked.
    if q.x == nil then
        r.ok = true
        r.why = 'in the right zone; this one has no coordinate to stand on'
        return r
    end

    -- In the right zone and in the wrong place. A `!pos` issued while the character is still
    -- zoning is dropped without a word, and the check that follows reads the entity table
    -- from the zone entrance and calls the NPC absent. Seven rows in the ledger were written
    -- that way -- all in Northern San d'Oria, up to 212 yalms off -- and every one of them
    -- reads like a real miss. Say so instead: this is the harness failing, not evidence.
    local off = U.dist(px, pz, q.x, q.z)
    if off > ARRIVED then
        r.why = ('standing %.1f yalms from the spot'):format(off)
        return r
    end

    -- Some quests are started at a "???" marker or a door rather than by talking to anybody.
    -- The database carries the server's internal name for those — `qm6 (H-10/Boat)`, `_0id`,
    -- `_iya` — and the client never calls them that, so matching by name is impossible. For
    -- those, the question is only whether *something* is standing where the guide points.
    local marker = q.npc ~= nil and (q.npc:match('^qm') ~= nil or q.npc:match('^_') ~= nil
                                     or q.npc:find('%?%?%?') ~= nil)
    local want = normalize(q.npc)
    local list = V.nearby(px, pz)
    r.entities = #list
    r.nearest = (#list > 0) and list[1].name or ''
    if want == '' or marker then
        -- Within ten yalms is the same "you are in the right place" the arrow uses.
        local near = list[1]
        r.ok = near ~= nil and (near.dist or 1e9) <= 10
        r.dist = near and near.dist or nil
        r.why = marker
            and (r.ok and ('marker quest: %s is here at %.1f yalms'):format(near.name, near.dist or -1)
                       or ('marker quest: nothing within 10 yalms (%d loaded)'):format(#list))
            or  (r.ok and ('no NPC named; %s is here'):format(near.name)
                       or 'no NPC named and nothing is loaded here')
        return r
    end
    for _, e in ipairs(list) do
        if normalize(e.name) == want then
            r.ok = true
            r.dist = e.dist
            r.why = ('found %s at %.1f yalms'):format(e.name, e.dist or -1)
            return r
        end
    end
    r.why = ('%s is not loaded here (%d entities, nearest %s)')
        :format(q.npc, #list, r.nearest ~= '' and r.nearest or 'none')
    return r
end

--- One CSV row, for the driver script that walks the whole database.
function V.row(r)
    local function n(v) return v == nil and '' or ('%.1f'):format(v) end
    return table.concat({
        r.area, tostring(r.id), r.ok and 'ok' or 'MISS',
        '"' .. tostring(r.name):gsub('"', "'") .. '"',
        '"' .. tostring(r.npc):gsub('"', "'") .. '"',
        tostring(r.want_zone or ''), n(r.want_x), n(r.want_z),
        tostring(r.zone or ''), n(r.x), n(r.z), n(r.dist),
        '"' .. tostring(r.why):gsub('"', "'") .. '"',
        -- Fourteenth column, added after the first sweeps: rows written before this default
        -- to 'quest', which is what they were.
        r.kind or 'quest',
        -- Fifteenth column. Written on every row, not only on misses: "the NPC was not here"
        -- and "nothing at all was here yet" are different findings and the count is what
        -- tells them apart. Rows written before this leave it blank.
        r.entities == nil and '' or tostring(r.entities),
    }, ',')
end

--- Kept for anything that still asks for a quest by name.
function V.quest(area, id) return V.entry('quest', area, id) end

return V
