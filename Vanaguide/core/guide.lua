-- Vanaguide :: core/guide.lua
-- The guide format and its parser.
--
-- A guide is a list of steps written one per line.  The line starts with a one-letter verb
-- and the text shown to the player, and everything after it is |TAG|value| pairs:
--
--     t Ask the gate guard about missions|Z|230|POS|-140,120,8|N|He is by the fountain.|
--     A Mission 1-1: Save the Children|M|sandoria,2|Z|230|
--     K Kill orcs until you have three tusks|IT|1122,3|Z|140|
--
-- Verbs:  A accept · T turn in · C complete an objective · K kill · B buy · t talk
--         R run to · U use an item · F travel · N note only · L reach a level
--
-- Tags:   Z    zone (id, or a name from data/zone_names.lua)
--         POS  x,z[,radius]  — where in the zone; radius defaults to 10 yalms
--         M    area,id  — done when that mission is finished
--         MA   area,id  — done when that mission is active or finished
--         Q    area,id  — done when that quest is completed
--         QA   area,id  — done when that quest is *accepted* (for A steps)
--         KI   id       — done when you hold that key item
--         IT   id[,n]   — done when you hold n of that item (default 1)
--         LV   n        — done at level n
--         JOB  job,lvl  — done when that job reaches that level
--         RANK n        — done at that nation rank
--         SP   id       — done when you know that spell
--         N    note shown under the step
--         NPC  name     — who the step is about, by the name the client shows.  The audit
--                         looks for this NPC at the marker and `/vg talk` targets it.  Without
--                         it the step's quest or mission entry names the NPC, which is only
--                         right for the step where that quest or mission starts.
--         FIXED         — never skipped automatically, even if its condition already holds
--         RA   id       — the RetroAchievements achievement this step is (guides/achievements.lua);
--                         shown as earned or not from the launcher's snapshot, never a condition
--
-- A step with no completion tag is a manual step: it waits for a click, or for the player
-- to walk into its POS radius if it has one.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local zones = require('data.zone_names')

local G = { guides = {}, order = {} }

local VERBS = {
    A = 'accept', T = 'turnin', C = 'complete', K = 'kill', B = 'buy',
    t = 'talk', R = 'run', U = 'use', F = 'travel', N = 'note', L = 'level',
}

local TAGS = {
    Z = true, POS = true, M = true, MA = true, Q = true, QA = true, KI = true,
    IT = true, LV = true, JOB = true, RANK = true, SP = true, N = true, NPC = true,
    FIXED = true, RA = true,
}

local function trim(s) return (s:gsub('^%s+', ''):gsub('%s+$', '')) end

local function numbers(s)
    local out = {}
    for n in s:gmatch('-?%d+%.?%d*') do out[#out + 1] = tonumber(n) end
    return out
end

--- Parse one line into a step, or nil (blank lines and -- comments).
function G.parse_line(line, lineno)
    line = trim(line or '')
    if line == '' or line:sub(1, 2) == '--' then return nil end

    local head = line:match('^([^|]*)') or ''
    local verb = head:sub(1, 1)
    local kind = VERBS[verb]
    if kind == nil then
        return nil, ('line %d: unknown verb %q'):format(lineno or 0, verb)
    end

    local step = { kind = kind, text = trim(head:sub(2)), line = lineno }

    local seen = {}
    for tag, value in line:gmatch('|([^|]+)|([^|]*)') do
        if not tag:match('^[A-Z]+$') or not TAGS[tag] then
            return nil, ('line %d: unknown tag %q'):format(lineno or 0, tag)
        end
        if seen[tag] then
            return nil, ('line %d: duplicate tag %q'):format(lineno or 0, tag)
        end
        seen[tag] = true
        value = trim(value)
        if tag == 'Z' then
            step.zone = tonumber(value) or zones.find(value)
            if step.zone == nil then
                return nil, ('line %d: unknown zone %q'):format(lineno or 0, value)
            end
        elseif tag == 'POS' then
            local n = numbers(value)
            if #n < 2 then return nil, ('line %d: POS needs x,z'):format(lineno or 0) end
            step.pos = { x = n[1], z = n[2], r = n[3] or 10 }
        elseif tag == 'M' or tag == 'MA' or tag == 'Q' or tag == 'QA' then
            local area, id = value:match('^([%w_]+)%s*,%s*(%d+)$')
            if area == nil then
                return nil, ('line %d: %s needs area,id'):format(lineno or 0, tag)
            end
            step[tag == 'M' and 'mission' or (tag == 'MA' and 'mission_accept'
                or (tag == 'Q' and 'quest' or 'quest_accept'))] =
                { area = area, id = tonumber(id) }
        elseif tag == 'KI' then
            step.key_item = tonumber(value)
            if step.key_item == nil then
                return nil, ('line %d: KI needs an id'):format(lineno or 0)
            end
        elseif tag == 'IT' then
            local n = numbers(value)
            if #n == 0 or n[1] < 0 or n[2] ~= nil and n[2] < 1 then
                return nil, ('line %d: IT needs item id[,positive count]'):format(lineno or 0)
            end
            step.item = { id = n[1], count = n[2] or 1 }
        elseif tag == 'LV' then
            step.level = tonumber(value)
            if step.level == nil or step.level < 1 then
                return nil, ('line %d: LV needs a positive level'):format(lineno or 0)
            end
        elseif tag == 'JOB' then
            local n = numbers(value)
            if #n == 0 or n[1] < 1 or n[2] ~= nil and n[2] < 1 then
                return nil, ('line %d: JOB needs job id[,positive level]'):format(lineno or 0)
            end
            step.job = { id = n[1], level = n[2] or 1 }
        elseif tag == 'RANK' then
            step.rank = tonumber(value)
            if step.rank == nil or step.rank < 1 then
                return nil, ('line %d: RANK needs a positive rank'):format(lineno or 0)
            end
        elseif tag == 'SP' then
            step.spell = tonumber(value)
            if step.spell == nil or step.spell < 0 then
                return nil, ('line %d: SP needs a spell id'):format(lineno or 0)
            end
        elseif tag == 'N' then
            step.note = value
        elseif tag == 'NPC' then
            if value == '' then return nil, ('line %d: NPC needs a name'):format(lineno or 0) end
            step.npc = value
        elseif tag == 'FIXED' then
            step.fixed = true
        elseif tag == 'RA' then
            step.ra = tonumber(value)
            if step.ra == nil or step.ra < 1 then
                return nil, ('line %d: RA needs an achievement id'):format(lineno or 0)
            end
        end
    end

    -- The "N" verb is a note with no completion of its own; make that explicit rather than
    -- leaving a step the player can never satisfy sitting at the top of the window.
    if step.kind == 'note' then step.manual = true end
    if step.zone == nil and step.pos ~= nil then
        return nil, ('line %d: POS without Z'):format(lineno or 0)
    end
    return step
end

--- Parse a whole guide body.  Returns steps, errors (errors is empty on a clean parse).
function G.parse(body)
    local steps, errs = {}, {}
    local n = 0
    for line in tostring(body or ''):gmatch('[^\r\n]*') do
        n = n + 1
        local step, err = G.parse_line(line, n)
        if err ~= nil then errs[#errs + 1] = err end
        if step ~= nil then
            step.index = #steps + 1
            steps[#steps + 1] = step
        end
    end
    return steps, errs
end

--- Register a guide.  `def.steps` may be the raw body or an already-parsed list.
function G.register(def)
    assert(type(def) == 'table' and def.name, 'a guide needs a name')
    local steps, errs = def.steps, {}
    if type(steps) ~= 'table' then steps, errs = G.parse(steps) end
    local guide = {
        name = def.name,
        author = def.author or 'unknown',
        nation = def.nation,
        levels = def.levels,
        desc = def.desc,
        steps = steps,
        errors = errs,
    }
    if G.guides[guide.name] == nil then G.order[#G.order + 1] = guide.name end
    G.guides[guide.name] = guide
    return guide
end

--- Who a step is about, or nil.  `entry` is the step's quest or mission from the database.
---
--- The step's own `NPC` tag first.  Then the database entry's NPC, but only when the step is
--- in that entry's zone: the entry names where a quest or mission *starts*, and a hand-written
--- guide's turn-in step in another town is about somebody else ("Deliver the Zeruhn Report to
--- Naji" is not about Argus, who is in Port Bastok).  Then the name a generated step's note
--- carries ("Ask X." / "Starts with X.").
function G.npc_of(step, entry)
    if step == nil then return nil end
    if step.npc ~= nil then return step.npc end
    if entry ~= nil and entry.npc ~= nil
        and (step.zone == nil or entry.zone == nil or step.zone == entry.zone) then
        return entry.npc
    end
    local note = step.note or ''
    return note:match('Ask ([^.]+)%.') or note:match('Starts with ([^.]+)%.')
end

function G.get(name) return G.guides[name] end

function G.list()
    local out = {}
    for _, name in ipairs(G.order) do out[#out + 1] = G.guides[name] end
    return out
end

return G
